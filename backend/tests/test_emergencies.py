from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

import pytest
from pydantic import ValidationError

from app.models.access import AccessRequest, GuestInviteInput
from app.models.building import WorkOrder
from app.models.business import AppointmentCreateInput, VisitorCheckInInput
from app.models.emergency import (
    EmergencyAssignInput, EmergencyCreateInput,
    EmergencyResolveInput, EmergencyStatus, EmergencyType,
)
from app.repository import InMemoryRepository, create_demo_repository
from app.services.access_engine import evaluate_access
from app.services.appointments import create_appointment, check_in_visitor
from app.services.emergencies import create_emergency, resolve_emergency, assign_responders
from app.services.errors import DomainError
from app.services.guests import create_invitation


NOW = datetime(2026, 9, 29, 12, tzinfo=timezone.utc)


def emergency_input(**changes):
    return EmergencyCreateInput(**(dict(
        emergency_id="incident-1", emergency_type="water_leak", severity="high",
        affected_zone_ids=["utility-room"], description="Water leaking at the supply valve",
        created_by="manager-1",
    ) | changes))


def trigger(repo, **changes):
    return create_emergency(repo, emergency_input(**changes), NOW)


def resolve(repo, emergency_id="incident-1", at=NOW):
    return resolve_emergency(repo, emergency_id,
                             EmergencyResolveInput(resolved_by="manager-1"), at)


def access(repo, person_id="contractor-1", zone_id="machine-room", **changes):
    request = AccessRequest(
        person_id=changes.pop("request_person", person_id),
        zone_id=changes.pop("request_zone", zone_id), purpose="Test",
        requested_at=NOW,
    )
    return evaluate_access(
        request, repo.get_person(person_id), repo.get_zone(zone_id),
        changes.get("permissions", repo.list_permissions()),
        changes.get("work_orders", repo.list_work_orders()),
        appointments=repo.list_appointments(), businesses=repo.list_businesses(),
        emergencies=changes.get("emergencies", repo.list_emergencies()),
    )


def invite_guest(repo):
    create_invitation(repo, GuestInviteInput(
        resident_id="resident-1", guest_id="guest-1", guest_name="Sara",
        allowed_zone_ids=["floor-5", "lobby"],
    ), NOW)


def check_in_business_visitor(repo):
    create_appointment(repo, AppointmentCreateInput(
        id="appointment-1", visitor_id="visitor-1", visitor_name="Sam",
        business_id="atlas-dental", destination_zone_id="office-106", appointment_time=NOW,
    ), NOW)
    check_in_visitor(repo, "appointment-1",
                     VisitorCheckInInput(visitor_id="visitor-1", visitor_name="Sam"), NOW)


def test_create_list_get_resolve_http(api, repo):
    assert api("GET", "/emergencies/active") == (200, [])
    status, created = api("POST", "/emergencies", emergency_input().model_dump(mode="json"))
    assert status == 201
    assert created["status"] == "active"
    assert created["created_at"] == "2026-09-29T12:00:00Z"
    assert created["created_by"] == "manager-1"
    assert created["resolved_at"] is None
    assert created["history"][0]["action"] == "triggered"
    assert api("GET", "/emergencies") == (200, [created])
    assert api("GET", "/emergencies/active") == (200, [created])
    assert api("GET", "/emergencies/incident-1") == (200, created)
    status, resolved = api("POST", "/emergencies/incident-1/resolve", {"resolved_by": "manager-1"})
    assert status == 200 and resolved["status"] == "resolved"
    assert resolved["resolved_at"] == "2026-09-29T12:00:00Z"
    assert resolved["resolved_by"] == "manager-1"
    assert resolved["history"][:-1] == created["history"]
    assert resolved["history"][-1]["action"] == "resolved"
    assert api("GET", "/emergencies/active") == (200, [])
    assert api("GET", "/emergencies") == (200, [resolved])
    assert repo.list_permissions() == []


