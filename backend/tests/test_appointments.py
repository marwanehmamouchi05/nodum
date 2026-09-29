from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

import pytest
from pydantic import ValidationError

from app.api.dependencies import utc_now
from app.main import app
from app.models.access import AccessRequest
from app.models.building import Person, PersonRole, Zone, ZoneType
from app.models.business import (
    Appointment, AppointmentCreateInput, AppointmentStatus, Business, VisitorCheckInInput,
)
from app.repository import InMemoryRepository
from app.services.access_engine import evaluate_access
from app.services.appointments import check_in_visitor, create_appointment
from app.services.errors import DomainError


NOW = datetime(2026, 9, 29, 12, tzinfo=timezone.utc)


def appointment_input(**changes):
    values = dict(id="appt-1", visitor_id="visitor-1", visitor_name="Sam",
                  business_id="atlas-dental", destination_zone_id="office-106",
                  appointment_time=NOW + timedelta(minutes=10))
    return AppointmentCreateInput(**(values | changes))


def check_in_input(**changes):
    return VisitorCheckInInput(**(dict(visitor_id="visitor-1", visitor_name="Sam") | changes))


def schedule_and_check_in(repo):
    create_appointment(repo, appointment_input(), NOW)
    return check_in_visitor(repo, "appt-1", check_in_input(), NOW)


def access(repo, zone_id="office-106", at=NOW, request_changes=None, **context):
    values = dict(person_id="visitor-1", zone_id=zone_id,
                  purpose="Appointment", requested_at=at)
    return evaluate_access(
        AccessRequest(**(values | (request_changes or {}))),
        repo.get_person("visitor-1"), repo.get_zone(zone_id),
        context.get("permissions", repo.list_permissions()), repo.list_work_orders(),
        appointments=context.get("appointments", repo.list_appointments()),
        businesses=context.get("businesses", repo.list_businesses()),
    )


def test_http_appointment_flow_and_no_access_at_scheduling(api, repo):
    status, created = api("POST", "/appointments", appointment_input().model_dump(mode="json"))
    assert status == 201
    assert created["status"] == "scheduled" and created["checked_in_at"] is None
    assert created["created_at"] == "2026-09-29T12:00:00Z"
    assert repo.get_person("visitor-1") is None
    assert repo.list_permissions() == []
    assert api("GET", "/appointments/appt-1") == (200, created)
    assert api("GET", "/appointments") == (200, [created])
    status, result = api("POST", "/appointments/appt-1/check-in", check_in_input().model_dump())
    assert status == 200
    assert result["appointment"]["status"] == "checked_in"
    assert result["appointment"]["checked_in_at"] == "2026-09-29T12:00:00Z"
    assert result["permission"]["allowed_zone_ids"] == ["office-106"]
    assert result["permission"]["appointment_id"] == "appt-1"
    assert result["permission"]["business_id"] == "atlas-dental"
    assert repo.get_person("visitor-1").role == PersonRole.BUSINESS_VISITOR
    status, decision = api("POST", "/access/check",
                           dict(person_id="visitor-1", zone_id="office-106", purpose="Visit"))
    assert status == 200 and decision["allowed"]
    assert api("GET", "/guests/permissions") == (200, [])


def test_duplicate_appointment_does_not_overwrite(api, repo):
    payload = appointment_input().model_dump(mode="json")
    assert api("POST", "/appointments", payload)[0] == 201
    assert api("POST", "/appointments", payload | {"visitor_name": "Someone else"})[0] == 409
    assert len(repo.list_appointments()) == 1
    assert repo.get_appointment("appt-1").visitor_name == "Sam"
    assert repo.list_permissions() == []


