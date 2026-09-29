from datetime import datetime, timedelta, timezone

from app.models.access import AccessPermission, AccessRequest
from app.models.building import Person, PersonRole, WorkOrder, Zone, ZoneType
from app.services.access_engine import evaluate_access


def test_contractor_allowed_by_work_order():
    person = Person(
        id="contractor-1",
        name="Ahmed",
        role=PersonRole.CONTRACTOR,
    )

    zone = Zone(
        id="machine-room",
        name="Elevator Machine Room",
        zone_type=ZoneType.MAINTENANCE,
        floor=-1,
    )

    request = AccessRequest(
        person_id=person.id,
        zone_id=zone.id,
        purpose="Elevator repair",
        requested_at=datetime.now(timezone.utc),
    )

    work_order = WorkOrder(
        id="wo-001",
        contractor_id=person.id,
        description="Repair Elevator 2",
        allowed_zone_ids=["machine-room"],
        active=True,
    )

    decision = evaluate_access(
        request=request,
        person=person,
        zone=zone,
        permissions=[],
        work_orders=[work_order],
    )

    assert decision.allowed is True


def test_contractor_denied_without_work_order():
    person = Person(
        id="contractor-2",
        name="Youssef",
        role=PersonRole.CONTRACTOR,
    )

    zone = Zone(
        id="res-floor-5",
        name="Residential Floor 5",
        zone_type=ZoneType.RESIDENTIAL,
        floor=5,
    )

    request = AccessRequest(
        person_id=person.id,
        zone_id=zone.id,
        purpose="Maintenance",
        requested_at=datetime.now(timezone.utc),
    )

    decision = evaluate_access(
        request=request,
        person=person,
        zone=zone,
        permissions=[],
        work_orders=[],
    )

    assert decision.allowed is False


def test_guest_allowed_with_temporary_permission():
    person = Person(
        id="guest-1",
        name="Sara",
        role=PersonRole.GUEST,
    )

    zone = Zone(
        id="floor-5",
        name="Residential Floor 5",
        zone_type=ZoneType.RESIDENTIAL,
        floor=5,
    )

    now = datetime.now(timezone.utc)

    permission = AccessPermission(
        person_id=person.id,
        allowed_zone_ids=["floor-5"],
        valid_from=now - timedelta(minutes=5),
        valid_until=now + timedelta(hours=2),
        reason="Approved guest visit",
    )

    request = AccessRequest(
        person_id=person.id,
        zone_id=zone.id,
        purpose="Visit resident",
        requested_at=now,
    )

    decision = evaluate_access(
        request=request,
        person=person,
        zone=zone,
        permissions=[permission],
        work_orders=[],
    )

    assert decision.allowed is True