@pytest.mark.parametrize("kind", ["water_leak", "fire_alarm", "elevator_failure", "security_incident"])
@pytest.mark.parametrize("severity", ["low", "medium", "high", "critical"])
def test_supported_types_and_severities(api, kind, severity):
    payload = emergency_input(emergency_type=kind, severity=severity).model_dump(mode="json")
    assert api("POST", "/emergencies", payload)[0] == 201


@pytest.mark.parametrize("changes,status", [
    ({"emergency_id": ""}, 422), ({"emergency_id": "active"}, 422),
    ({"affected_zone_ids": []}, 422), ({"affected_zone_ids": ["missing"]}, 404),
    ({"affected_zone_ids": ["utility-room", "missing"]}, 404),
    ({"severity": "urgent"}, 422), ({"emergency_type": "earthquake"}, 422),
    ({"description": " "}, 422), ({"created_by": "missing"}, 404),
    ({"created_by": "guest-1"}, 403), ({"created_by": "contractor-1"}, 403),
    ({"status": "resolved"}, 422), ({"created_at": NOW.isoformat()}, 422),
    ({"resolved_at": NOW.isoformat()}, 422), ({"history": []}, 422),
    ({"assigned_responder_ids": ["missing"]}, 404),
    ({"assigned_responder_ids": ["guest-1"]}, 403),
    ({"assigned_responder_ids": ["contractor-1"]}, 403),
    ({"emergency_type": "fire_alarm", "assigned_responder_ids": ["plumber-1"]}, 403),
    ({"emergency_type": "security_incident", "assigned_responder_ids": ["plumber-1"]}, 403),
])
def test_invalid_creation_does_not_write(api, repo, changes, status):
    payload = emergency_input().model_dump(mode="json") | changes
    assert api("POST", "/emergencies", payload)[0] == status
    assert repo.list_emergencies() == []


def test_duplicate_id_rejected_even_after_resolution(api, repo):
    initial = trigger(repo)
    payload = emergency_input(description="Replacement").model_dump(mode="json")
    assert api("POST", "/emergencies", payload)[0] == 409
    assert repo.get_emergency("incident-1") == initial
    resolved = resolve(repo)
    assert api("POST", "/emergencies", payload)[0] == 409
    assert repo.get_emergency("incident-1") == resolved


def test_double_resolution_rejected(api, repo):
    trigger(repo)
    resolved = resolve(repo)
    assert api("POST", "/emergencies/incident-1/resolve", {"resolved_by": "manager-1"})[0] == 409
    assert repo.get_emergency("incident-1") == resolved


def test_missing_incident_returns_404(api):
    assert api("GET", "/emergencies/missing")[0] == 404
    assert api("POST", "/emergencies/missing/resolve", {"resolved_by": "manager-1"})[0] == 404
    assert api("POST", "/emergencies/missing/responders",
               {"assigned_by": "manager-1", "responder_ids": ["responder-1"]})[0] == 404


def test_guest_emergency_block_and_resolution_http(api, repo):
    invite_guest(repo)
    request = dict(person_id="guest-1", zone_id="floor-5", purpose="Visit")
    assert api("POST", "/access/check", request)[1]["allowed"]
    trigger(repo, affected_zone_ids=["floor-5"])
    result = api("POST", "/access/check", request)[1]
    assert not result["allowed"] and "incident-1" in result["reason"]
    assert access(repo, person_id="guest-1", zone_id="lobby").allowed
    resolve(repo)
    assert api("POST", "/access/check", request)[1]["allowed"]


def test_business_visitor_block_and_resolution_http(api, repo):
    check_in_business_visitor(repo)
    request = dict(person_id="visitor-1", zone_id="office-106", purpose="Appointment")
    assert api("POST", "/access/check", request)[1]["allowed"]
    trigger(repo, affected_zone_ids=["office-106"])
    assert not api("POST", "/access/check", request)[1]["allowed"]
    resolve(repo)
    assert api("POST", "/access/check", request)[1]["allowed"]


def test_unaffected_guest_business_and_contractor_behave_normally(repo):
    invite_guest(repo)
    check_in_business_visitor(repo)
    trigger(repo)
    assert access(repo, person_id="guest-1", zone_id="floor-5").allowed
    assert access(repo, person_id="visitor-1", zone_id="office-106").allowed
    assert access(repo).allowed
    assert not access(repo, person_id="guest-1", zone_id="machine-room").allowed


