"""Shared isolated repository and in-process HTTP fixtures."""
import asyncio
from datetime import datetime, timezone
import json
from urllib.parse import urlsplit

import pytest

from app.api.dependencies import get_repository, utc_now
from app.main import app
from app.repository import create_demo_repository

NOW = datetime(2026, 9, 29, 12, tzinfo=timezone.utc)


def pytest_addoption(parser):
    parser.addoption("--repository-backend", choices=["memory", "sqlite"], default="memory")


@pytest.fixture
def repo(request, tmp_path):
    if request.config.getoption("--repository-backend") == "sqlite":
        from app.sqlite_repository import SQLiteRepository

        repository = SQLiteRepository(f"sqlite:///{tmp_path / 'test.db'}")
        repository.initialize()
        return repository
    return create_demo_repository()


@pytest.fixture
def api(repo):
    """Exercise actual FastAPI routing, validation, dependencies, and responses.

    Tiny one-request ASGI transport keeps tests independent of an HTTP client
    dependency. No network or running server is needed.
    """
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[utc_now] = lambda: NOW

    def request(method, path, payload=None, *, raw=None, headers=(), include_headers=False):
        async def execute():
            target = urlsplit(path)
            body = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else b"")
            sent = []
            received = False

            async def receive():
                nonlocal received
                if not received:
                    received = True
                    return {"type": "http.request", "body": body, "more_body": False}
                # The app does not need another request message for JSON responses.
                await asyncio.Event().wait()

            async def send(message):
                sent.append(message)

            scope = {"type": "http", "asgi": {"version": "3.0"},
                     "http_version": "1.1", "method": method, "scheme": "http",
                     "path": target.path, "raw_path": target.path.encode(), "root_path": "",
                     "query_string": target.query.encode(), "headers": [(b"content-type", b"application/json"), *headers],
                     "client": ("127.0.0.1", 1234), "server": ("test", 80)}
            await asyncio.wait_for(app(scope, receive, send), timeout=5)
            status = next(m["status"] for m in sent if m["type"] == "http.response.start")
            content = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
            try:
                result = json.loads(content)
            except (ValueError, UnicodeDecodeError):
                result = content.decode()
            if include_headers:
                response_headers = dict(next(m["headers"] for m in sent if m["type"] == "http.response.start"))
                return status, result, response_headers
            return status, result

        return asyncio.run(execute())

    yield request
    app.dependency_overrides.clear()

