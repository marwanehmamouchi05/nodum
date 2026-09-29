from datetime import datetime, timedelta
from hashlib import sha256
import json

from pydantic import TypeAdapter

from app.models.access import AccessPermission, GuestInviteInput, UTCTimestamp
from app.models.building import Person, PersonRole
from app.repository import Repository
from app.services.access_engine import guest_zone_allowed
from app.services.errors import DomainError


def create_invitation(repository: Repository, payload: GuestInviteInput, now: datetime):
    payload = GuestInviteInput.model_validate(payload.model_dump())
    now = TypeAdapter(UTCTimestamp).validate_python(now)
    until = now + timedelta(hours=payload.valid_for_hours)
    zone_ids = sorted(set(payload.allowed_zone_ids))
    with repository.transaction():
        inviter = repository.get_person(payload.resident_id)
        if inviter is None:
            raise DomainError(404, "Inviter not found")
        if inviter.role not in {PersonRole.RESIDENT, PersonRole.MANAGER}:
            raise DomainError(403, "Only residents or managers may invite guests")
        for zone_id in zone_ids:
            zone = repository.get_zone(zone_id)
            if zone is None:
                raise DomainError(404, f"Zone not found: {zone_id}")
            if not guest_zone_allowed(zone):
                raise DomainError(403, "Guest access is forbidden in this zone")
            if inviter.role == PersonRole.RESIDENT and zone_id not in inviter.guest_zone_ids:
                raise DomainError(403, "Zone is outside inviter authority")
        guest = repository.get_person(payload.guest_id)
        if guest is not None and (guest.role != PersonRole.GUEST or guest.name != payload.guest_name):
            raise DomainError(409, "Guest ID conflicts with an existing person")
        for existing in repository.list_permissions():
            if (existing.person_id == payload.guest_id
                    and set(existing.allowed_zone_ids).intersection(zone_ids)
                    and existing.valid_from < until and now < existing.valid_until):
                raise DomainError(409, "An overlapping permission already exists for this guest and zone")
        guest = guest or Person(id=payload.guest_id, name=payload.guest_name, role=PersonRole.GUEST)
        audit_data = [inviter.id, guest.id, zone_ids, now.isoformat(), until.isoformat()]
        permission = AccessPermission(
            id=sha256(json.dumps(audit_data, separators=(",", ":")).encode()).hexdigest(),
            person_id=guest.id, allowed_zone_ids=zone_ids, valid_from=now, valid_until=until,
            reason=f"Guest invited by {inviter.role.value} {inviter.id}",
            granted_by=inviter.id, created_at=now,
        )
        repository.add_guest_permission(guest, permission)
        return {"guest_id": guest.id, "guest_name": guest.name,
                "status": "approved", "permission": permission}