@pytest.mark.parametrize("changes,status", [
    ({"business_id": "missing"}, 404),
    ({"destination_zone_id": "missing"}, 404),
    ({"destination_zone_id": "floor-5"}, 403),
    ({"destination_zone_id": "machine-room"}, 403),
    ({"destination_zone_id": "lobby"}, 403),
    ({"appointment_time": "2026-09-29T11:59:59Z"}, 422),
    ({"appointment_time": "2026-09-29T12:10:00"}, 422),
    ({"appointment_time": "invalid"}, 422),
    ({"appointment_time": "9999-12-31T23:59:59Z"}, 422),
    ({"appointment_time": "0001-01-01T00:00:00Z"}, 422),
    ({"access_before_minutes": -1}, 422),
    ({"access_before_minutes": 121}, 422),
    ({"access_after_minutes": 0}, 422),
    ({"access_after_minutes": 481}, 422),
    ({"access_after_minutes": 10**20}, 422),
    ({"access_before_minutes": True}, 422),
    ({"access_after_minutes": 1.5}, 422),
    ({"visitor_id": ""}, 422),
    ({"visitor_name": " "}, 422),
    ({"status": "checked_in"}, 422),
    ({"checked_in_at": "2026-09-29T12:00:00Z"}, 422),
    ({"visitor_id": "guest-1", "visitor_name": "Sara"}, 409),
    ({"visitor_id": "contractor-1", "visitor_name": "Ahmed"}, 409),
])
def test_invalid_creation_is_atomic(api, repo, changes, status):
    payload = appointment_input().model_dump(mode="json") | changes
    assert api("POST", "/appointments", payload)[0] == status
    assert repo.list_appointments() == [] and repo.list_permissions() == []
    assert repo.get_person("visitor-1") is None


@pytest.mark.parametrize("kind,restricted,owned,active", [
    (ZoneType.BUSINESS, False, True, False),
    (ZoneType.BUSINESS, True, True, True),
    (ZoneType.BUSINESS, False, False, True),
    (ZoneType.RESIDENTIAL, False, True, True),
    (ZoneType.MAINTENANCE, False, True, True),
])
def test_business_destination_validation_even_if_owned(kind, restricted, owned, active):
    repo = InMemoryRepository(
        zones=[Zone(id="office-106", name="Office", zone_type=kind, restricted=restricted)],
        businesses=[Business(id="atlas-dental", name="Atlas", active=active,
                             destination_zone_ids=["office-106" if owned else "other"])])
    with pytest.raises(DomainError) as exc:
        create_appointment(repo, appointment_input(), NOW)
    assert exc.value.status_code == 403
    assert not repo.list_appointments()


@pytest.mark.parametrize("offset,status", [(-16, 403), (-15, 200), (59, 200), (60, 403), (61, 403)])
def test_check_in_window_http(api, repo, offset, status):
    payload = appointment_input(appointment_time=NOW + timedelta(hours=1))
    assert api("POST", "/appointments", payload.model_dump(mode="json"))[0] == 201
    check_time = payload.appointment_time + timedelta(minutes=offset)
    app.dependency_overrides[utc_now] = lambda: check_time
    response_status, _ = api("POST", "/appointments/appt-1/check-in", check_in_input().model_dump())
    assert response_status == status
    if status != 200:
        assert repo.get_person("visitor-1") is None and repo.list_permissions() == []
        assert repo.get_appointment("appt-1").status == AppointmentStatus.SCHEDULED
    else:
        assert repo.list_permissions()[0].valid_from == check_time


@pytest.mark.parametrize("changes", [{"visitor_id": "other"}, {"visitor_name": "Other"}])
def test_check_in_visitor_mismatch_rejected(api, repo, changes):
    create_appointment(repo, appointment_input(), NOW)
    assert api("POST", "/appointments/appt-1/check-in",
               check_in_input(**changes).model_dump())[0] == 403
    assert not repo.list_permissions() and repo.get_person("visitor-1") is None


def test_unknown_appointment_http(api):
    assert api("GET", "/appointments/missing")[0] == 404
    assert api("POST", "/appointments/missing/check-in", check_in_input().model_dump())[0] == 404


def test_repeat_check_in_does_not_extend_or_duplicate(api, repo):
    schedule_and_check_in(repo)
    before = repo.list_permissions()
    assert api("POST", "/appointments/appt-1/check-in", check_in_input().model_dump())[0] == 409
    assert repo.list_permissions() == before
    assert repo.get_appointment("appt-1").checked_in_at == NOW


