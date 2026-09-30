"""Documented Ring wire examples, mocked transport, and policy/persistence regressions."""
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import hashlib
import hmac
import json
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

from cryptography.fernet import Fernet
import pytest

from app.api.ring import get_ring_service, receive_verified_ring_code, require_ring_principal
from app.integrations.ring.client import NoRedirect, RingClient, RingRemoteError
from app.integrations.ring.config import RingSettings
from app.main import app
from app.models.ring import RingLinkInput, RingPrincipal
from app.models.access import AccessCheckInput, GuestInviteInput
from app.services.access import check_access
from app.services.guests import create_invitation
from app.services.errors import DomainError
from app.services.ring import RingService, SIGNALS, nonce_for, normalize_devices
from app.sqlite_repository import SQLiteRepository
from conftest import NOW


ACCOUNT = "ava1.ring.account.test"
DEVICE = "ava1.ring.device.sensor"
PRINCIPAL = RingPrincipal(person_id="manager-1", masked_account_identifier="m***r@example.test")


@pytest.fixture
def settings():
    return RingSettings(client_id="test-client", client_secret="test-secret", signing_key="test-signing",
                        encryption_key=Fernet.generate_key().decode())


def link_response(status):
    return {"data": {"type": "app-integrations", "attributes": {"status": status}}}


@pytest.fixture
def remote():
    client = Mock(spec=RingClient)
    client.exchange.return_value = {"access_token": "access-secret", "refresh_token": "refresh-secret",
                                    "expires_in": 14400, "token_type": "Bearer", "scope": "ava"}
    client.profile.return_value = {"data": {"type": "users", "id": ACCOUNT}}
    client.confirm.return_value = link_response("awaiting")
    client.complete.return_value = link_response("completed")
    client.discover.return_value = {"data": [{"id": DEVICE, "type": "devices",
                                            "attributes": {"name": "Utility Flood Sensor"}}]}
    return client


@pytest.fixture
def service(repo, settings, remote):
    return RingService(repo, settings, remote)


def link(service):
    service.receive_code("one-use-code", NOW)
    timestamp = int(NOW.timestamp() * 1000)
    return service.claim(RingLinkInput(time=timestamp,
                        nonce=nonce_for(service.settings.signing_key, timestamp, ACCOUNT)), PRINCIPAL, NOW)


def event(kind="flood_detected", request_id="request-1", event_id="event-1", account_id=ACCOUNT):
    integration = kind.startswith("app_integration_")
    return {"meta": {"version": "1.1", "time": NOW.isoformat(), "request_id": request_id,
                     "account_id": account_id},
            "data": {"id": event_id, "type": kind, "attributes": {
                "source": account_id if integration else DEVICE,
                "source_type": "users" if integration else "devices",
                "timestamp": int(NOW.timestamp() * 1000)}}}


def signed(service, payload=None):
    raw = json.dumps(payload or event(), indent=2).encode()
    signature = "sha256=" + hmac.new(service.settings.signing_key.encode(), raw, hashlib.sha256).hexdigest()
    return raw, signature


def deliver(service, payload=None):
    raw, signature = signed(service, payload)
    return service.receive_event(raw, signature, NOW)


@pytest.mark.parametrize("kind", sorted(SIGNALS))
def test_documented_event_normalization(service, kind):
    result = deliver(service, event(kind))
    saved = service.repository.get_ring_event(result["id"])
    assert saved.signal == SIGNALS[kind]
    assert saved.occurred_at == NOW
    assert json.loads(saved.raw_payload) == event(kind)
    assert service.repository.list_emergencies() == []


@pytest.mark.parametrize("signature", [None, "", "sha256=bad", "SHA256=bad", "é"])
def test_invalid_signature_no_write(service, signature):
    with pytest.raises(DomainError) as exc:
        service.receive_event(b"not-json", signature, NOW)
    assert exc.value.status_code == 401
    assert not service.repository.list_ring_events()


def test_raw_bytes_signature(service):
    raw, signature = signed(service)
    with pytest.raises(DomainError):
        service.receive_event(raw + b" ", signature, NOW)
    assert service.receive_event(raw, signature, NOW)["status"] == "received"


def test_duplicates_by_request_and_event(service):
    first = deliver(service)
    assert deliver(service)["status"] == "duplicate"
    assert deliver(service, event(request_id="new-delivery"))["id"] == first["id"]
    assert len(service.repository.list_ring_events()) == 1


def test_conflicting_delivery_rejected(service):
    deliver(service)
    with pytest.raises(DomainError) as exc:
        deliver(service, event(event_id="different-event"))
    assert exc.value.status_code == 409


