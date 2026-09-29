from datetime import datetime

from app.models.access import AccessDecision, AccessPermission, AccessRequest
from app.models.building import Person, PersonRole, WorkOrder, Zone


def evaluate_access(
    request: AccessRequest,
    person: Person,
    zone: Zone,
    permissions: list[AccessPermission],
    work_orders: list[WorkOrder],
) -> AccessDecision:

    # Managers and emergency responders can access all zones for now.
    if person.role in {
        PersonRole.MANAGER,
        PersonRole.EMERGENCY_RESPONDER,
    }:
        return AccessDecision(
            allowed=True,
            reason=f"{person.role.value} has building-wide access.",
        )

    # Check explicit temporary permissions.
    for permission in permissions:
        if (
            permission.person_id == person.id
            and zone.id in permission.allowed_zone_ids
            and permission.valid_from <= request.requested_at <= permission.valid_until
        ):
            return AccessDecision(
                allowed=True,
                reason=permission.reason,
                permission=permission,
            )

    # Contractor access must match an active work order.
    if person.role == PersonRole.CONTRACTOR:
        for work_order in work_orders:
            if (
                work_order.contractor_id == person.id
                and work_order.active
                and zone.id in work_order.allowed_zone_ids
            ):
                return AccessDecision(
                    allowed=True,
                    reason=f"Authorized by work order {work_order.id}.",
                )

        return AccessDecision(
            allowed=False,
            reason="No active work order authorizes access to this zone.",
        )

    return AccessDecision(
        allowed=False,
        reason="No valid access permission found.",
    )