@pytest.mark.parametrize("zone_id", ["floor-5", "machine-room", "lobby"])
def test_checked_in_visitor_denied_unrelated_zones(api, repo, zone_id):
    schedule_and_check_in(repo)
    status, result = api("POST", "/access/check",
                         dict(person_id="visitor-1", zone_id=zone_id, purpose="Visit"))
    assert status == 200 and not result["allowed"]


def test_another_business_zone_denied(repo):
    extra = Zone(id="office-107", name="Other business", zone_type=ZoneType.BUSINESS)
    extended = InMemoryRepository(
        zones=[repo.get_zone("office-106"), extra],
        businesses=repo.list_businesses() + [
            Business(id="other", name="Other", destination_zone_ids=["office-107"])])
    schedule_and_check_in(extended)
    assert access(extended).allowed
    assert not access(extended, zone_id="office-107").allowed


@pytest.mark.parametrize("offset,allowed", [(-1, False), (0, True), (69, True), (70, False), (71, False)])
def test_business_permission_time_boundaries(repo, offset, allowed):
    schedule_and_check_in(repo)
    assert access(repo, at=NOW + timedelta(minutes=offset)).allowed is allowed


@pytest.mark.parametrize("changes", [{"person_id": "other"}, {"zone_id": "other"}])
def test_business_request_mismatch_denied(repo, changes):
    schedule_and_check_in(repo)
    assert not access(repo, request_changes=changes).allowed


@pytest.mark.parametrize("changes", [
    {"appointment_id": None}, {"appointment_id": "other"}, {"business_id": "other"},
    {"allowed_zone_ids": ["office-106", "floor-5"]},
    {"valid_from": NOW - timedelta(minutes=1)},
    {"valid_until": NOW + timedelta(days=1)}, {"created_at": None},
    {"granted_by": "other"}, {"id": ""},
])
def test_engine_rejects_tampered_business_grant(repo, changes):
    result = schedule_and_check_in(repo)
    grant = result.permission.model_copy(update=changes)
    assert not access(repo, permissions=[grant]).allowed


@pytest.mark.parametrize("context", ["missing_business", "inactive_business", "unowned_zone",
                                    "missing_appointment", "cancelled", "scheduled", "wrong_visitor"])
def test_engine_requires_current_business_and_checked_in_appointment(repo, context):
    result = schedule_and_check_in(repo)
    businesses = repo.list_businesses()
    appointments = repo.list_appointments()
    if context == "missing_business":
        businesses = []
    elif context == "inactive_business":
        businesses[0].active = False
    elif context == "unowned_zone":
        businesses[0].destination_zone_ids = ["other"]
    elif context == "missing_appointment":
        appointments = []
    elif context in {"cancelled", "scheduled"}:
        appointments[0].status = AppointmentStatus(context)
        appointments[0].checked_in_at = None
    else:
        appointments[0].visitor_id = "other"
    assert not access(repo, appointments=appointments, businesses=businesses).allowed
    assert result.permission.appointment_id == "appt-1"


def test_check_in_revalidates_inactive_business_and_identity(repo):
    appointment = create_appointment(repo, appointment_input(), NOW)
    business = repo.get_business("atlas-dental")
    business.active = False
    inactive = InMemoryRepository(zones=[repo.get_zone("office-106")],
                                  businesses=[business], appointments=[appointment])
    with pytest.raises(DomainError) as exc:
        check_in_visitor(inactive, "appt-1", check_in_input(), NOW)
    assert exc.value.status_code == 403 and not inactive.list_permissions()
    occupied = InMemoryRepository(
        people=[Person(id="visitor-1", name="Sam", role=PersonRole.CONTRACTOR)],
        zones=[repo.get_zone("office-106")], businesses=repo.list_businesses(),
        appointments=[appointment])
    with pytest.raises(DomainError) as exc:
        check_in_visitor(occupied, "appt-1", check_in_input(), NOW)
    assert exc.value.status_code == 409
    assert occupied.get_person("visitor-1").role == PersonRole.CONTRACTOR
    assert not occupied.list_permissions()