@pytest.mark.parametrize("change", ["version", "time", "timestamp", "source_type", "missing", "account"])
def test_malformed_signed_events_rejected(service, change):
    payload = event("app_integration_added")
    if change == "version":
        payload["meta"]["version"] = "2.0"
    elif change == "time":
        payload["meta"]["time"] = "2026-09-29T12:00:00"
    elif change == "timestamp":
        payload["data"]["attributes"]["timestamp"] = True
    elif change == "source_type":
        payload["data"]["attributes"]["source_type"] = "devices"
    elif change == "account":
        payload["data"]["attributes"]["source"] = "other"
    else:
        del payload["data"]["id"]
    with pytest.raises(DomainError) as exc:
        deliver(service, payload)
    assert exc.value.status_code == 400


def test_unknown_event_audited(service):
    saved = service.repository.get_ring_event(deliver(service, event("new_type"))["id"])
    assert saved.signal == "unknown"
    assert saved.status == "received"


def test_unclaimed_encrypted_tokens(service):
    assert service.receive_code("code", NOW) == {"status": "unclaimed"}
    account = service.repository.get_ring_account(service.account_key(ACCOUNT))
    assert "access-secret" not in account.model_dump_json()
    assert "refresh-secret" not in account.model_dump_json()
    assert service.secrets(account)["refresh_token"] == "refresh-secret"
    assert account.owner_id is None
    assert account.expires_at == NOW + timedelta(hours=4)


def test_link_and_nonce_replay(service):
    assert link(service)["status"] == "completed"
    timestamp = int(NOW.timestamp() * 1000)
    with pytest.raises(DomainError) as exc:
        service.claim(RingLinkInput(time=timestamp, nonce=nonce_for(
            service.settings.signing_key, timestamp, ACCOUNT)), PRINCIPAL, NOW)
    assert exc.value.status_code == 409
    service.client.confirm.assert_called_once()
    service.client.complete.assert_called_once()


@pytest.mark.parametrize("offset", [-600001, 1])
def test_nonce_time_window(service, offset):
    service.receive_code("code", NOW)
    timestamp = int(NOW.timestamp() * 1000) + offset
    with pytest.raises(DomainError) as exc:
        service.claim(RingLinkInput(time=timestamp, nonce=nonce_for(
            service.settings.signing_key, timestamp, ACCOUNT)), PRINCIPAL, NOW)
    assert exc.value.status_code == 400
    service.client.confirm.assert_not_called()


def test_bad_nonce(service):
    service.receive_code("code", NOW)
    with pytest.raises(DomainError):
        service.claim(RingLinkInput(time=int(NOW.timestamp()*1000), nonce="x"*43), PRINCIPAL, NOW)
    service.client.confirm.assert_not_called()


def test_link_patch_failure_can_retry_same_owner(service):
    service.client.complete.side_effect = RingRemoteError()
    with pytest.raises(RingRemoteError):
        link(service)
    account = service.repository.get_ring_account(service.account_key(ACCOUNT))
    assert account.status == "awaiting" and account.link_verified
    service.client.complete.side_effect = None
    timestamp = int(NOW.timestamp()*1000)
    payload = RingLinkInput(time=timestamp, nonce=nonce_for(service.settings.signing_key, timestamp, ACCOUNT))
    other = RingPrincipal(person_id="responder-1", masked_account_identifier="r***r@example.test")
    with pytest.raises(DomainError):
        service.claim(payload, other, NOW)
    assert service.claim(payload, PRINCIPAL, NOW)["status"] == "completed"
    service.client.confirm.assert_called_once()


def test_discovery_links_included_resources_not_array_order():
    response = {"data": [{"type": "devices", "id": "sensor", "attributes": {"name": "Water"},
                          "relationships": {"status": {"data": {"type": "device-status", "id": "s1"}}}}],
                "included": [{"type": "device-status", "id": "unrelated", "attributes": {"online": False}},
                             {"type": "device-status", "id": "s1", "attributes": {
                                 "online": True, "flood_detection": {"faulted": True}}}]}
    device = normalize_devices(response)[0]
    assert device.related["status"] == {"online": True, "flood_detection": {"faulted": True}}


@pytest.mark.parametrize("payload", [{}, {"data": {}}, {"data": [{"type": "bad"}]}, {"data": [None]}])
def test_malformed_discovery(service, payload):
    with pytest.raises(RingRemoteError):
        normalize_devices(payload)


