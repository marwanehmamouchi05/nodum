"""Authentication tests use real hashing, cookies, ASGI routes and both repositories."""
from dataclasses import replace
from datetime import timedelta
import json
from urllib.parse import urlencode
import pytest

from app.api.auth import get_auth_settings
from app.api.ring import get_ring_service
from app.api.dependencies import utc_now
from app.auth_config import AuthSettings
from app.config import ConfigurationError
from app.main import app
from app.models.ring import RingPrincipal
from app.services.auth import AuthService, bootstrap_user, csrf_token, digest, hash_password, verify_password
from app.services.errors import DomainError
from app.sqlite_repository import SQLiteRepository
from conftest import NOW
from test_ring import ACCOUNT, settings, remote, service, nonce_for  # noqa: F401

PASSWORD = "test-only-password-782!"


@pytest.fixture
def auth(api, repo):
    config = AuthSettings("http://test")
    app.dependency_overrides[get_auth_settings] = lambda: config
    auth = AuthService(repo, config)
    auth.create_user("admin@example.test", PASSWORD, "manager-1", NOW)
    return auth


def context(api):
    status, data, headers = api("GET", "/auth/session", include_headers=True)
    assert status == 200
    return headers[b"set-cookie"].decode().split(";")[0], data["csrf_token"]


def protected(cookie, csrf, origin="http://test"):
    return [(b"cookie", cookie.encode()), (b"x-csrf-token", csrf.encode()), (b"origin", origin.encode())]


def sign_in(api, username="admin@example.test", password=PASSWORD):
    cookie, csrf = context(api)
    status, data, headers = api("POST", "/auth/login", {"username": username, "password": password},
                                headers=protected(cookie, csrf), include_headers=True)
    assert status == 200, data
    return headers[b"set-cookie"].decode().split(";")[0], data["csrf_token"], data["user"]


def payload(service, offset=0, nonce=None):
    timestamp = int(NOW.timestamp() * 1000) + offset
    return {"nonce": nonce or nonce_for(service.settings.signing_key, timestamp, ACCOUNT), "time": timestamp}


def test_login_rotates_session_and_never_returns_secrets(api, auth, repo):
    old, csrf = context(api)
    status, body, headers = api("POST", "/auth/login", {"username": "ADMIN@example.test", "password": PASSWORD},
                               headers=protected(old, csrf), include_headers=True)
    assert status == 200
    cookie = headers[b"set-cookie"].decode()
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/" in cookie
    assert cookie.split(";")[0] != old
    assert body["csrf_token"] != csrf
    assert api("GET", "/auth/me", headers=[(b"cookie", old.encode())])[0] == 401
    assert PASSWORD not in json.dumps(body) and "password_hash" not in json.dumps(body)
    assert auth.user(cookie.split(";", 1)[0].split("=", 1)[1], NOW).id == body["user"]["id"]
    assert all(cookie.split(";", 1)[0].split("=", 1)[1] not in s.model_dump_json() for s in repo.list_auth_sessions())


@pytest.mark.parametrize("username,password", [("admin@example.test", "wrong"), ("unknown", PASSWORD)])
def test_login_failure_is_generic(api, auth, username, password):
    cookie, csrf = context(api)
    assert api("POST", "/auth/login", {"username": username, "password": password},
               headers=protected(cookie, csrf)) == (401, {"detail": "Invalid username or password"})


def test_current_user_requires_session_and_logout_revokes_it(api, auth):
    assert api("GET", "/auth/me")[0] == 401
    cookie, csrf, user = sign_in(api)
    assert api("GET", "/auth/me", headers=protected(cookie, csrf)) == (200, user)
    assert api("POST", "/auth/logout", {}, headers=protected(cookie, csrf))[0] == 200
    assert api("GET", "/auth/me", headers=protected(cookie, csrf))[0] == 401
    assert api("POST", "/ring/link", {"nonce": "x" * 43, "time": 1},
               headers=protected(cookie, csrf))[0] == 401


@pytest.mark.parametrize("origin,token", [("https://evil.test", "correct"), ("null", "correct"), ("http://test", "wrong"), ("", "correct")])
def test_login_csrf_rejected(api, auth, origin, token):
    cookie, csrf = context(api)
    status, _ = api("POST", "/auth/login", {"username": "admin@example.test", "password": PASSWORD},
                    headers=protected(cookie, csrf if token == "correct" else token, origin))
    assert status == 403


