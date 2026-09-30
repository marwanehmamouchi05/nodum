"""Policy-first connector contracts, API regression and restart coverage."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from conftest import NOW
from app.integrations.building import ConnectorRegistry
from app.models.access import GuestInviteInput
from app.models.building import Zone
from app.models.emergency import EmergencyCreateInput
from app.models.integrations import (
    ActionInput, CredentialInput, DeviceInput, IntegrationInput, JourneyInput,
    ScanInput, TransitionInput,
)
from app.models.ring import RingDevice, RingPrincipal
from app.services.building import BuildingService
from app.services.emergencies import create_emergency
from app.services.errors import DomainError
from app.services.guests import create_invitation
from app.services.journeys import JourneyService
from app.sqlite_repository import SQLiteRepository


@pytest.fixture
def building(repo):
    service = BuildingService(repo)
    for integration in repo.list_building_integrations():
        service.configure_integration(integration.id, True, "manager-1", NOW)
    return service


def action(**changes):
    return ActionInput(**({"id": "command-1", "person_id": "manager-1", "zone_id": "lobby",
                          "purpose": "Test access", "command": "temporary_unlock"} | changes))


def invite(repo):
    create_invitation(repo, GuestInviteInput(resident_id="resident-1", guest_id="test-guest",
        guest_name="Test Guest", allowed_zone_ids=["lobby", "floor-5"]), NOW)


def demo(repo, connected=True):
    return JourneyService(repo).demo_atlas("demo-1", "manager-1", connected, NOW)


def incident(repo, zone):
    create_emergency(repo, EmergencyCreateInput(emergency_id="incident", emergency_type="fire_alarm",
        severity="high", affected_zone_ids=[zone], description="Test", created_by="manager-1"), NOW)


def test_seeds_disabled_and_no_actuation(repo):
    assert len(repo.list_building_integrations()) == 4
    assert all(not i.enabled for i in repo.list_building_integrations())
    assert len(repo.list_building_devices()) == 6
    assert not repo.list_actuator_events()


@pytest.mark.parametrize("kind", ["access_control", "elevator", "credential_reader", "wayfinding"])
def test_integration_registration(api, kind):
    body = dict(id="custom", name="Demo", kind=kind, actor_id="manager-1")
    status, record = api("POST", "/building/integrations", body)
    assert status == 201 and record["mode"] == "simulated"
    assert api("POST", "/building/integrations", body)[0] == 409


@pytest.mark.parametrize("provider", ["kisi", "salto", "hid", "ring", "https://example.com"])
def test_no_real_manufacturer_registration(api, provider):
    assert api("POST", "/building/integrations", dict(id="x", name="x", provider=provider,
        kind="access_control", actor_id="manager-1"))[0] == 422


@pytest.mark.parametrize("actor", ["guest-1", "resident-1", "contractor-1", "missing"])
def test_inventory_requires_operator(api, actor):
    assert api("PATCH", "/building/integrations/demo-access_control",
               dict(actor_id=actor, enabled=True))[0] in {403, 404}


@pytest.mark.parametrize("device_type,integration,capability", [
    ("door", "access_control", "unlock"), ("smart_lock", "access_control", "lock"),
    ("turnstile", "access_control", "temporary_unlock"),
    ("credential_reader", "credential_reader", "read_credential"),
    ("elevator", "elevator", "call_elevator"),
    ("elevator_floor_controller", "elevator", "authorize_floor"),
    ("navigation_light", "wayfinding", "illuminate_route"),
    ("digital_sign", "wayfinding", "show_destination"),
])
def test_device_registration_and_mapping(api, device_type, integration, capability):
    body = dict(id="custom", integration_id="demo-" + integration, name="Device", device_type=device_type,
                zone_id="lobby", capabilities=[capability], actor_id="manager-1")
    status, record = api("POST", "/building/devices", body)
    assert status == 201 and record["simulated"] is True
    assert api("POST", "/building/devices", body)[0] == 409
    assert api("PUT", "/building/devices/custom/mapping", dict(actor_id="manager-1", zone_ids=["lobby"]))[0] == 200
    assert api("GET", "/building/devices/custom/status")[1]["mapping"]["zone_ids"] == ["lobby"]


@pytest.mark.parametrize("changes,expected", [
    ({"zone_id": "missing"}, 404), ({"capabilities": ["arbitrary"]}, 422),
    ({"metadata": {"secret": "not-public"}}, 422),
    ({"device_type": "elevator"}, 422), ({"integration_id": "missing"}, 404),
])
def test_invalid_device(api, changes, expected):
    body = dict(id="custom", integration_id="demo-access_control", name="Device", device_type="door",
                zone_id="lobby", capabilities=["unlock"], actor_id="manager-1")
    assert api("POST", "/building/devices", body | changes)[0] == expected


@pytest.mark.parametrize("zones,expected", [([], 422), (["missing"], 404), (["lobby", "floor-5"], 422)])
def test_invalid_door_mapping(api, zones, expected):
    assert api("PUT", "/building/devices/demo-entrance/mapping",
               dict(actor_id="manager-1", zone_ids=zones))[0] == expected


@pytest.mark.parametrize("command", ["unlock", "temporary_unlock", "lock"])
def test_allowed_access_audited(building, repo, command):
    response = building.action("demo-entrance", action(command=command), NOW)
    assert response.executed and response.simulated and response.decision.allowed
    assert len(repo.list_actuator_events()) == 1
    assert building.status("demo-entrance", NOW)["state"].locked == (command == "lock")


@pytest.mark.parametrize("person,zone", [("guest-1", "lobby"), ("missing", "lobby"),
    ("contractor-1", "lobby"), ("resident-1", "lobby"), ("manager-1", "missing")])
def test_denied_never_dispatches(building, repo, person, zone):
    adapter = Mock()
    building.registry.access["simulator"] = adapter
    response = building.action("demo-entrance", action(person_id=person, zone_id=zone), NOW)
    assert response.status == "denied" and not response.executed
    adapter.execute.assert_not_called()
    assert not repo.list_actuator_events()


def test_guest_and_contractor_policy_remains_authoritative(building, repo):
    invite(repo)
    assert building.action("demo-entrance", action(person_id="test-guest"), NOW).executed
    building.map_device("demo-entrance", ["machine-room"], "manager-1", NOW)
    assert building.action("demo-entrance", action(id="contractor", person_id="contractor-1", zone_id="machine-room"), NOW).executed
    assert not building.action("demo-entrance", action(id="guest", person_id="test-guest", zone_id="machine-room"), NOW).executed
    order = next(w for w in repo.list_work_orders() if w.id == "wo-001")
    order.active = False
    if isinstance(repo, SQLiteRepository):
        with repo.database.transaction() as connection:
            connection.execute("UPDATE work_orders SET data=? WHERE id=?", (order.model_dump_json(), order.id))
    else:
        repo._work_orders = [order if w.id == order.id else w for w in repo._work_orders]
    assert not building.action("demo-entrance", action(id="inactive", person_id="contractor-1", zone_id="machine-room"), NOW).executed


def test_disabled_and_offline_are_manual(repo, building):
    building.connection("demo-entrance", "offline", "manager-1", NOW)
    assert building.action("demo-entrance", action(), NOW).status == "manual_action_required"
    building.connection("demo-entrance", "online", "manager-1", NOW)
    building.configure_integration("demo-access_control", False, "manager-1", NOW)
    assert building.action("demo-entrance", action(), NOW).status == "manual_action_required"
    assert not repo.list_actuator_events()


def test_command_replay_does_not_extend_unlock(building, repo):
    first = building.action("demo-entrance", action(), NOW)
    assert building.action("demo-entrance", action(), NOW + timedelta(minutes=1)) == first
    assert len(repo.list_actuator_events()) == 1
    assert building.status("demo-entrance", NOW + timedelta(seconds=10))["state"].locked
    with pytest.raises(DomainError, match="conflicts"):
        building.action("demo-entrance", action(command="lock"), NOW)


def test_concurrent_command_replay(building, repo):
    with ThreadPoolExecutor(max_workers=4) as executor:
        outcomes = list(executor.map(lambda _: building.action("demo-entrance", action(), NOW), range(4)))
    assert all(r.executed for r in outcomes)
    assert len(repo.list_actuator_events()) == 1


def test_adapter_failure_audited_without_confirmed_action(building, repo):
    adapter = Mock()
    adapter.execute.side_effect = RuntimeError("private provider details")
    building.registry.access["simulator"] = adapter
    outcome = building.action("demo-entrance", action(), NOW)
    assert outcome.status == "failed" and not outcome.executed
    assert "private" not in outcome.message
    assert repo.get_actuator_event("command-1").status == "failed"
    assert building.status("demo-entrance", NOW)["state"].locked


@pytest.mark.parametrize("kind", ["nfc", "badge", "qr_mobile"])
def test_credential_resolves_person_and_calls_policy(building, repo, kind):
    invite(repo)
    public = building.register_credential(CredentialInput(id="card", kind=kind, value="sample-secret",
        person_id="test-guest"), "manager-1", NOW)
    assert "fingerprint" not in public and "value" not in public
    assert "sample-secret" not in repo.get_credential("card").model_dump_json()
    payload = ScanInput(id="scan", reader_id="demo-reader", kind=kind, value="sample-secret", zone_id="lobby")
    event = building.scan(payload, NOW)
    assert event.person_id == "test-guest" and event.result.executed
    assert building.scan(payload, NOW + timedelta(hours=5)) == event
    assert len(repo.list_credential_events()) == len(repo.list_actuator_events()) == 1
    assert "sample-secret" not in event.model_dump_json()
    with pytest.raises(DomainError, match="conflicts"):
        building.scan(payload.model_copy(update={"value": "other"}), NOW)


@pytest.mark.parametrize("value", ["DEMO-RESIDENT-NFC", "unknown"])
def test_credential_deny_no_actuator(building, repo, value):
    event = building.scan(ScanInput(id="scan", reader_id="demo-reader", kind="nfc", value=value, zone_id="lobby"), NOW)
    assert not event.result.executed and event.result.status == "denied"
    assert not repo.list_actuator_events()


def test_duplicate_credential_rejected(building):
    payload = CredentialInput(id="card", kind="badge", value="card", person_id="manager-1")
    building.register_credential(payload, "manager-1", NOW)
    with pytest.raises(DomainError, match="already"):
        building.register_credential(payload.model_copy(update={"id": "new"}), "manager-1", NOW)


def test_atlas_demo_complete_api(api, repo):
    status, journey = api("POST", "/building/demo/atlas-dental", dict(id="api-demo", actor_id="manager-1"))
    assert status == 200 and journey["status"] == "ready"
    assert journey["current_confirmed_zone_id"] is None
    assert journey["authorized_zone_ids"] == ["lobby", "office-106"]
    assert len(journey["steps"]) == 4 and all(s["result"]["executed"] for s in journey["steps"])
    assert journey["route"] == ["Lobby", "Elevator", "Floor 1 corridor (guidance waypoint)", "Atlas Dental - Office 106"]
    assert repo.get_appointment(journey["appointment_id"]).status == "checked_in"
    assert api("GET", "/building/journeys/" + journey["id"])[1] == journey
    assert len(api("GET", "/building/actuator-events")[1]) == 4


def test_ring_only_recommendations_no_actuation(repo):
    journey = demo(repo, False)
    assert journey.status == "manual_action_required"
    assert all(not s.result.executed for s in journey.steps)
    assert journey.steps[0].result.message == "Visitor verified; manual door action required"
    assert not repo.list_actuator_events()
    assert BuildingService(repo).decision(journey.person_id, "office-106", "Visit", NOW).allowed


def test_elevator_and_wayfinding_scope(repo):
    journey = demo(repo)
    service = BuildingService(repo)
    state = service.status("demo-elevator", NOW)["state"]
    assert state.authorized_floor == 1 and state.authorized_zone_id == "office-106"
    assert state.current_floor == 0 and state.requested_floor == 0
    assert service.status("demo-navigation", NOW)["state"].route == journey.route
    assert service.status("demo-elevator", NOW + timedelta(seconds=10))["state"].authorized_floor is None
    assert service.status("demo-navigation", NOW + timedelta(seconds=10))["state"].route == []


@pytest.mark.parametrize("zone", ["floor-5", "machine-room", "utility-room", "other-office"])
def test_visitor_denied_unrelated_destinations(repo, zone):
    other = Zone(id="other-office", name="Other office", floor=1, zone_type="business")
    if isinstance(repo, SQLiteRepository):
        with repo.database.transaction() as connection:
            connection.execute("INSERT INTO zones (id,data) VALUES (?,?)", (other.id, other.model_dump_json()))
    else:
        repo._zones[other.id] = other
    journey = demo(repo)
    service = BuildingService(repo)
    outcome = service.action("demo-elevator", action(id="forbidden", person_id=journey.person_id,
        zone_id=zone, command="authorize_floor", journey_id=journey.id), NOW)
    assert outcome.status == "denied" and not outcome.executed
    assert len(repo.list_actuator_events()) == 4
    assert not service.decision(journey.person_id, zone, "visit", NOW).allowed


def test_normal_lobby_access_unchanged_and_journey_person_bound(repo):
    journey = demo(repo)
    service = BuildingService(repo)
    assert not service.decision(journey.person_id, "lobby", "visit", NOW).allowed
    assert service.decision(journey.person_id, "lobby", "visit", NOW, journey).allowed
    assert not service.action("demo-entrance", action(id="wrong-person", journey_id=journey.id), NOW).executed


@pytest.mark.parametrize("zone", ["lobby", "office-106"])
def test_emergency_blocks_journey_commands(repo, zone):
    journey = demo(repo)
    incident(repo, zone)
    outcome = BuildingService(repo).action("demo-entrance", action(id="new", person_id=journey.person_id,
        journey_id=journey.id), NOW)
    assert outcome.status == "denied"
    assert len(repo.list_actuator_events()) == 4


def test_expired_journey_no_commands(repo):
    journey = demo(repo)
    outcome = BuildingService(repo).action("demo-entrance", action(id="late", person_id=journey.person_id,
        journey_id=journey.id), NOW + timedelta(days=1))
    assert outcome.status == "denied" and len(repo.list_actuator_events()) == 4


def test_denied_journey_has_no_route_or_actuation(repo):
    journey = JourneyService(repo).create(JourneyInput(id="denied", person_id="guest-1", purpose="Visit",
        starting_zone_id="lobby", destination_zone_id="machine-room"), NOW)
    assert journey.status == "denied" and journey.route == []
    assert not repo.list_actuator_events()


def test_wayfinding_without_authorized_journey_rejected(building, repo):
    with pytest.raises(DomainError, match="requires"):
        building.action("demo-navigation", action(command="illuminate_route"), NOW)
    assert not repo.list_actuator_events()


def test_demo_replay_safe(repo):
    first = demo(repo)
    assert demo(repo) == first
    assert len(repo.list_actuator_events()) == 4
    assert len(repo.list_journeys()) == 1


def test_explicit_transitions_only(repo):
    journey = demo(repo)
    service = JourneyService(repo)
    destination = TransitionInput(id="end", source_device_id="demo-office-reader", zone_id="office-106")
    with pytest.raises(DomainError, match="next"):
        service.confirm_transition(journey.id, destination, NOW)
    start = TransitionInput(id="start", source_device_id="demo-reader", zone_id="lobby")
    first = service.confirm_transition(journey.id, start, NOW)
    assert service.confirm_transition(journey.id, start, NOW) == first
    assert service.get(journey.id).current_confirmed_zone_id == "lobby"
    service.confirm_transition(journey.id, destination, NOW + timedelta(seconds=1))
    assert service.get(journey.id).status == "completed"
    assert len(repo.list_journey_transitions()) == 2
    assert len(repo.list_actuator_events()) == 4  # Confirmation never operates a door.


def test_wrong_confirmation_device_rejected(repo):
    journey = demo(repo)
    with pytest.raises(DomainError, match="does not serve"):
        JourneyService(repo).confirm_transition(journey.id,
            TransitionInput(id="wrong", source_device_id="demo-office-reader", zone_id="lobby"), NOW)
    assert repo.get_journey(journey.id).current_confirmed_zone_id is None


def test_ring_inventory_readonly_discovery_bound(repo):
    remote = Mock()
    remote.discover.return_value = [RingDevice(id="real-id", name="Entrance Ring", attributes={}, related={"status": {"online": True}})]
    remote.account_key.return_value = "account-key"
    principal = RingPrincipal(person_id="manager-1", masked_account_identifier="m***")
    service = BuildingService(repo)
    device = service.import_ring_device("account", "real-id", "lobby", principal, remote, NOW)
    remote.discover.assert_called_once_with("account", principal, NOW)
    assert not device.simulated and device.provider == "ring"
    assert service.status(device.id, NOW)["state"] is None
    with pytest.raises(DomainError):
        service.action(device.id, action(), NOW)
    journey = demo(repo)
    with pytest.raises(DomainError):
        JourneyService(repo).confirm_transition(journey.id,
            TransitionInput(id="ring-motion", source_device_id=device.id, zone_id="lobby"), NOW)
    with pytest.raises(DomainError, match="not returned"):
        service.import_ring_device("account", "made-up", "lobby", principal, remote, NOW)


def test_restart_preserves_inventory_journey_audit_credentials(tmp_path):
    url = f"sqlite:///{tmp_path / 'building.db'}"
    first = SQLiteRepository(url)
    first.initialize()
    journey = demo(first)
    service = BuildingService(first)
    service.register_credential(CredentialInput(id="visitor", kind="qr_mobile", value="demo-qr", person_id=journey.person_id), "manager-1", NOW)
    scan = ScanInput(id="visitor-scan", reader_id="demo-office-reader", zone_id="office-106", kind="qr_mobile", value="demo-qr")
    service.scan(scan, NOW)
    JourneyService(first).confirm_transition(journey.id, TransitionInput(id="arrival", source_device_id="demo-reader", zone_id="lobby"), NOW)
    second = SQLiteRepository(url)
    second.initialize()
    second.initialize()
    assert len(second.list_building_devices()) == 6 and len(second.list_credentials()) == 2
    assert all(i.enabled for i in second.list_building_integrations())
    assert second.get_journey(journey.id).current_confirmed_zone_id == "lobby"
    assert len(second.list_journey_transitions()) == 1 and len(second.list_actuator_events()) == 5
    assert BuildingService(second).scan(scan, NOW).result.executed
    assert len(second.list_actuator_events()) == 5
    assert BuildingService(second).decision(journey.person_id, "office-106", "Visit", NOW).allowed
    assert second.get_actuator_event("scan-visitor-scan").at.tzinfo is not None


def test_v2_upgrade_preserves_state(tmp_path, monkeypatch):
    import app.database as database
    from app.repository import create_demo_repository
    migrations = database.MIGRATIONS
    repo = SQLiteRepository(f"sqlite:///{tmp_path / 'v2.db'}")
    monkeypatch.setattr(database, "MIGRATIONS", migrations[:2])
    repo.database.initialize()
    person = create_demo_repository().get_person("manager-1")
    person.name = "Existing Manager"
    with repo.database.transaction() as connection:
        connection.execute("INSERT INTO people (id,data) VALUES (?,?)", (person.id, person.model_dump_json()))
    monkeypatch.setattr(database, "MIGRATIONS", migrations)
    repo.initialize()
    assert repo.get_person("manager-1").name == "Existing Manager"
    assert len(repo.list_building_devices()) == 6


@pytest.mark.parametrize("seconds", [0, 31, True])
def test_duration_bounded(seconds):
    with pytest.raises(ValidationError):
        action(duration_seconds=seconds)
