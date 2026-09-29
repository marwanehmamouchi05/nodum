"""Service, policy, concurrency, and HTTP regression tests; no external services."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

import pytest
from pydantic import ValidationError

from app.models.access import AccessPermission, AccessRequest, GuestInviteInput
from app.models.building import Person, PersonRole, WorkOrder, Zone, ZoneType
from app.repository import InMemoryRepository, create_demo_repository
from app.services.access_engine import evaluate_access
from app.services.errors import DomainError
from app.services.guests import create_invitation


NOW = datetime(2026, 9, 29, 12, tzinfo=timezone.utc)


def invitation(**changes):
    values = dict(resident_id="resident-1", guest_id="new-guest",
                  guest_name="New Guest", allowed_zone_ids=["floor-5"])
    return GuestInviteInput(**(values | changes))


def permission(**changes):
    values = dict(person_id="guest-1", allowed_zone_ids=["floor-5"],
                  valid_from=NOW - timedelta(hours=1),
                  valid_until=NOW + timedelta(hours=1), reason="Test permission")
    return AccessPermission(**(values | changes))


def decision(repo, *, person_id="guest-1", zone_id="floor-5",
             permissions=(), work_orders=(), request_changes=None):
    request = AccessRequest(**(dict(person_id=person_id, zone_id=zone_id,
                                    purpose="Test", requested_at=NOW)
                               | (request_changes or {})))
    return evaluate_access(request, repo.get_person(person_id), repo.get_zone(zone_id),
                           list(permissions), list(work_orders))



def test_valid_resident_invitation_registers_guest_and_grants_access(api, repo):
    status, body = api("POST", "/guests/invite", invitation().model_dump())
    assert status == 200
    assert body["status"] == "approved"
    assert repo.get_person("new-guest").role == PersonRole.GUEST
    assert body["permission"]["granted_by"] == "resident-1"
    assert body["permission"]["id"]
    assert body["permission"]["created_at"].endswith("Z")
    status, access = api("POST", "/access/check",
                        dict(person_id="new-guest", zone_id="floor-5", purpose="Visit"))
    assert status == 200 and access["allowed"] is True
    status, access = api("POST", "/access/check",
                        dict(person_id="new-guest", zone_id="lobby", purpose="Visit"))
    assert status == 200 and access["allowed"] is False
    status, stored = api("GET", "/guests/permissions")
    assert status == 200 and stored == [body["permission"]]


@pytest.mark.parametrize("changes,status", [
    ({"resident_id": "unknown"}, 404),
    ({"resident_id": "guest-1"}, 403),
    ({"resident_id": "contractor-1"}, 403),
    ({"allowed_zone_ids": ["unknown"]}, 404),
    ({"allowed_zone_ids": ["floor-5", "unknown"]}, 404),
    ({"allowed_zone_ids": ["machine-room"]}, 403),
    ({"resident_id": "manager-1", "allowed_zone_ids": ["machine-room"]}, 403),
    ({"guest_id": "contractor-1"}, 409),
    ({"guest_id": "resident-1"}, 409),
    ({"guest_id": "guest-1", "guest_name": "Different name"}, 409),
    ({"valid_for_hours": 0}, 422),
    ({"valid_for_hours": -1}, 422),
    ({"valid_for_hours": 25}, 422),
    ({"valid_for_hours": 10**20}, 422),
    ({"valid_for_hours": True}, 422),
    ({"valid_for_hours": 1.5}, 422),
    ({"allowed_zone_ids": []}, 422),
    ({"guest_name": " "}, 422),
    ({"guest_id": ""}, 422),
])
def test_invalid_invitations_rejected_without_writes(api, repo, changes, status):
    payload = invitation().model_dump() | changes
    response_status, _ = api("POST", "/guests/invite", payload)
    assert response_status == status
    assert repo.list_permissions() == []
    assert repo.get_person("new-guest") is None
    assert repo.get_person("contractor-1").role == PersonRole.CONTRACTOR


def test_resident_authority_and_manager_scope():
    zones = [Zone(id="other-floor", name="Other floor", zone_type=ZoneType.RESIDENTIAL)]
    people = [Person(id="resident", name="Resident", role=PersonRole.RESIDENT),
              Person(id="manager", name="Manager", role=PersonRole.MANAGER)]
    repo = InMemoryRepository(people=people, zones=zones)
    with pytest.raises(DomainError) as exc:
        create_invitation(repo, invitation(resident_id="resident", allowed_zone_ids=["other-floor"]), NOW)
    assert exc.value.status_code == 403
    result = create_invitation(repo, invitation(resident_id="manager", allowed_zone_ids=["other-floor"]), NOW)
    assert result["permission"].granted_by == "manager"


@pytest.mark.parametrize("kind,restricted", [
    (ZoneType.RESIDENTIAL, True), (ZoneType.LOBBY, True),
    (ZoneType.MAINTENANCE, False), (ZoneType.BUSINESS, False),
    (ZoneType.EMERGENCY, False),
])
def test_forbidden_zones_rejected_in_service_and_engine(kind, restricted):
    repo = InMemoryRepository(
        people=[Person(id="manager-1", name="Manager", role=PersonRole.MANAGER),
                Person(id="guest-1", name="Guest", role=PersonRole.GUEST)],
        zones=[Zone(id="floor-5", name="Restricted", zone_type=kind, restricted=restricted)])
    with pytest.raises(DomainError) as exc:
        create_invitation(repo, invitation(resident_id="manager-1"), NOW)
    assert exc.value.status_code == 403
    assert not decision(repo, permissions=[permission()]).allowed


@pytest.mark.parametrize("kind", [ZoneType.RESIDENTIAL, ZoneType.LOBBY, ZoneType.PARKING])
def test_resident_can_invite_into_authorized_guest_safe_zone(kind):
    repo = InMemoryRepository(
        people=[Person(id="resident-1", name="Resident", role=PersonRole.RESIDENT,
                       guest_zone_ids=["floor-5"])],
        zones=[Zone(id="floor-5", name="Allowed", zone_type=kind)])
    create_invitation(repo, invitation(), NOW)
    assert decision(repo, person_id="new-guest", permissions=repo.list_permissions()).allowed


@pytest.mark.parametrize("start,end,allowed", [
    (-2, -1, False), (1, 2, False), (-1, 0, False), (0, 1, True),
])
def test_permission_time_boundaries(repo, start, end, allowed):
    grant = permission(valid_from=NOW + timedelta(hours=start),
                       valid_until=NOW + timedelta(hours=end))
    assert decision(repo, permissions=[grant]).allowed is allowed


@pytest.mark.parametrize("changes", [
    {"valid_until": NOW - timedelta(hours=1)},
    {"valid_until": NOW - timedelta(hours=2)},
    {"valid_from": NOW.replace(tzinfo=None)},
    {"valid_until": NOW.replace(tzinfo=None)},
])
def test_invalid_permission_period_rejected(changes):
    with pytest.raises(ValidationError):
        permission(**changes)


def test_timezone_normalization(repo):
    offset = timezone(timedelta(hours=5))
    grant = permission(valid_from=NOW.astimezone(offset),
                       valid_until=(NOW + timedelta(hours=1)).astimezone(offset))
    assert grant.valid_from == NOW and grant.valid_from.tzinfo == timezone.utc
    assert decision(repo, permissions=[grant]).allowed


def test_naive_request_rejected():
    with pytest.raises(ValidationError):
        AccessRequest(person_id="guest-1", zone_id="floor-5", purpose="Visit",
                      requested_at=NOW.replace(tzinfo=None))


def test_contractor_temporary_permission_cannot_bypass_work_orders(repo):
    assert not decision(repo, person_id="contractor-1",
                        permissions=[permission(person_id="contractor-1")]).allowed


@pytest.mark.parametrize("active,contractor,zones", [
    (False, "contractor-1", ["machine-room"]),
    (True, "someone-else", ["machine-room"]),
    (True, "contractor-1", ["floor-5"]),
])
def test_invalid_work_order_denies(repo, active, contractor, zones):
    order = WorkOrder(id="wo", contractor_id=contractor, description="Repair",
                      allowed_zone_ids=zones, active=active)
    assert not decision(repo, person_id="contractor-1", zone_id="machine-room",
                        work_orders=[order]).allowed


@pytest.mark.parametrize("person_id", ["guest-1", "contractor-1", "manager-1"])
@pytest.mark.parametrize("changes", [{"person_id": "other"}, {"zone_id": "other"}])
def test_mismatched_context_denied_before_any_override(repo, person_id, changes):
    assert not decision(repo, person_id=person_id, permissions=[permission()],
                        work_orders=repo.list_work_orders(), request_changes=changes).allowed


@pytest.mark.parametrize("role", [PersonRole.MANAGER, PersonRole.EMERGENCY_RESPONDER])
def test_existing_privileged_override_preserved(role):
    repo = InMemoryRepository(
        people=[Person(id="privileged", name="Privileged", role=role)],
        zones=[Zone(id="technical", name="Technical", zone_type=ZoneType.MAINTENANCE,
                    restricted=True)])
    assert decision(repo, person_id="privileged", zone_id="technical").allowed


def test_duplicate_or_overlapping_permission_rejected(api, repo):
    payload = invitation().model_dump()
    assert api("POST", "/guests/invite", payload)[0] == 200
    assert api("POST", "/guests/invite", payload)[0] == 409
    assert api("POST", "/guests/invite", payload | {"allowed_zone_ids": ["lobby", "floor-5"]})[0] == 409
    assert len(repo.list_permissions()) == 1


def test_nonoverlapping_zones_and_renewal_at_expiry(repo):
    create_invitation(repo, invitation(), NOW)
    create_invitation(repo, invitation(allowed_zone_ids=["lobby"]), NOW)
    create_invitation(repo, invitation(), NOW + timedelta(hours=3))
    assert len(repo.list_permissions()) == 3


def test_future_overlapping_permission_rejected():
    seed = create_demo_repository()
    repo = InMemoryRepository(
        people=[seed.get_person("resident-1")], zones=[seed.get_zone("floor-5")],
        permissions=[permission(person_id="new-guest", valid_from=NOW + timedelta(hours=1),
                                valid_until=NOW + timedelta(hours=2))])
    with pytest.raises(DomainError) as exc:
        create_invitation(repo, invitation(), NOW)
    assert exc.value.status_code == 409
    assert repo.get_person("new-guest") is None


def test_invitation_is_deterministic_and_deduplicates_zone_ids():
    first = create_invitation(create_demo_repository(),
                              invitation(allowed_zone_ids=["lobby", "floor-5", "lobby"]), NOW)
    second = create_invitation(create_demo_repository(),
                               invitation(allowed_zone_ids=["floor-5", "lobby"]), NOW)
    assert first == second
    assert first["permission"].allowed_zone_ids == ["floor-5", "lobby"]


def test_conflicting_permissions_fail_closed(repo):
    assert not decision(repo, permissions=[permission(), permission(reason="Other")]).allowed


def test_mutated_invalid_permission_fails_closed(repo):
    grant = permission()
    grant.valid_until = grant.valid_from
    assert not decision(repo, permissions=[grant]).allowed


def test_repository_returns_copies(repo):
    result = create_invitation(repo, invitation(), NOW)
    result["permission"].allowed_zone_ids.append("machine-room")
    person = repo.get_person("new-guest")
    person.role = PersonRole.MANAGER
    assert repo.get_person("new-guest").role == PersonRole.GUEST
    assert repo.list_permissions()[0].allowed_zone_ids == ["floor-5"]


def test_concurrent_duplicate_invites_are_atomic(repo):
    barrier = Barrier(2)

    def invite():
        barrier.wait(timeout=5)
        try:
            create_invitation(repo, invitation(), NOW)
            return 200
        except DomainError as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: invite(), range(2)))
    assert sorted(results) == [200, 409]
    assert len(repo.list_permissions()) == 1


@pytest.mark.parametrize("payload", [
    {"person_id": "missing", "zone_id": "floor-5", "purpose": "Visit"},
    {"person_id": "guest-1", "zone_id": "missing", "purpose": "Visit"},
])
def test_unknown_access_context_returns_404(api, payload):
    assert api("POST", "/access/check", payload)[0] == 404


def test_application_health_and_openapi(api):
    assert api("GET", "/health") == (200, {"status": "healthy"})
    status, schema = api("GET", "/openapi.json")
    assert status == 200
    assert {"/access/check", "/guests/invite", "/guests/permissions"} <= schema["paths"].keys()


def test_maximum_duration_accepted(api):
    status, body = api("POST", "/guests/invite",
                       invitation(valid_for_hours=24).model_dump())
    assert status == 200
    assert datetime.fromisoformat(body["permission"]["valid_until"]) == NOW + timedelta(hours=24)


def test_existing_guest_reused_without_duplicate_registration(repo):
    create_invitation(repo, invitation(guest_id="guest-1", guest_name="Sara"), NOW)
    assert repo.get_person("guest-1").name == "Sara"
    assert decision(repo, permissions=repo.list_permissions()).allowed


def test_work_order_selection_independent_of_input_order(repo):
    orders = [WorkOrder(id=identifier, contractor_id="contractor-1", description="Repair",
                        allowed_zone_ids=["machine-room"]) for identifier in ["z", "a"]]
    first = decision(repo, person_id="contractor-1", zone_id="machine-room", work_orders=orders)
    second = decision(repo, person_id="contractor-1", zone_id="machine-room",
                      work_orders=list(reversed(orders)))
    assert first == second
    assert first.allowed and first.reason == "Authorized by work order a."


def test_permission_for_another_person_cannot_grant_access(repo):
    assert not decision(repo, permissions=[permission(person_id="someone-else")]).allowed


def test_missing_context_fails_closed(repo):
    request = AccessRequest(person_id="guest-1", zone_id="floor-5",
                            purpose="Visit", requested_at=NOW)
    assert not evaluate_access(request, None, repo.get_zone("floor-5"), [], []).allowed


def test_mutated_naive_request_denied_before_manager_override(repo):
    request = AccessRequest(person_id="manager-1", zone_id="floor-5",
                            purpose="Visit", requested_at=NOW)
    request.requested_at = NOW.replace(tzinfo=None)
    assert not evaluate_access(request, repo.get_person("manager-1"),
                               repo.get_zone("floor-5"), [], []).allowed