def test_throttle_is_persisted_and_recovers_after_window(api, auth, repo):
    cookie, csrf = context(api)
    for _ in range(5):
        assert api("POST", "/auth/login", {"username": "admin@example.test", "password": "wrong"},
                   headers=protected(cookie, csrf))[0] == 401
    assert repo.list_auth_throttles()
    assert api("POST", "/auth/login", {"username": "admin@example.test", "password": PASSWORD},
               headers=protected(cookie, csrf))[0] == 429
    app.dependency_overrides[utc_now] = lambda: NOW + timedelta(minutes=16)
    sign_in(api)


@pytest.mark.parametrize("change", ["expired", "inactive"])
def test_expired_or_inactive_user_session_rejected(api, auth, repo, change):
    cookie, csrf, user = sign_in(api)
    if change == "expired":
        app.dependency_overrides[utc_now] = lambda: NOW + timedelta(hours=9)
    else:
        record = repo.get_auth_user(user["id"])
        record.active = False
        repo.save_auth_user(record)
    assert api("GET", "/auth/me", headers=protected(cookie, csrf))[0] == 401


def test_login_validation_does_not_echo_password(api, auth):
    cookie, csrf = context(api)
    status, result = api("POST", "/auth/login", {"username": "admin", "password": PASSWORD * 20},
                         headers=protected(cookie, csrf))
    assert status == 422 and PASSWORD not in json.dumps(result)


def test_browser_get_preserves_query_without_matching_or_claiming(api, auth, service):
    app.dependency_overrides[get_ring_service] = lambda: service
    service.receive_code("code", NOW)
    status, html, headers = api("GET", "/ring/link?" + urlencode(payload(service)), include_headers=True)
    assert status == 200 and 'id="login"' in html and "Confirm and connect Ring" in html
    assert headers[b"cache-control"] == b"no-store" and headers[b"referrer-policy"] == b"no-referrer"
    assert b"frame-ancestors 'none'" in headers[b"content-security-policy"]
    assert service.repository.get_ring_account(service.account_key(ACCOUNT)).owner_user_id is None
    service.client.confirm.assert_not_called()
    script = api("GET", "/auth/client.js")[1]
    assert "window.location.search" in script and "params.get('nonce')" in script and "params.get('time')" in script
    # Invalid HMAC and stale time do not become an unauthenticated matching oracle.
    assert api("GET", "/ring/link?" + urlencode(payload(service, -600001, "x" * 43)))[0] == 200
    assert api("POST", "/ring/link", payload(service))[0] == 401


def test_authenticated_claim_uses_session_owner_and_sanitized_responses(api, auth, service, repo):
    app.dependency_overrides[get_ring_service] = lambda: service
    service.receive_code("code", NOW)
    cookie, csrf, user = sign_in(api)
    status, result = api("POST", "/ring/link", payload(service), headers=protected(cookie, csrf))
    assert (status, result) == (200, {"account_id": ACCOUNT, "status": "completed"})
    stored = repo.get_ring_account(service.account_key(ACCOUNT))
    assert stored.owner_user_id == user["id"] and stored.owner_id == "manager-1"
    accounts = api("GET", "/ring/accounts", headers=protected(cookie, csrf))
    assert accounts[0] == 200 and accounts[1][0]["status"] == "completed"
    text = json.dumps([result, accounts, user])
    for secret in ("access-secret", "refresh-secret", "encrypted_tokens", "password_hash"):
        assert secret not in text
    service.client.confirm.assert_called_once()
    service.client.complete.assert_called_once()
    assert api("POST", "/ring/link", payload(service), headers=protected(cookie, csrf))[0] == 409


@pytest.mark.parametrize("offset,nonce,expected", [(0, "x" * 43, 409), (-600001, None, 400), (1, None, 400)])
def test_claim_validates_nonce_and_freshness_after_login(api, auth, service, offset, nonce, expected):
    app.dependency_overrides[get_ring_service] = lambda: service
    service.receive_code("code", NOW)
    cookie, csrf, _ = sign_in(api)
    assert api("POST", "/ring/link", payload(service, offset, nonce), headers=protected(cookie, csrf))[0] == expected
    service.client.confirm.assert_not_called()