@pytest.mark.parametrize("person_id", ["manager-1", "responder-1"])
@pytest.mark.parametrize("kind", ["water_leak", "fire_alarm", "elevator_failure", "security_incident"])
def test_privileged_override_preserved(repo, person_id, kind):
    trigger(repo, emergency_type=kind)
    assert access(repo, person_id=person_id, zone_id="utility-room").allowed
    assert access(repo, person_id=person_id, zone_id="floor-5").allowed


@pytest.mark.parametrize("kind", ["water_leak", "elevator_failure"])
def test_assigned_contractor_needs_active_matching_order(repo, kind):
    trigger(repo, emergency_type=kind, affected_zone_ids=["machine-room"],
            assigned_responder_ids=["contractor-1"])
    assert access(repo).allowed
    assert not access(repo, work_orders=[]).allowed
    inactive = repo.list_work_orders()
    for order in inactive:
        order.active = False
    assert not access(repo, work_orders=inactive).allowed
    wrong = WorkOrder(id="wrong", contractor_id="someone-else",
                      description="Repair", allowed_zone_ids=["machine-room"])
    assert not access(repo, work_orders=[wrong]).allowed
    wrong_zone = WorkOrder(id="wrong-zone", contractor_id="contractor-1",
                           description="Repair", allowed_zone_ids=["utility-room"])
    assert not access(repo, work_orders=[wrong_zone]).allowed


def test_unassigned_contractor_denied_then_assignment_allows_http(api, repo):
    trigger(repo, emergency_type="elevator_failure", affected_zone_ids=["machine-room"])
    assert not access(repo).allowed
    status, assigned = api("POST", "/emergencies/incident-1/responders",
                           {"assigned_by": "manager-1", "responder_ids": ["contractor-1"]})
    assert status == 200 and assigned["assigned_responder_ids"] == ["contractor-1"]
    assert assigned["history"][-1]["actor_id"] == "manager-1"
    assert assigned["history"][-1]["action"] == "responders_assigned"
    assert access(repo).allowed


@pytest.mark.parametrize("kind", ["fire_alarm", "security_incident"])
def test_fire_security_deny_even_assigned_contractor(repo, kind):
    incident = trigger(repo, affected_zone_ids=["machine-room"],
                       assigned_responder_ids=["contractor-1"])
    # Even a persisted assignment cannot bypass the incident-type restriction.
    changed = incident.model_copy(update={"emergency_type": EmergencyType(kind)})
    assert not access(repo, emergencies=[changed]).allowed


def test_nonmaintenance_zone_denies_assigned_contractor(repo):
    incident = trigger(repo, affected_zone_ids=["machine-room", "floor-5"],
                       assigned_responder_ids=["contractor-1"])
    order = WorkOrder(id="broad", contractor_id="contractor-1", description="Repair",
                      allowed_zone_ids=["machine-room", "floor-5"])
    assert not access(repo, zone_id="floor-5", work_orders=[order], emergencies=[incident]).allowed


def test_overlapping_emergencies_require_every_incident_to_allow(repo):
    trigger(repo, affected_zone_ids=["machine-room"], assigned_responder_ids=["contractor-1"])
    trigger(repo, emergency_id="incident-2", emergency_type="elevator_failure",
            affected_zone_ids=["machine-room"])
    assert not access(repo).allowed
    assign_responders(repo, "incident-2",
                      EmergencyAssignInput(assigned_by="manager-1", responder_ids=["contractor-1"]), NOW)
    assert access(repo).allowed
    trigger(repo, emergency_id="fire", emergency_type="fire_alarm", affected_zone_ids=["machine-room"])
    assert not access(repo).allowed
    resolve(repo, "fire")
    assert access(repo).allowed


def test_resolving_one_incident_does_not_clear_another(repo):
    invite_guest(repo)
    trigger(repo, affected_zone_ids=["floor-5"])
    trigger(repo, emergency_id="incident-2", affected_zone_ids=["floor-5"])
    resolve(repo)
    assert not access(repo, person_id="guest-1", zone_id="floor-5").allowed