def test_token_refresh_rotates_persisted_pair(service):
    link(service)
    service.client.exchange.return_value.update(access_token="rotated-access", refresh_token="rotated-refresh")
    service.discover(ACCOUNT, PRINCIPAL, NOW + timedelta(hours=4))
    account = service.repository.get_ring_account(service.account_key(ACCOUNT))
    assert service.secrets(account) == {"access_token": "rotated-access", "refresh_token": "rotated-refresh"}
    service.client.discover.assert_called_with("rotated-access")
    service.client.exchange.assert_called_with(refresh_token="refresh-secret")


def test_discovery_401_refreshes_once(service):
    link(service)
    service.client.discover.side_effect = [RingRemoteError(401), {"data": []}]
    assert service.discover(ACCOUNT, PRINCIPAL, NOW) == []
    assert service.client.discover.call_count == 2


def test_foreign_account_cannot_discover(service):
    link(service)
    with pytest.raises(DomainError):
        service.discover("other-account", PRINCIPAL, NOW)
    service.client.discover.assert_not_called()


def test_removed_integration_disables_and_erases_tokens(service):
    link(service)
    deliver(service, event("app_integration_removed"))
    account = service.repository.get_ring_account(service.account_key(ACCOUNT))
    assert account.status == "removed" and not account.encrypted_tokens
    with pytest.raises(DomainError):
        service.discover(ACCOUNT, PRINCIPAL, NOW)


def test_flood_bridge_uses_emergency_service_no_permission_grants(service):
    link(service)
    permissions = service.repository.list_permissions()
    orders = service.repository.list_work_orders()
    key = deliver(service)["id"]
    processed = service.process_event(key, PRINCIPAL, "utility-room", NOW)
    incident = service.repository.get_emergency(processed.emergency_id)
    assert incident.emergency_type == "water_leak"
    assert incident.affected_zone_ids == ["utility-room"]
    assert incident.history[0].actor_id == "manager-1"
    assert incident.assigned_responder_ids == []
    assert service.repository.list_permissions() == permissions
    assert service.repository.list_work_orders() == orders
    assert service.process_event(key, PRINCIPAL, "floor-5", NOW) == processed
    assert len(service.repository.list_emergencies()) == 1


@pytest.mark.parametrize("zone", [None, "unknown"])
def test_flood_requires_valid_operator_zone(service, zone):
    link(service)
    key = deliver(service)["id"]
    with pytest.raises(DomainError):
        service.process_event(key, PRINCIPAL, zone, NOW)
    assert not service.repository.list_emergencies()
    assert service.repository.get_ring_event(key).status == "received"


def test_unlinked_event_cannot_create_emergency(service):
    key = deliver(service)["id"]
    with pytest.raises(DomainError):
        service.process_event(key, PRINCIPAL, "utility-room", NOW)
    assert not service.repository.list_emergencies()


def test_freeze_and_cleared_never_create_or_resolve(service):
    link(service)
    flooded = service.process_event(deliver(service)["id"], PRINCIPAL, "utility-room", NOW)
    key = deliver(service, event("freeze_detected", "r2", "e2"))["id"]
    assert service.process_event(key, PRINCIPAL, "utility-room", NOW).status == "review"
    key = deliver(service, event("flood_cleared", "r3", "e3"))["id"]
    service.process_event(key, PRINCIPAL, "utility-room", NOW)
    assert service.repository.get_emergency(flooded.emergency_id).status == "active"
    assert len(service.repository.list_emergencies()) == 1


def test_environment_isolation(service):
    link(service)
    other = RingService(service.repository, replace(service.settings, environment="production"), service.client)
    with pytest.raises(DomainError):
        other.discover(ACCOUNT, PRINCIPAL, NOW)
    deliver(service)
    assert deliver(other)["status"] == "received"
    assert len(service.repository.list_ring_events()) == 2


def test_missing_encryption_key_does_not_spend_code(service):
    service.settings = replace(service.settings, encryption_key="")
    with pytest.raises(DomainError):
        service.receive_code("code", NOW)
    service.client.exchange.assert_not_called()


def test_wrong_encryption_key_fails_closed(service):
    link(service)
    service.settings = replace(service.settings, encryption_key=Fernet.generate_key().decode())
    with pytest.raises(DomainError):
        service.discover(ACCOUNT, PRINCIPAL, NOW)
    service.client.discover.assert_not_called()


