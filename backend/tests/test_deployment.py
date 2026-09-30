"""Deployment boundaries: startup, CORS, optional Ring and server arguments."""
import asyncio
import json
from unittest.mock import Mock

from cryptography.fernet import Fernet
import pytest

from app.config import AppSettings, ConfigurationError, validate_startup
from app.main import create_app
from app.run import main


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    import os
    names = {"APP_ENV", "HOST", "PORT", "LOG_LEVEL", "ACCESS_LOG", "DATABASE_URL",
             "CORS_ALLOWED_ORIGINS", "CORS_ALLOW_CREDENTIALS", "FORWARDED_ALLOW_IPS",
             "GRACEFUL_SHUTDOWN_SECONDS"}
    for name in list(os.environ):
        if name in names or name.startswith("RING_"):
            monkeypatch.delenv(name)


def production(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'production.db'}")


def ring_configuration(monkeypatch):
    for name, value in {
        "RING_REQUIRED": "true", "RING_CLIENT_ID": "test", "RING_CLIENT_SECRET": "private-secret",
        "RING_SIGNING_KEY": "private-signing", "RING_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "RING_ENVIRONMENT": "staging", "RING_API_BASE_URL": "https://api.amazonvision.com",
        "RING_OAUTH_TOKEN_URL": "https://oauth.ring.com/oauth/token",
        "RING_ACCOUNT_LINK_URL": "https://nodum.example/link", "RING_TOKEN_EXCHANGE_URL": "https://nodum.example/ring/token-exchange",
        "RING_WEBHOOK_URL": "https://nodum.example/ring/webhooks", "RING_HOMEPAGE_URL": "https://nodum.example/",
    }.items():
        monkeypatch.setenv(name, value)


def request(application, method="GET", headers=()):
    async def execute():
        messages = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        await application({"type": "http", "asgi": {"version": "3.0"}, "method": method,
                           "path": "/health", "root_path": "", "query_string": b"",
                           "headers": list(headers), "scheme": "http", "server": ("test", 80)}, receive, send)
        start = next(m for m in messages if m["type"] == "http.response.start")
        body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
        return start["status"], dict(start["headers"]), body
    return asyncio.run(execute())


def test_default_no_cors_and_health_unchanged():
    status, headers, body = request(create_app(), headers=[(b"origin", b"https://untrusted.example")])
    assert status == 200 and json.loads(body) == {"status": "healthy"}
    assert b"access-control-allow-origin" not in headers


def test_production_explicit_cors(monkeypatch, tmp_path):
    production(monkeypatch, tmp_path)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://nodum.example,https://admin.example")
    application = create_app()
    status, headers, _ = request(application, "OPTIONS", [
        (b"origin", b"https://nodum.example"), (b"access-control-request-method", b"POST"),
        (b"access-control-request-headers", b"content-type,authorization")])
    assert status == 200 and headers[b"access-control-allow-origin"] == b"https://nodum.example"
    assert b"access-control-allow-credentials" not in headers
    status, headers, _ = request(application, "OPTIONS", [
        (b"origin", b"https://attacker.example"), (b"access-control-request-method", b"POST")])
    assert status == 400 and b"access-control-allow-origin" not in headers


def test_credentialed_cors_requires_explicit_origins(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "true")
    _, headers, _ = request(create_app(), headers=[(b"origin", b"http://localhost:5173")])
    assert headers[b"access-control-allow-credentials"] == b"true"
    assert headers[b"access-control-allow-origin"] == b"http://localhost:5173"


@pytest.mark.parametrize("origin", ["*", "https://*.example.com", "null", "https://site.example/path",
                                    "https://secret@site.example", "http://site.example", "https://site.example:bad"])
def test_unsafe_production_origins_rejected(monkeypatch, origin):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", origin)
    with pytest.raises(ConfigurationError, match="CORS_ALLOWED_ORIGINS"):
        create_app()


@pytest.mark.parametrize("name,value", [("PORT", "0"), ("PORT", "65536"), ("PORT", "abc"),
    ("APP_ENV", "unknown"), ("HOST", "http://host"), ("LOG_LEVEL", "unknown"),
    ("CORS_ALLOW_CREDENTIALS", "yes"), ("RING_REQUIRED", "yes"), ("ACCESS_LOG", "yes"),
    ("FORWARDED_ALLOW_IPS", "*"), ("GRACEFUL_SHUTDOWN_SECONDS", "0")])
def test_invalid_settings_fail_clearly(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigurationError, match=name):
        AppSettings.from_env()


def test_runner_passes_env_to_uvicorn(monkeypatch):
    import uvicorn
    run = Mock()
    monkeypatch.setattr(uvicorn, "run", run)
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "9090")
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "10.0.0.5,10.1.0.0/24")
    assert main([]) == 0
    assert run.call_args.args == ("app.main:app",)
    options = run.call_args.kwargs
    assert options["host"] == "0.0.0.0" and options["port"] == 9090
    assert options["workers"] == 1 and options["reload"] is False
    assert options["proxy_headers"] is True and options["server_header"] is False