@pytest.mark.parametrize("person_id", ["manager-1", "responder-1", "contractor-1", "guest-1"])
@pytest.mark.parametrize("changes", [{"request_person": "wrong"}, {"request_zone": "wrong"}])
def test_mismatched_context_denied_before_emergency_override(repo, person_id, changes):
    trigger(repo, affected_zone_ids=["machine-room"], assigned_responder_ids=["contractor-1"])
    assert not access(repo, person_id=person_id, **changes).allowed


@pytest.mark.parametrize("mutation", ["empty_zones", "invalid_status", "naive_time",
                                     "inconsistent_resolution", "missing_history", "bad_assignments"])
def test_invalid_emergency_data_fails_closed_even_for_manager(repo, mutation):
    incident = trigger(repo)
    if mutation == "empty_zones":
        incident.affected_zone_ids = []
    elif mutation == "invalid_status":
        incident.status = "invalid"
        with pytest.warns(UserWarning, match="Pydantic serializer warnings"):
            assert not access(repo, person_id="manager-1", emergencies=[incident]).allowed
        return
    elif mutation == "naive_time":
        incident.created_at = NOW.replace(tzinfo=None)
    elif mutation == "inconsistent_resolution":
        incident.status = EmergencyStatus.RESOLVED
    elif mutation == "missing_history":
        incident.history = []
    else:
        incident.assigned_responder_ids = ["contractor-1"]
    assert not access(repo, person_id="manager-1", emergencies=[incident]).allowed


def test_duplicate_emergency_snapshot_fails_closed(repo):
    incident = trigger(repo)
    assert not access(repo, person_id="manager-1", emergencies=[incident, incident]).allowed


@pytest.mark.parametrize("changes,status", [
    ({"assigned_by": "guest-1"}, 403), ({"assigned_by": "missing"}, 404),
    ({"responder_ids": ["missing"]}, 404), ({"responder_ids": ["guest-1"]}, 403),
    ({"responder_ids": ["contractor-1"]}, 403), ({"responder_ids": []}, 422),
    ({"responder_ids": ["plumber-1", "missing"]}, 404),
])
def test_assignment_validation_is_atomic(api, repo, changes, status):
    original = trigger(repo)
    payload = {"assigned_by": "manager-1", "responder_ids": ["responder-1"]} | changes
    assert api("POST", "/emergencies/incident-1/responders", payload)[0] == status
    assert repo.get_emergency("incident-1") == original


@pytest.mark.parametrize("operator,status", [("guest-1", 403), ("missing", 404)])
def test_resolution_actor_validation(api, repo, operator, status):
    original = trigger(repo)
    assert api("POST", "/emergencies/incident-1/resolve", {"resolved_by": operator})[0] == status
    assert repo.get_emergency("incident-1") == original


def test_responder_can_manage_and_assignment_history_is_preserved(repo):
    initial = trigger(repo, created_by="responder-1",
                      affected_zone_ids=["utility-room", "utility-room"],
                      assigned_responder_ids=["plumber-1", "plumber-1"])
    assert initial.affected_zone_ids == ["utility-room"]
    assert initial.assigned_responder_ids == ["plumber-1"]
    assigned = assign_responders(repo, "incident-1",
        EmergencyAssignInput(assigned_by="responder-1", responder_ids=["responder-1", "plumber-1"]),
        NOW + timedelta(minutes=1))
    assert assigned.history[-1].responder_ids == ["responder-1"]
    resolved = resolve_emergency(repo, "incident-1",
        EmergencyResolveInput(resolved_by="responder-1"), NOW + timedelta(minutes=2))
    assert resolved.history[:-1] == assigned.history
    assert resolved.created_by == "responder-1"
    assert resolved.assigned_responder_ids == ["plumber-1", "responder-1"]