def test_restart_preserves_tokens_events_and_emergency(tmp_path, settings, remote):
    url = f"sqlite:///{tmp_path / 'ring.db'}"
    repo = SQLiteRepository(url)
    repo.initialize()
    first = RingService(repo, settings, remote)
    link(first)
    key = deliver(first)["id"]
    result = first.process_event(key, PRINCIPAL, "utility-room", NOW)
    restarted = SQLiteRepository(url)
    restarted.initialize()
    second = RingService(restarted, settings, remote)
    assert second.discover(ACCOUNT, PRINCIPAL, NOW)[0].id == DEVICE
    assert deliver(second)["status"] == "duplicate"
    assert second.process_event(key, PRINCIPAL, "utility-room", NOW) == result
    assert restarted.get_emergency(result.emergency_id).status == "active"
    with restarted.database.transaction() as connection:
        assert [r[0] for r in connection.execute("SELECT version FROM schema_migrations ORDER BY version")] == [1, 2]


def test_http_webhook_and_core_outage(api, service):
    app.dependency_overrides[get_ring_service] = lambda: service
    raw, signature = signed(service)
    status, result = api("POST", "/ring/webhooks", raw=raw, headers=[(b"x-signature", signature.encode())])
    assert status == 200 and result["status"] == "received"
    assert api("POST", "/ring/webhooks", raw=raw)[0] == 401
    assert api("POST", "/ring/webhooks", raw=b"x"*1_048_577)[0] == 413
    link(service)
    app.dependency_overrides[require_ring_principal] = lambda: PRINCIPAL
    service.client.discover.side_effect = RingRemoteError(503)
    assert api("GET", f"/ring/accounts/{ACCOUNT}/devices")[0] == 503
    assert api("GET", "/health") == (200, {"status": "healthy"})
    assert api("GET", "/emergencies/active")[0] == 200


def test_http_adapters_fail_closed(api):
    assert api("POST", "/ring/token-exchange", {"code": "not-trusted"})[0] == 503
    assert api("POST", "/ring/link", {"person_id": "manager-1"})[0] == 503


def test_http_verified_adapter_and_link(api, service):
    app.dependency_overrides[get_ring_service] = lambda: service
    app.dependency_overrides[receive_verified_ring_code] = lambda: "verified-code"
    assert api("POST", "/ring/token-exchange")[1] == {"status": "unclaimed"}
    app.dependency_overrides[require_ring_principal] = lambda: PRINCIPAL
    time_ms = int(NOW.timestamp()*1000)
    status, result = api("POST", "/ring/link", {"time": time_ms,
        "nonce": nonce_for(service.settings.signing_key, time_ms, ACCOUNT)})
    assert status == 200 and result["status"] == "completed"
    assert "access-secret" not in json.dumps(result)
    key = deliver(service)["id"]
    assert api("GET", f"/ring/accounts/{ACCOUNT}/events")[0] == 200
    assert api("POST", f"/ring/events/{key}/process", {"zone_id": "utility-room"})[0] == 200


def test_client_wire_contract(settings):
    client = RingClient(settings)
    client._request = Mock(return_value={})
    client.exchange(code="code")
    args, kwargs = client._request.call_args
    assert args == ("POST", "https://oauth.ring.com/oauth/token")
    assert kwargs["form"] == {"grant_type": "authorization_code", "code": "code",
                              "client_id": "test-client", "client_secret": "test-secret"}
    client.discover("access")
    assert client._request.call_args.args == ("GET", "https://api.amazonvision.com/v1/devices?include=status,capabilities,location,configurations")
    client.confirm("access", "m***r@test", "nonce")
    assert client._request.call_args.kwargs["payload"] == {"account_identifier": "m***r@test", "nonce": "nonce"}
    client.complete("access", "m***r@test")
    assert client._request.call_args.kwargs["payload"]["status"] == "completed"


@pytest.mark.parametrize("error", [URLError("secret"), HTTPError("https://ring", 401, "secret", {}, None)])
def test_client_outage_redacts_remote_error(settings, error):
    client = RingClient(settings)
    client.transport.open = Mock(side_effect=error)
    with pytest.raises(RingRemoteError) as exc:
        client.profile("secret")
    assert "secret" not in exc.value.detail


def test_redirects_never_forward_credentials():
    assert NoRedirect().redirect_request(None, None, 302, "", {}, "https://attacker") is None


@pytest.mark.parametrize("name,value", [("RING_API_BASE_URL", "http://ring"),
                                       ("RING_OAUTH_TOKEN_URL", "https://u:p@ring/token"),
                                       ("RING_ENVIRONMENT", "other")])