@pytest.mark.parametrize("operation", ["/ring/link", "/auth/logout", "/ring/events/event/process"])
def test_sensitive_mutations_require_csrf(api, auth, service, operation):
    app.dependency_overrides[get_ring_service] = lambda: service
    cookie, _, _ = sign_in(api)
    assert api("POST", operation, payload(service), headers=[(b"cookie", cookie.encode())])[0] == 403


@pytest.mark.parametrize("complete", [True, False])
def test_other_user_cannot_claim_owned_or_reserved_ring_account(api, auth, service, complete):
    app.dependency_overrides[get_ring_service] = lambda: service
    service.receive_code("code", NOW)
    first_cookie, first_csrf, first_user = sign_in(api)
    if not complete:
        from app.integrations.ring.client import RingRemoteError
        service.client.complete.side_effect = RingRemoteError()
    api("POST", "/ring/link", payload(service), headers=protected(first_cookie, first_csrf))
    auth.create_user("second@example.test", PASSWORD, "responder-1", NOW)
    cookie, csrf, _ = sign_in(api, "second@example.test")
    assert api("POST", "/ring/link", payload(service), headers=protected(cookie, csrf))[0] == 409
    assert api("GET", "/ring/accounts", headers=protected(cookie, csrf)) == (200, [])
    assert api("GET", f"/ring/accounts/{ACCOUNT}/devices", headers=protected(cookie, csrf))[0] == 403
    assert service.repository.get_ring_account(service.account_key(ACCOUNT)).owner_user_id == first_user["id"]


def test_supplied_person_id_cannot_override_session(api, auth, service):
    app.dependency_overrides[get_ring_service] = lambda: service
    cookie, csrf, _ = sign_in(api)
    assert api("POST", "/ring/link", {**payload(service), "person_id": "responder-1"},
               headers=protected(cookie, csrf))[0] == 422


def test_token_delivery_stays_fail_closed(api, auth):
    cookie, csrf, _ = sign_in(api)
    assert api("POST", "/ring/token-exchange", {"code": "unverified"}, headers=protected(cookie, csrf))[0] == 503


def test_password_hash_is_salted_and_not_reversible():
    first, second = hash_password(PASSWORD), hash_password(PASSWORD)
    assert first != second and PASSWORD not in first
    assert verify_password(PASSWORD, first) and not verify_password("wrong", first)
    assert not verify_password(PASSWORD, "malformed")


@pytest.mark.parametrize("password", ["short", "x" * 129])
def test_password_bounds(password):
    with pytest.raises(DomainError):
        hash_password(password)


def test_bootstrap_idempotent_and_no_silent_password_reset(repo, monkeypatch):
    monkeypatch.setenv("AUTH_BOOTSTRAP_USERNAME", "seed")
    monkeypatch.setenv("AUTH_BOOTSTRAP_PASSWORD", PASSWORD)
    monkeypatch.setenv("AUTH_BOOTSTRAP_PERSON_ID", "manager-1")
    monkeypatch.setenv("AUTH_PUBLIC_ORIGIN", "http://test")
    bootstrap_user(repo, NOW)
    original = repo.list_auth_users()[0]
    monkeypatch.setenv("AUTH_BOOTSTRAP_PASSWORD", "different-test-password")
    bootstrap_user(repo, NOW)
    assert repo.list_auth_users() == [original]


def test_partial_bootstrap_fails_cleanly(repo, monkeypatch):
    monkeypatch.setenv("AUTH_BOOTSTRAP_USERNAME", "seed")
    monkeypatch.delenv("AUTH_BOOTSTRAP_PASSWORD", raising=False)
    monkeypatch.delenv("AUTH_BOOTSTRAP_PERSON_ID", raising=False)
    with pytest.raises(ConfigurationError):
        bootstrap_user(repo, NOW)


@pytest.mark.parametrize("origin", ["", "http://production.test", "https://host/path", "https://user:secret@host", "*"])
def test_production_origin_must_be_explicit_https(monkeypatch, origin):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_PUBLIC_ORIGIN", origin)
    with pytest.raises(ConfigurationError):
        AuthSettings.from_env()


def test_production_cookie_has_host_prefix_secure_and_httponly(api, auth):
    app.dependency_overrides[get_auth_settings] = lambda: replace(auth.settings, public_origin="https://test", secure=True)
    _, _, headers = api("GET", "/auth/session", include_headers=True)
    cookie = headers[b"set-cookie"].decode()
    assert cookie.startswith("__Host-nodum_session=")
    assert "Secure" in cookie and "HttpOnly" in cookie and "Domain=" not in cookie


