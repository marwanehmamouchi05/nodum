"""Single-server abuse controls; persistent AI allowances, not AWS billing caps."""
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
from threading import BoundedSemaphore
import time

from starlette.responses import JSONResponse
from app.services.errors import DomainError


LIMIT_MESSAGE = "Demo AI allowance reached. Please use the ordinary forms or local Guide."


@dataclass(frozen=True)
class Allowances:
    questions_per_minute: int = 5
    questions_per_user_day: int = 20
    questions_per_day: int = 60
    calls_per_day: int = 40
    calls_per_month: int = 200
    input_bytes_per_day: int = 1_000_000
    input_bytes_per_month: int = 4_000_000
    call_bytes: int = 65_536


class UsageGuard:
    def __init__(self, path, limits=None, clock=None):
        self.path = str(path)
        self.limits = limits or Allowances()
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.slot = BoundedSemaphore(1)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS usage (kind TEXT, window TEXT, subject TEXT, used INTEGER NOT NULL, PRIMARY KEY(kind, window, subject))")

    def reserve(self, entries):
        # All windows reserve together. No refunds: ambiguous provider failures
        # may already be billable. SQLite serializes across threads/processes.
        try:
            with sqlite3.connect(self.path, timeout=1) as db:
                db.execute("BEGIN IMMEDIATE")
                for kind, window, subject, amount, maximum in entries:
                    row = db.execute("SELECT used FROM usage WHERE kind=? AND window=? AND subject=?", (kind, window, subject)).fetchone()
                    if (row[0] if row else 0) + amount > maximum:
                        raise DomainError(429, LIMIT_MESSAGE)
                for kind, window, subject, amount, _ in entries:
                    db.execute("INSERT INTO usage VALUES(?,?,?,?) ON CONFLICT(kind,window,subject) DO UPDATE SET used=used+excluded.used", (kind, window, subject, amount))
                # Retain current/previous month only; never reset active quotas.
                now = self.clock()
                previous = (now.replace(day=1).date().toordinal() - 1)
                cutoff = datetime.fromordinal(previous).strftime("%Y-%m")
                db.execute("DELETE FROM usage WHERE window < ?", (cutoff,))
        except sqlite3.Error:
            raise DomainError(503, "AI usage accounting is unavailable. Use the ordinary forms or local Guide.") from None

    @contextmanager
    def question(self, identity):
        if not self.slot.acquire(blocking=False):
            raise DomainError(429, "The demo assistant is busy. Please retry shortly or use the ordinary forms.")
        try:
            now = self.clock(); day = now.strftime("%Y-%m-%d")
            subject = hashlib.sha256(identity.encode()).hexdigest()
            self.reserve([
                ("question-minute", now.strftime("%Y-%m-%dT%H:%M"), subject, 1, self.limits.questions_per_minute),
                ("question-user-day", day, subject, 1, self.limits.questions_per_user_day),
                ("question-day", day, "all", 1, self.limits.questions_per_day),
            ])
            yield
        finally:
            self.slot.release()

    def provider_call(self, payload, settings):
        # Fail closed if a deployment switches to an unbudgeted model/output size.
        if settings.model_id != "eu.amazon.nova-2-lite-v1:0" or settings.max_tokens > 1000:
            raise DomainError(503, "This AI model is not enabled under the demo allowance.")
        size = len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) + 4096
        if size > self.limits.call_bytes:
            raise DomainError(429, "AI context is too large. Please narrow your question or use the ordinary forms.")
        now = self.clock(); day = now.strftime("%Y-%m-%d"); month = now.strftime("%Y-%m")
        self.reserve([
            ("call-day", day, "all", 1, self.limits.calls_per_day),
            ("call-month", month, "all", 1, self.limits.calls_per_month),
            ("input-day", day, "all", size, self.limits.input_bytes_per_day),
            ("input-month", month, "all", size, self.limits.input_bytes_per_month),
        ])


class MeteredGateway:
    def __init__(self, gateway, guard, settings):
        self.gateway, self.guard, self.settings = gateway, guard, settings

    def converse(self, **payload):
        self.guard.provider_call(payload, self.settings)
        return self.gateway.converse(**payload)


class TrafficLimitsMiddleware:
    """Bound admission before body buffering. Memory is bounded under IP churn."""
    def __init__(self, app, per_ip=120, global_limit=600, concurrency=20, clock=None):
        self.app = app
        self.per_ip, self.global_limit, self.concurrency = per_ip, global_limit, concurrency
        self.clock = clock or time.monotonic
        self.windows = OrderedDict()
        self.active = 0
        self.minute = None
        self.total = 0

    async def __call__(self, scope, receive, send):
        state = getattr(scope.get("app"), "state", None)
        if scope["type"] != "http" or not getattr(state, "usage_guard", None):
            await self.app(scope, receive, send)
            return
        # ASGI event-loop ownership makes check/reserve atomic before any await.
        minute = int(self.clock() // 60)
        if self.minute != minute:
            self.minute, self.total = minute, 0
            self.windows.clear()
        client = scope.get("client")
        ip = client[0] if client else "unknown"
        count = self.windows.get(ip, 0)
        if count >= self.per_ip or self.total >= self.global_limit or self.active >= self.concurrency:
            await JSONResponse({"detail": "Too many requests. Please retry shortly."}, status_code=429,
                               headers={"Retry-After": "60", "Cache-Control": "no-store"})(scope, receive, send)
            return
        self.total += 1
        self.windows[ip] = count + 1
        self.windows.move_to_end(ip)
        if len(self.windows) > 4096:
            self.windows.popitem(last=False)
        self.active += 1
        try:
            await self.app(scope, receive, send)
        finally:
            self.active -= 1
