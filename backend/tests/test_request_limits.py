"""Bounded hostile requests through the actual application, without a network flood."""
import asyncio
import json

import pytest

from app.request_limits import RequestLimitsMiddleware


def test_oversized_json_is_rejected_before_authentication(api, repo):
    before = len(repo.list_auth_sessions())
    status, body, headers = api("POST", "/auth/login", raw=b" " * (1024 * 1024) + b"{}", include_headers=True)
    assert status == 413
    assert body == {"detail": "Request body exceeds 1048576 bytes"}
    assert headers[b"cache-control"] == b"no-store"
    assert len(repo.list_auth_sessions()) == before


def probe(chunks, headers=(), *, stall=False, disconnect=False):
    """No HTTP parser assumptions: hostile ASGI chunks reach the guard directly."""
    consumed = []
    downstream = []
    sent = []

    async def run():
        messages = iter(chunks)

        async def receive():
            try:
                chunk, more = next(messages)
                consumed.append(len(chunk))
                return {"type": "http.request", "body": chunk, "more_body": more}
            except StopIteration:
                if stall:
                    await asyncio.Event().wait()
                return {"type": "http.disconnect" if disconnect else "http.request", "body": b""}

        async def endpoint(scope, receive, send):
            downstream.append((await receive())["body"])
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        async def send(message):
            sent.append(message)

        await RequestLimitsMiddleware(endpoint, max_bytes=8, body_timeout=.02)(
            {"type": "http", "headers": list(headers)}, receive, send)

    asyncio.run(asyncio.wait_for(run(), 1))
    statuses = [m["status"] for m in sent if m["type"] == "http.response.start"]
    return statuses, downstream, consumed, sent


@pytest.mark.parametrize("headers", [[], [(b"content-length", b"2")], [(b"transfer-encoding", b"chunked")]])
def test_chunked_and_lying_length_cannot_bypass_limit(headers):
    status, downstream, consumed, _ = probe([(b"1234", True), (b"56789", True), (b"never-read", False)], headers)
    assert status == [413] and downstream == [] and consumed == [4, 5]


def test_declared_oversized_body_is_rejected_without_reading():
    status, downstream, consumed, _ = probe([(b"never-read", False)], [(b"content-length", b"9")])
    assert status == [413] and downstream == [] and consumed == []


@pytest.mark.parametrize("headers", [
    [(b"content-length", b"2"), (b"content-length", b"2")],
    [(b"content-length", b"2"), (b"transfer-encoding", b"chunked")],
    *[[(b"content-length", value)] for value in [b"-1", b"+2", b"2, 2", b"2x", b"", b"9" * 5000]],
])
def test_ambiguous_framing_never_reaches_handler(headers):
    status, downstream, consumed, _ = probe([(b"{}", False)], headers)
    assert status == [400] and downstream == [] and consumed == []


@pytest.mark.parametrize("length", [b"1", b"7"])
def test_bounded_body_still_must_match_declared_length(length):
    status, downstream, _, _ = probe([(b"{}", False)], [(b"content-length", length)])
    assert status == [400] and downstream == []


def test_exact_boundary_preserves_raw_signed_bytes():
    status, downstream, _, _ = probe([(b' {"a":', True), (b'1}', False)], [(b"content-length", b"8")])
    assert status == [200] and downstream == [b' {"a":1}']


def test_stalled_body_is_bounded_and_does_not_run_handler():
    status, downstream, _, sent = probe([(b"x", True)], stall=True)
    assert status == [408] and downstream == []
    assert b"x" not in json.loads(sent[-1]["body"])["detail"].encode()


def test_disconnect_before_body_completion_has_no_side_effect():
    status, downstream, _, _ = probe([(b"x", True)], disconnect=True)
    assert status == [] and downstream == []