def test_identity_sessions_and_ownership_survive_restart(tmp_path, settings, remote):
    from app.services.ring import RingService
    from app.models.ring import RingLinkInput
    url = f"sqlite:///{tmp_path / 'auth.db'}"
    first = SQLiteRepository(url)
    first.initialize()
    auth = AuthService(first, AuthSettings("http://test"))
    user = auth.create_user("persisted", PASSWORD, "manager-1", NOW)
    cookie, _ = auth.issue(NOW, user.id)
    ring = RingService(first, settings, remote)
    ring.receive_code("code", NOW)
    principal = RingPrincipal(person_id=user.person_id, user_id=user.id, masked_account_identifier="p***d")
    ring.claim(RingLinkInput(**payload(ring)), principal, NOW)
    second = SQLiteRepository(url)
    second.initialize()
    assert AuthService(second, auth.settings).user(cookie, NOW).id == user.id
    assert verify_password(PASSWORD, second.get_auth_user(user.id).password_hash)
    assert RingService(second, settings, remote).authorized_account(ACCOUNT, principal).owner_user_id == user.id
    assert second.get_auth_session(digest(cookie)).created_at.utcoffset().total_seconds() == 0
    AuthService(second, auth.settings).logout(cookie)
    assert auth.user(cookie, NOW) is None
    with second.database.transaction() as connection:
        assert [r[0] for r in connection.execute("SELECT version FROM schema_migrations ORDER BY version")] == [1, 2, 3, 4]


def test_v3_database_upgrades_without_reassigning_legacy_accounts(tmp_path, monkeypatch, settings, remote):
    import app.database as database
    from app.services.ring import RingService
    from test_ring import link
    migrations = database.MIGRATIONS
    monkeypatch.setattr(database, "MIGRATIONS", migrations[:3])
    url = f"sqlite:///{tmp_path / 'upgrade.db'}"
    first = SQLiteRepository(url)
    first.initialize()
    ring = RingService(first, settings, remote)
    link(ring)
    monkeypatch.setattr(database, "MIGRATIONS", migrations)
    second = SQLiteRepository(url)
    second.initialize()
    assert second.get_ring_account(ring.account_key(ACCOUNT)).owner_user_id is None
    user = AuthService(second, AuthSettings("http://test")).create_user("new-manager", PASSWORD, "manager-1", NOW)
    with pytest.raises(DomainError) as exc:
        RingService(second, settings, remote).authorized_account(ACCOUNT, RingPrincipal(
            person_id=user.person_id, user_id=user.id, masked_account_identifier="n***r"))
    assert exc.value.status_code == 403


def test_refresh_keeps_user_ownership(api, auth, service):
    app.dependency_overrides[get_ring_service] = lambda: service
    service.receive_code("code", NOW)
    cookie, csrf, user = sign_in(api)
    assert api("POST", "/ring/link", payload(service), headers=protected(cookie, csrf))[0] == 200
    principal = RingPrincipal(person_id=user["person_id"], user_id=user["id"], masked_account_identifier="a***t")
    service.access_token(ACCOUNT, principal, NOW, force=True)
    assert service.repository.get_ring_account(service.account_key(ACCOUNT)).owner_user_id == user["id"]


def test_resident_login_does_not_confer_operator_authority(api, auth, service):
    app.dependency_overrides[get_ring_service] = lambda: service
    auth.create_user("resident", PASSWORD, "resident-1", NOW)
    cookie, csrf, _ = sign_in(api, "resident")
    assert api("POST", "/ring/link", payload(service), headers=protected(cookie, csrf))[0] == 403
    service.client.confirm.assert_not_called()


def test_missing_production_auth_configuration_keeps_health_available(api, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("AUTH_PUBLIC_ORIGIN", raising=False)
    assert api("GET", "/auth/session")[0] == 503
    assert api("GET", "/health")[0] == 200


@pytest.mark.parametrize("username,person", [("admin@example.test", "responder-1"), ("another", "manager-1")])
def test_duplicate_user_or_person_is_rejected(auth, username, person):
    with pytest.raises(DomainError) as exc:
        auth.create_user(username, PASSWORD, person, NOW)
    assert exc.value.status_code == 409