def test_invalid_config_isolated(name, value, monkeypatch, api):
    monkeypatch.setenv(name, value)
    with pytest.raises(DomainError):
        RingSettings.from_env()
    assert api("GET", "/health")[0] == 200


def test_flood_policy_changes_only_through_engine(service):
    link(service)
    def allowed(person, zone):
        return check_access(service.repository, AccessCheckInput(
            person_id=person, zone_id=zone, purpose="Ring regression"), NOW).allowed
    assert allowed("plumber-1", "utility-room")
    assert allowed("contractor-1", "machine-room")
    service.process_event(deliver(service)["id"], PRINCIPAL, "utility-room", NOW)
    assert not allowed("plumber-1", "utility-room")  # Needs incident assignment, even with a work order.
    assert allowed("contractor-1", "machine-room")  # Unaffected.
    assert allowed("responder-1", "utility-room")
    assert allowed("manager-1", "utility-room")
    assert not allowed("guest-1", "utility-room")


def test_flood_blocks_existing_guest_permission(service):
    link(service)
    create_invitation(service.repository, GuestInviteInput(
        resident_id="resident-1", guest_id="guest-1", guest_name="Sara", allowed_zone_ids=["floor-5"]), NOW)
    request = AccessCheckInput(person_id="guest-1", zone_id="floor-5", purpose="visit")
    assert check_access(service.repository, request, NOW).allowed
    service.process_event(deliver(service)["id"], PRINCIPAL, "floor-5", NOW)
    assert not check_access(service.repository, request, NOW).allowed


def test_concurrent_webhook_delivery(service):
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: deliver(service), range(8)))
    assert sum(r["status"] == "received" for r in results) == 1
    assert len(service.repository.list_ring_events()) == 1


def test_concurrent_processing_creates_one_incident(service):
    link(service)
    key = deliver(service)["id"]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: service.process_event(key, PRINCIPAL, "utility-room", NOW), range(4)))
    assert len({r.emergency_id for r in results}) == 1
    assert len(service.repository.list_emergencies()) == 1


def test_future_flood_cannot_trigger(service):
    link(service)
    payload = event()
    payload["data"]["attributes"]["timestamp"] += 1000
    with pytest.raises(DomainError) as exc:
        service.process_event(deliver(service, payload)["id"], PRINCIPAL, "utility-room", NOW)
    assert exc.value.status_code == 422
    assert not service.repository.list_emergencies()


def test_refresh_commits_even_if_discovery_fails(service):
    link(service)
    service.client.exchange.return_value.update(access_token="new-access", refresh_token="new-refresh")
    service.client.discover.side_effect = RingRemoteError(503)
    with pytest.raises(RingRemoteError):
        service.discover(ACCOUNT, PRINCIPAL, NOW + timedelta(hours=4))
    assert service.secrets(service.repository.get_ring_account(service.account_key(ACCOUNT)))["refresh_token"] == "new-refresh"


def test_schema_upgrade_preserves_existing_data(tmp_path, monkeypatch):
    import app.database as database
    url = f"sqlite:///{tmp_path / 'upgrade.db'}"
    migrations = database.MIGRATIONS
    monkeypatch.setattr(database, "MIGRATIONS", migrations[:1])
    repo = SQLiteRepository(url)
    repo.initialize()
    before = repo.list_people()
    monkeypatch.setattr(database, "MIGRATIONS", migrations)
    repo.initialize()
    assert repo.list_people() == before
    assert repo.list_ring_events() == []


def test_busy_sqlite_inbox_returns_retryable_failure(tmp_path, settings, remote):
    from time import monotonic
    url = f"sqlite:///{tmp_path / 'busy.db'}"
    locked = SQLiteRepository(url)
    locked.initialize()
    service = RingService(SQLiteRepository(url), settings, remote)
    with locked.transaction():
        started = monotonic()
        with pytest.raises(DomainError) as exc:
            deliver(service)
        assert exc.value.status_code == 503
        assert monotonic() - started < 4
    assert not service.repository.list_ring_events()
    assert deliver(service)["status"] == "received"


@pytest.mark.parametrize("person", ["guest-1", "resident-1", "contractor-1", "unknown"])
def test_nonoperators_cannot_claim(service, person):
    service.receive_code("code", NOW)
    timestamp = int(NOW.timestamp()*1000)
    with pytest.raises(DomainError):
        service.claim(RingLinkInput(time=timestamp, nonce=nonce_for(
            service.settings.signing_key, timestamp, ACCOUNT)),
            RingPrincipal(person_id=person, masked_account_identifier="x***x@test"), NOW)
    service.client.confirm.assert_not_called()