def test_no_proxy_trust_by_default(monkeypatch):
    import uvicorn
    run = Mock()
    monkeypatch.setattr(uvicorn, "run", run)
    main([])
    assert run.call_args.kwargs["proxy_headers"] is False


def test_runner_dotenv_does_not_override_environment(monkeypatch, tmp_path):
    import uvicorn
    run = Mock()
    monkeypatch.setattr(uvicorn, "run", run)
    path = tmp_path / "startup.env"
    path.write_text("PORT=8080\nHOST=0.0.0.0\n")
    monkeypatch.setenv("PORT", "9090")
    monkeypatch.setenv("HOST", "127.0.0.1")
    main(["--env-file", str(path)])
    assert run.call_args.kwargs["port"] == 9090


def test_missing_env_file_fails_cleanly(tmp_path, capsys):
    assert main(["--env-file", str(tmp_path / "missing")]) == 2
    assert "environment file does not exist" in capsys.readouterr().err


def test_required_ring_lists_missing_variables_without_secrets(monkeypatch, tmp_path, capsys):
    production(monkeypatch, tmp_path)
    monkeypatch.setenv("RING_REQUIRED", "true")
    monkeypatch.setenv("RING_CLIENT_SECRET", "never-print-this")
    assert main([]) == 2
    message = capsys.readouterr().err
    assert "RING_CLIENT_ID" in message and "RING_SIGNING_KEY" in message
    assert "never-print-this" not in message


def test_valid_required_ring_no_network(monkeypatch, tmp_path):
    production(monkeypatch, tmp_path)
    ring_configuration(monkeypatch)
    validate_startup(AppSettings.from_env())


@pytest.mark.parametrize("name,value", [("RING_ENCRYPTION_KEY", "secret-invalid-key"),
    ("RING_API_BASE_URL", "http://secret-host"), ("RING_ENVIRONMENT", "invalid")])
def test_invalid_required_ring_sanitized(monkeypatch, tmp_path, name, value):
    production(monkeypatch, tmp_path)
    ring_configuration(monkeypatch)
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigurationError) as exc:
        validate_startup(AppSettings.from_env())
    assert value not in str(exc.value)


def test_signing_key_alias_works_when_primary_empty(monkeypatch, tmp_path):
    from app.integrations.ring.config import RingSettings
    production(monkeypatch, tmp_path)
    ring_configuration(monkeypatch)
    monkeypatch.setenv("RING_SIGNING_KEY", "")
    monkeypatch.setenv("RING_WEBHOOK_SECRET", "legacy-key")
    validate_startup(AppSettings.from_env())
    assert RingSettings.from_env().signing_key == "legacy-key"


def test_optional_ring_invalid_config_does_not_block_startup(monkeypatch, tmp_path):
    production(monkeypatch, tmp_path)
    monkeypatch.setenv("RING_API_BASE_URL", "invalid")
    application = create_app()
    async def startup():
        async with application.router.lifespan_context(application):
            assert application.state.repository.get_business("atlas-dental") is not None
    asyncio.run(startup())
    assert request(application)[0] == 200


@pytest.mark.parametrize("url", ["", "sqlite:///./nodum.db", "postgresql://secret@server/db"])
def test_production_requires_explicit_absolute_database(monkeypatch, url):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        validate_startup(AppSettings.from_env())


def test_database_failure_sanitized(monkeypatch, tmp_path):
    production(monkeypatch, tmp_path)
    from app.sqlite_repository import SQLiteRepository
    monkeypatch.setattr(SQLiteRepository, "initialize", Mock(side_effect=OSError("private-path")))
    application = create_app()
    async def startup():
        async with application.router.lifespan_context(application):
            pytest.fail("Startup should fail")
    with pytest.raises(ConfigurationError) as exc:
        asyncio.run(startup())
    assert "storage permissions" in str(exc.value) and "private-path" not in str(exc.value)


def test_production_import_schema_does_not_require_credentials(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    schema = create_app().openapi()
    assert "/health" in schema["paths"] and "/ring/webhooks" in schema["paths"]


@pytest.mark.parametrize("host,target", [("0.0.0.0", "127.0.0.1"), ("::", "[::1]"), ("127.0.0.2", "127.0.0.2")])
def test_health_probe_uses_bind_and_port(monkeypatch, host, target):
    from app import healthcheck
    monkeypatch.setenv("HOST", host)
    monkeypatch.setenv("PORT", "8123")
    response = Mock(status=200)
    response.read.return_value = b'{"status":"healthy"}'
    opener = Mock()
    opener.open.return_value.__enter__ = Mock(return_value=response)
    opener.open.return_value.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(healthcheck, "build_opener", Mock(return_value=opener))
    healthcheck.main()
    opener.open.assert_called_once_with(f"http://{target}:8123/health", timeout=3)
