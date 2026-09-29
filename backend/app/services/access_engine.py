"""Pure deterministic policy: no clock reads, repository access, or AI.

Precedence: consistency checks -> manager/emergency override -> contractor work
orders only -> guest permissions in guest-safe zones -> checked-in business
visitor permissions in their exact destination -> default deny.
Time windows are half-open: valid_from <= requested_at < valid_until.
"""
from pydantic import ValidationError

from app.models.access import AccessDecision, AccessPermission, AccessRequest
from app.models.building import Person, PersonRole, WorkOrder, Zone, ZoneType
from app.models.business import Appointment, AppointmentStatus, Business


GUEST_ZONE_TYPES = {ZoneType.RESIDENTIAL, ZoneType.LOBBY, ZoneType.PARKING}


def guest_zone_allowed(zone: Zone) -> bool:
    return not zone.restricted and zone.zone_type in GUEST_ZONE_TYPES


def evaluate_access(
    request: AccessRequest,
    person: Person,
    zone: Zone,
    permissions: list[AccessPermission],
    work_orders: list[WorkOrder],
    *,
    appointments: list[Appointment] | None = None,
    businesses: list[Business] | None = None,
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

    if person.role == PersonRole.BUSINESS_VISITOR:
        if zone.restricted or zone.zone_type != ZoneType.BUSINESS:
            return deny("Business visitors may only access their business destination.")
    elif person.role != PersonRole.GUEST or not guest_zone_allowed(zone):
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
        if person.role == PersonRole.BUSINESS_VISITOR:
            return evaluate_business_permission(
                person, zone, matches[0], appointments or [], businesses or []
            )
        return AccessDecision(allowed=True, reason=matches[0].reason, permission=matches[0])
    return deny("No valid access permission found.")


def evaluate_business_permission(
    person: Person, zone: Zone, permission: AccessPermission,
    appointments: list[Appointment], businesses: list[Business],
) -> AccessDecision:
    """Require a current checked-in appointment and exact permission provenance."""
    denied = AccessDecision(allowed=False, reason="Invalid business appointment authorization.")
    try:
        records = [Appointment.model_validate(a.model_dump()) for a in appointments]
        companies = [Business.model_validate(b.model_dump()) for b in businesses]
    except (ValidationError, ValueError, TypeError, AttributeError):
        return denied
    matching_appointments = [a for a in records if a.id == permission.appointment_id]
    matching_businesses = [b for b in companies if b.id == permission.business_id]
    if len(matching_appointments) != 1 or len(matching_businesses) != 1:
        return denied
    appointment = matching_appointments[0]
    business = matching_businesses[0]
    if (
        appointment.status != AppointmentStatus.CHECKED_IN
        or appointment.visitor_id != person.id
        or appointment.visitor_name != person.name
        or appointment.business_id != business.id
        or not business.active
        or zone.id not in business.destination_zone_ids
        or appointment.destination_zone_id != zone.id
        or permission.allowed_zone_ids != [appointment.destination_zone_id]
        or permission.valid_from != appointment.checked_in_at
        or permission.valid_until != appointment.window_end
        or permission.created_at != appointment.checked_in_at
        or permission.granted_by != f"business:{business.id}"
        or not permission.id
    ):
        return denied
    return AccessDecision(allowed=True, reason=permission.reason, permission=permission)
