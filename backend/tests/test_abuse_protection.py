import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.abuse_protection import Allowances, MeteredGateway, TrafficLimitsMiddleware, UsageGuard
from app.integrations.bedrock import BedrockSettings, BedrockUnavailable
from app.services.errors import DomainError


NOW = datetime(2026, 10, 22, 12, tzinfo=timezone.utc)


def test_quota_survives_restart_and_reserves_atomically(tmp_path):
    path = tmp_path / "usage.db"
    limits = replace(Allowances(), calls_per_day=3)
    def call(_):
        guard = UsageGuard(path, limits, lambda: NOW)
        try:
            guard.provider_call({}, BedrockSettings())
            return True
        except DomainError as exc:
            assert exc.status_code == 429
            return False
    UsageGuard(path, limits, lambda: NOW)
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(call, range(12))) == 3
    assert call(None) is False


def test_daily_reset_cannot_reset_monthly_allowance(tmp_path):
    now = [NOW]
    guard = UsageGuard(tmp_path / "usage.db", replace(Allowances(), calls_per_day=1, calls_per_month=2), lambda: now[0])
    guard.provider_call({}, BedrockSettings())
    with pytest.raises(DomainError):guard.provider_call({}, BedrockSettings())
    now[0] += timedelta(days=1)
    guard.provider_call({}, BedrockSettings())
    now[0] += timedelta(days=1)
    with pytest.raises(DomainError):guard.provider_call({}, BedrockSettings())
    now[0] = datetime(2026, 11, 1, tzinfo=timezone.utc)
    guard.provider_call({}, BedrockSettings())


def test_rejected_call_never_reaches_provider_and_failures_still_count(tmp_path):
    class Provider:
        calls = 0
        def converse(self, **payload):
            self.calls += 1
            raise BedrockUnavailable()
    provider = Provider()
    guard = UsageGuard(tmp_path / "usage.db", replace(Allowances(), calls_per_day=1), lambda: NOW)
    gateway = MeteredGateway(provider, guard, BedrockSettings())
    with pytest.raises(BedrockUnavailable):gateway.converse(messages=[])
    with pytest.raises(DomainError):gateway.converse(messages=[])
    assert provider.calls == 1


def test_per_user_limits_and_single_flight_release_on_error(tmp_path):
    guard = UsageGuard(tmp_path / "usage.db", replace(Allowances(), questions_per_minute=1), lambda: NOW)
    with guard.question("one"):
        with pytest.raises(DomainError):
            with guard.question("two"):pass
    with pytest.raises(RuntimeError):
        with guard.question("two"):raise RuntimeError("provider failed")
    with pytest.raises(DomainError):
        with guard.question("one"):pass
    with guard.question("three"):pass


def test_oversized_context_and_unbudgeted_model_fail_closed(tmp_path):
    guard = UsageGuard(tmp_path / "usage.db", clock=lambda: NOW)
    with pytest.raises(DomainError):guard.provider_call({"messages": "x" * 65536}, BedrockSettings())
    with pytest.raises(DomainError):guard.provider_call({}, BedrockSettings(model_id="different-model"))
    with pytest.raises(DomainError):guard.provider_call({}, BedrockSettings(max_tokens=2000))


def test_input_byte_allowance_is_not_bypassed_by_new_guard(tmp_path):
    path = tmp_path / "usage.db"
    limits = replace(Allowances(), input_bytes_per_day=5000)
    UsageGuard(path, limits, lambda: NOW).provider_call({}, BedrockSettings())
    with pytest.raises(DomainError):UsageGuard(path, limits, lambda: NOW).provider_call({}, BedrockSettings())


def test_accounting_failure_blocks_provider(tmp_path):
    guard = UsageGuard(tmp_path / "usage.db", clock=lambda: NOW)
    guard.path = str(tmp_path / "absent" / "usage.db")
    with pytest.raises(DomainError) as failure:guard.provider_call({}, BedrockSettings())
    assert failure.value.status_code == 503


def test_concurrency_rejection_releases_slot_after_handler_failure():
    async def run():
        entered = asyncio.Event(); release = asyncio.Event(); statuses = []
        async def app(scope, receive, send):
            entered.set()
            await release.wait()
            raise RuntimeError("handler failed")
        async def receive():raise AssertionError("Body should not be read")
        async def send(message):
            if message["type"] == "http.response.start":statuses.append(message["status"])
        guard = TrafficLimitsMiddleware(app, concurrency=1)
        scope = {"type": "http", "path": "/health", "client": ("one", 1), "app": SimpleNamespace(state=SimpleNamespace(usage_guard=True))}
        first = asyncio.create_task(guard(scope, receive, send))
        await entered.wait()
        await guard(scope, receive, send)
        release.set()
        with pytest.raises(RuntimeError):await first
        assert statuses == [429] and guard.active == 0
    asyncio.run(run())


def test_web_throttle_does_not_read_body_and_resets_without_blocking_forms():
    async def run():
        calls = []; statuses = []; reads = []
        async def app(scope, receive, send):
            calls.append(scope["path"])
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})
        async def receive():
            reads.append(True)
            return {"type": "http.request", "body": b"", "more_body": False}
        async def send(message):
            if message["type"] == "http.response.start":statuses.append(message["status"])
        now = [0]
        guard = TrafficLimitsMiddleware(app, per_ip=1, global_limit=2, clock=lambda: now[0])
        scope = {"type": "http", "path": "/resident/visitors", "client": ("one", 1), "app": SimpleNamespace(state=SimpleNamespace(usage_guard=True))}
        await guard(scope, receive, send)
        await guard(scope, receive, send)
        scope["client"] = ("two", 1)
        await guard(scope, receive, send)
        scope["client"] = ("three", 1)
        await guard(scope, receive, send)
        now[0] = 60
        await guard(scope, receive, send)
        assert statuses == [200, 429, 200, 429, 200]
        assert calls == ["/resident/visitors"] * 3 and not reads
    asyncio.run(run())


def test_api_enforces_ai_quota_but_keeps_normal_routes(api, tmp_path, monkeypatch):
    # Reuse actual routed app; provider must not be called after reservation fails.
    from app.main import app
    from app.api.agent import get_gateway, get_actions
    from app.services.agent_actions import PendingActionStore
    class Provider:
        calls = []
        def converse(self, **payload):
            self.calls.append(payload)
            return {"stopReason": "end_turn", "output": {"message": {"role": "assistant", "content": [{"text": "Hello"}]}}}
    provider = Provider()
    app.dependency_overrides[get_gateway] = lambda: provider
    app.dependency_overrides[get_actions] = lambda: PendingActionStore()
    guard = UsageGuard(tmp_path / "usage.db", replace(Allowances(), questions_per_minute=1), lambda: NOW)
    monkeypatch.setattr(app.state, "usage_guard", guard, raising=False)
    assert api("POST", "/agent/chat", {"message": "Hello"})[0] == 200
    assert api("POST", "/agent/chat", {"message": "Hello"})[0] == 429
    assert len(provider.calls) == 1
    assert api("GET", "/health")[0] == 200