def test_assignment_after_resolution_and_duplicate_assignment_rejected(repo):
    trigger(repo, assigned_responder_ids=["plumber-1"])
    payload = EmergencyAssignInput(assigned_by="manager-1", responder_ids=["plumber-1"])
    with pytest.raises(DomainError) as exc:
        assign_responders(repo, "incident-1", payload, NOW)
    assert exc.value.status_code == 409
    resolved = resolve(repo)
    with pytest.raises(DomainError) as exc:
        assign_responders(repo, "incident-1", payload, NOW)
    assert exc.value.status_code == 409 and repo.get_emergency("incident-1") == resolved


@pytest.mark.parametrize("operation", ["resolve", "assign"])
def test_backdated_transition_rejected(repo, operation):
    original = trigger(repo)
    with pytest.raises(DomainError) as exc:
        if operation == "resolve":
            resolve(repo, at=NOW - timedelta(seconds=1))
        else:
            assign_responders(repo, "incident-1",
                EmergencyAssignInput(assigned_by="manager-1", responder_ids=["plumber-1"]),
                NOW - timedelta(seconds=1))
    assert exc.value.status_code == 422 and repo.get_emergency("incident-1") == original


@pytest.mark.parametrize("operation", ["create", "resolve", "assign"])
def test_concurrent_transitions_are_atomic(repo, operation):
    if operation != "create":
        trigger(repo)
    barrier = Barrier(2)

    def run():
        barrier.wait(timeout=5)
        try:
            if operation == "create":
                trigger(repo)
            elif operation == "resolve":
                resolve(repo)
            else:
                assign_responders(repo, "incident-1",
                    EmergencyAssignInput(assigned_by="manager-1", responder_ids=["plumber-1"]), NOW)
            return 200
        except DomainError as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert sorted(results) == [200, 409]
    assert len(repo.list_emergencies()) == 1
    assert len(repo.get_emergency("incident-1").history) == (1 if operation == "create" else 2)


def test_repository_defensive_copies_and_sorted_lists(repo):
    created = trigger(repo, emergency_id="z")
    trigger(repo, emergency_id="a")
    created.affected_zone_ids.append("floor-5")
    created.history[0].actor_id = "changed"
    repo.get_emergency("z").assigned_responder_ids.append("guest-1")
    assert [e.emergency_id for e in repo.list_emergencies()] == ["a", "z"]
    stored = repo.get_emergency("z")
    assert stored.affected_zone_ids == ["utility-room"]
    assert stored.history[0].actor_id == "manager-1"
    assert stored.assigned_responder_ids == []


def test_utc_normalization_and_naive_time_rejection(repo):
    offset = timezone(timedelta(hours=5))
    incident = create_emergency(repo, emergency_input(), NOW.astimezone(offset))
    assert incident.created_at.tzinfo == timezone.utc
    assert incident.history[0].at == NOW
    with pytest.raises(ValidationError):
        resolve(repo, at=NOW.replace(tzinfo=None))


def test_demo_support_has_no_startup_incidents(repo):
    assert create_demo_repository().list_emergencies() == []
    trigger(repo, assigned_responder_ids=["plumber-1"])
    assert access(repo, person_id="plumber-1", zone_id="utility-room").allowed
    trigger(repo, emergency_id="elevator-1", emergency_type="elevator_failure",
            affected_zone_ids=["machine-room"], assigned_responder_ids=["contractor-1"])
    assert access(repo).allowed


def test_no_work_order_cannot_be_assigned(repo):
    isolated = InMemoryRepository(
        people=[repo.get_person("manager-1"), repo.get_person("plumber-1")],
        zones=[repo.get_zone("utility-room")])
    with pytest.raises(DomainError) as exc:
        trigger(isolated, assigned_responder_ids=["plumber-1"])
    assert exc.value.status_code == 403 and isolated.list_emergencies() == []


def test_openapi_emergency_endpoints(api):
    status, schema = api("GET", "/openapi.json")
    assert status == 200
    assert set(schema["paths"]["/emergencies"]) == {"get", "post"}
    assert "/emergencies/active" in schema["paths"]
    assert "/emergencies/{emergency_id}/resolve" in schema["paths"]
    assert "/emergencies/{emergency_id}/responders" in schema["paths"]