def test_overlapping_appointments_cannot_duplicate_permissions(repo):
    schedule_and_check_in(repo)
    create_appointment(repo, appointment_input(id="appt-2"), NOW)
    with pytest.raises(DomainError) as exc:
        check_in_visitor(repo, "appt-2", check_in_input(), NOW)
    assert exc.value.status_code == 409
    assert repo.get_appointment("appt-2").status == AppointmentStatus.SCHEDULED
    assert len(repo.list_permissions()) == 1


def test_expired_permission_can_be_followed_by_new_appointment(repo):
    schedule_and_check_in(repo)
    later = NOW + timedelta(hours=2)
    create_appointment(repo, appointment_input(id="appt-2", appointment_time=later), later)
    check_in_visitor(repo, "appt-2", check_in_input(), later)
    assert len(repo.list_permissions()) == 2 and access(repo, at=later).allowed


def test_scheduling_for_registered_visitor_does_not_grant_access(repo):
    visitor = Person(id="visitor-1", name="Sam", role=PersonRole.BUSINESS_VISITOR)
    repo = InMemoryRepository(people=[visitor], zones=[repo.get_zone("office-106")],
                              businesses=repo.list_businesses())
    create_appointment(repo, appointment_input(), NOW)
    assert not access(repo).allowed


@pytest.mark.parametrize("operation", ["schedule", "check_in"])
def test_concurrent_operations_are_atomic(repo, operation):
    if operation == "check_in":
        create_appointment(repo, appointment_input(), NOW)
    barrier = Barrier(2)

    def run():
        barrier.wait(timeout=5)
        try:
            if operation == "schedule":
                create_appointment(repo, appointment_input(), NOW)
            else:
                check_in_visitor(repo, "appt-1", check_in_input(), NOW)
            return 200
        except DomainError as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert sorted(results) == [200, 409]
    assert len(repo.list_appointments()) == 1
    assert len(repo.list_permissions()) == (1 if operation == "check_in" else 0)


def test_repository_copies_and_deterministic_results(repo):
    created = create_appointment(repo, appointment_input(), NOW)
    created.visitor_name = "Mutated"
    repo.get_business("atlas-dental").active = False
    assert repo.get_appointment("appt-1").visitor_name == "Sam"
    first = check_in_visitor(repo, "appt-1", check_in_input(), NOW)
    second_repo = InMemoryRepository(zones=[repo.get_zone("office-106")],
                                     businesses=repo.list_businesses())
    assert first == schedule_and_check_in(second_repo)
    first.appointment.visitor_name = "Mutated"
    first.permission.allowed_zone_ids.append("machine-room")
    assert access(repo).allowed
    assert repo.get_appointment("appt-1").visitor_name == "Sam"


def test_appointment_timestamps_normalize_to_utc(repo):
    offset = timezone(timedelta(hours=5))
    payload = appointment_input(appointment_time=NOW.astimezone(offset))
    created = create_appointment(repo, payload, NOW.astimezone(offset))
    assert created.appointment_time.tzinfo == timezone.utc
    assert created.created_at.tzinfo == timezone.utc
    result = check_in_visitor(repo, "appt-1", check_in_input(), NOW.astimezone(offset))
    assert result.appointment.checked_in_at.tzinfo == timezone.utc


def test_invalid_appointment_state_rejected():
    with pytest.raises(ValidationError):
        Appointment(**appointment_input().model_dump(), created_at=NOW,
                    status=AppointmentStatus.CHECKED_IN)


def test_new_endpoints_in_openapi(api):
    status, schema = api("GET", "/openapi.json")
    assert status == 200
    assert set(schema["paths"]["/appointments"]) == {"get", "post"}
    assert "/appointments/{appointment_id}/check-in" in schema["paths"]
