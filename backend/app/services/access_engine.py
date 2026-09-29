"""Pure deterministic policy: no clock reads, repository access, or AI.

Precedence: consistency checks -> manager/emergency override -> contractor work
orders only -> guest permissions in guest-safe zones -> default deny.
Time windows are half-open: valid_from <= requested_at < valid_until.
"""
from pydantic import ValidationError

from app.models.access import AccessDecision, AccessPermission, AccessRequest
from app.models.building import Person, PersonRole, WorkOrder, Zone, ZoneType


GUEST_ZONE_TYPES = {ZoneType.RESIDENTIAL, ZoneType.LOBBY, ZoneType.PARKING}


def guest_zone_allowed(zone: Zone) -> bool:
    return not zone.restricted and zone.zone_type in GUEST_ZONE_TYPES


def evaluate_access(
    request: AccessRequest,
    person: Person,
    zone: Zone,
    permissions: list[AccessPermission],
    work_orders: list[WorkOrder],
) -> AccessDecision:
    def deny(reason):
        return AccessDecision(allowed=False, reason=reason)

    # Revalidate even objects created via model_construct or modified in memory.
    try:
        request = AccessRequest.model_validate(request.model_dump())
        person = Person.model_validate(person.model_dump())
        zone = Zone.model_validate(zone.model_dump())
    except (ValidationError, ValueError, TypeError, AttributeError):
        return deny("Invalid access context.")
    if request.person_id != person.id or request.zone_id != zone.id:
        return deny("Request identity or zone does not match the access context.")

    if person.role in {PersonRole.MANAGER, PersonRole.EMERGENCY_RESPONDER}:
        return AccessDecision(allowed=True, reason=f"{person.role.value} has building-wide access.")

    if person.role == PersonRole.CONTRACTOR:
        try:
            orders = [WorkOrder.model_validate(w.model_dump()) for w in work_orders]
        except (ValidationError, ValueError, TypeError, AttributeError):
            return deny("Invalid work-order data.")
        for order in sorted(orders, key=lambda w: w.id):
            if order.contractor_id == person.id and order.active and zone.id in order.allowed_zone_ids:
                return AccessDecision(allowed=True, reason=f"Authorized by work order {order.id}.")
        return deny("No active work order authorizes access to this zone.")

    if person.role != PersonRole.GUEST or not guest_zone_allowed(zone):
        return deny("No guest access policy authorizes this role or zone.")

    try:
        grants = [AccessPermission.model_validate(p.model_dump()) for p in permissions]
    except (ValidationError, ValueError, TypeError, AttributeError):
        return deny("Invalid permission data.")
    matches = [p for p in grants if p.person_id == person.id
               and zone.id in p.allowed_zone_ids
               and p.valid_from <= request.requested_at < p.valid_until]
    if len(matches) > 1:
        return deny("Conflicting active permissions.")
    if matches:
        return AccessDecision(allowed=True, reason=matches[0].reason, permission=matches[0])
    return deny("No valid access permission found.")
