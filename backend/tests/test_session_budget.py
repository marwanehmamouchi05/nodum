"""Bound anonymous persistent writes without blocking existing valid sessions."""
from datetime import timedelta

import pytest

from app.api.auth import get_auth_settings
from app.api.dependencies import utc_now
from app.auth_config import AuthSettings
from app.main import app
from app.services.auth import AuthService
from app.services.errors import DomainError
from conftest import NOW


def test_discarded_cookies_cannot_grow_sessions_without_limit(api, repo):
    app.dependency_overrides[get_auth_settings] = lambda: AuthSettings("http://test")
    cookie = None
    for _ in range(30):
        status, _, response_headers = api("GET", "/auth/session", include_headers=True)
        assert status == 200
        cookie = response_headers[b"set-cookie"].split(b";")[0]
    before = len(repo.list_auth_sessions())
    # Caller-supplied forwarded headers cannot rotate the trusted client budget.
    status, _ = api("GET", "/auth/session", headers=[(b"x-forwarded-for", b"192.0.2.55")])
    assert status == 429 and len(repo.list_auth_sessions()) == before == 30
    # Valid cookies remain usable; a global HTTP request throttle would break this.
    assert api("GET", "/auth/session", headers=[(b"cookie", cookie)])[0] == 200
    app.dependency_overrides[utc_now] = lambda: NOW + timedelta(minutes=16)
    assert api("GET", "/auth/session")[0] == 200
    assert len(repo.list_auth_sessions()) == 1


def test_global_anonymous_cap_cannot_be_bypassed_by_rotating_ips(repo, monkeypatch):
    import app.services.auth as auth_module
    monkeypatch.setattr(auth_module, "MAX_ANONYMOUS_SESSIONS", 3)
    service = AuthService(repo, AuthSettings("http://test"))
    for i in range(3):
        service.issue(NOW, client_ip=f"192.0.2.{i + 1}")
    with pytest.raises(DomainError) as error:
        service.issue(NOW, client_ip="192.0.2.99")
    assert error.value.status_code == 429 and len(repo.list_auth_sessions()) == 3
    assert len(repo.list_auth_throttles()) == 3
    # Successful authenticated rotation must still work at anonymous capacity.
    from app.models.auth import NodumUser
    repo.save_auth_user(NodumUser(id="budget-user", username="budget-user", person_id="manager-1",
                                 password_hash="fixture-no-password", created_at=NOW))
    cookie, _ = service.issue(NOW, user_id="budget-user")
    assert service.user(cookie, NOW).id == "budget-user"
    service.issue(NOW + timedelta(minutes=16), client_ip="192.0.2.99")
    assert len(repo.list_auth_sessions()) == 2  # authenticated row plus new anonymous row


def test_concurrent_anonymous_reservations_do_not_exceed_capacity(repo, monkeypatch):
    import app.services.auth as auth_module
    from concurrent.futures import ThreadPoolExecutor
    monkeypatch.setattr(auth_module, "MAX_ANONYMOUS_SESSIONS", 1)
    service = AuthService(repo, AuthSettings("http://test"))

    def attempt(index):
        try:
            service.issue(NOW, client_ip=f"192.0.2.{index}")
            return 200
        except DomainError as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, [1, 2])) == [200, 429]
    assert len(repo.list_auth_sessions()) == 1
