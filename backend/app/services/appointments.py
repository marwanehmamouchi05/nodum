from datetime import datetime
from hashlib import sha256
import json

from pydantic import TypeAdapter

from app.models.access import AccessPermission, UTCTimestamp
from app.models.building import Person, PersonRole, ZoneType
from app.models.business import (
    Appointment, AppointmentCreateInput, AppointmentStatus,
    VisitorCheckInInput, VisitorCheckInResult,
)
from app.repository import Repository
from app.services.errors import DomainError


def validate_destination(repository: Repository, business_id: str, zone_id: str):
    business = repository.get_business(business_id)
    if business is None:
        raise DomainError(404, "Business not found")
    if not business.active:
        raise DomainError(403, "Business is inactive")
    zone = repository.get_zone(zone_id)
    if zone is None:
        raise DomainError(404, "Destination zone not found")
    if (zone_id not in business.destination_zone_ids
            or zone.zone_type != ZoneType.BUSINESS or zone.restricted):
        raise DomainError(403, "Destination is not an authorized business zone")


def validate_visitor(repository: Repository, visitor_id: str, visitor_name: str):
    visitor = repository.get_person(visitor_id)
    if visitor is not None and (
        visitor.role != PersonRole.BUSINESS_VISITOR or visitor.name != visitor_name
    ):
        raise DomainError(409, "Visitor ID conflicts with an existing person")
    return visitor


def create_appointment(repository: Repository, payload: AppointmentCreateInput,
                       now: datetime) -> Appointment:
    payload = AppointmentCreateInput.model_validate(payload.model_dump())
    now = TypeAdapter(UTCTimestamp).validate_python(now)
    with repository.transaction():
        if repository.get_appointment(payload.id) is not None:
            raise DomainError(409, "Appointment ID already exists")
        validate_destination(repository, payload.business_id, payload.destination_zone_id)
        if payload.appointment_time < now:
            raise DomainError(422, "Appointment time must not be in the past")
        validate_visitor(repository, payload.visitor_id, payload.visitor_name)
        appointment = Appointment(**payload.model_dump(), created_at=now)
        repository.add_appointment(appointment)
        return appointment


def get_appointment(repository: Repository, appointment_id: str) -> Appointment:
    appointment = repository.get_appointment(appointment_id)
    if appointment is None:
        raise DomainError(404, "Appointment not found")
    return appointment


def list_appointments(repository: Repository) -> list[Appointment]:
    return repository.list_appointments()


def check_in_visitor(repository: Repository, appointment_id: str,
                     payload: VisitorCheckInInput, now: datetime) -> VisitorCheckInResult:
    payload = VisitorCheckInInput.model_validate(payload.model_dump())
    now = TypeAdapter(UTCTimestamp).validate_python(now)
    with repository.transaction():
        appointment = get_appointment(repository, appointment_id)
        if (payload.visitor_id != appointment.visitor_id
                or payload.visitor_name != appointment.visitor_name):
            raise DomainError(403, "Visitor does not match the appointment")
        if appointment.status != AppointmentStatus.SCHEDULED:
            raise DomainError(409, "Appointment is not scheduled for check-in")
        if not appointment.window_start <= now < appointment.window_end or now < appointment.created_at:
            raise DomainError(403, "Outside the appointment check-in window")
        validate_destination(repository, appointment.business_id, appointment.destination_zone_id)
        visitor = validate_visitor(repository, payload.visitor_id, payload.visitor_name)
        for existing in repository.list_permissions():
            if (existing.person_id == payload.visitor_id
                    and appointment.destination_zone_id in existing.allowed_zone_ids
                    and existing.valid_from < appointment.window_end and now < existing.valid_until):
                raise DomainError(409, "An overlapping permission already exists for this visitor and zone")
        visitor = visitor or Person(id=payload.visitor_id, name=payload.visitor_name,
                                    role=PersonRole.BUSINESS_VISITOR)
        checked_in = Appointment.model_validate(
            appointment.model_dump() | {"status": AppointmentStatus.CHECKED_IN, "checked_in_at": now}
        )
        audit_data = ["appointment", appointment.id, visitor.id, appointment.business_id,
                      appointment.destination_zone_id, now.isoformat(), appointment.window_end.isoformat()]
        permission = AccessPermission(
            id=sha256(json.dumps(audit_data, separators=(",", ":")).encode()).hexdigest(),
            person_id=visitor.id, allowed_zone_ids=[appointment.destination_zone_id],
            valid_from=now, valid_until=appointment.window_end, created_at=now,
            reason=f"Checked in for appointment {appointment.id}.",
            granted_by=f"business:{appointment.business_id}",
            appointment_id=appointment.id, business_id=appointment.business_id,
        )
        repository.record_check_in(visitor, checked_in, permission)
        return VisitorCheckInResult(appointment=checked_in, permission=permission)
