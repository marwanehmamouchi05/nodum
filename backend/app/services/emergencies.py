from datetime import datetime

from pydantic import TypeAdapter

from app.models.access import UTCTimestamp
from app.models.building import PersonRole, ZoneType
from app.models.emergency import (
    EmergencyAction, EmergencyAssignInput, EmergencyAuditEvent,
    EmergencyCreateInput, EmergencyIncident, EmergencyResolveInput,
    EmergencyStatus, MAINTENANCE_EMERGENCY_TYPES,
)
from app.repository import Repository
from app.services.errors import DomainError


def validate_operator(repository: Repository, actor_id: str):
    actor = repository.get_person(actor_id)
    if actor is None:
        raise DomainError(404, "Emergency operator not found")
    if actor.role not in {PersonRole.MANAGER, PersonRole.EMERGENCY_RESPONDER}:
        raise DomainError(403, "Only managers or emergency responders may manage incidents")


def validate_assignments(repository: Repository, incident: EmergencyCreateInput,
                         responder_ids: list[str]):
    for responder_id in responder_ids:
        responder = repository.get_person(responder_id)
        if responder is None:
            raise DomainError(404, "Assigned responder not found")
        if responder.role == PersonRole.EMERGENCY_RESPONDER:
            continue
        if (responder.role != PersonRole.CONTRACTOR
                or incident.emergency_type not in MAINTENANCE_EMERGENCY_TYPES):
            raise DomainError(403, "Responder role is not eligible for this incident")
        maintenance_zones = {
            zone_id for zone_id in incident.affected_zone_ids
            if (zone := repository.get_zone(zone_id)) is not None
            and zone.zone_type == ZoneType.MAINTENANCE
        }
        if not any(order.active and order.contractor_id == responder_id
                   and maintenance_zones.intersection(order.allowed_zone_ids)
                   for order in repository.list_work_orders()):
            raise DomainError(403, "Contractor requires an active work order for an affected maintenance zone")


def get_emergency(repository: Repository, emergency_id: str) -> EmergencyIncident:
    incident = repository.get_emergency(emergency_id)
    if incident is None:
        raise DomainError(404, "Emergency not found")
    return incident


def list_emergencies(repository: Repository, active_only: bool = False) -> list[EmergencyIncident]:
    return [incident for incident in repository.list_emergencies()
            if not active_only or incident.status == EmergencyStatus.ACTIVE]


def create_emergency(repository: Repository, payload: EmergencyCreateInput,
                     now: datetime) -> EmergencyIncident:
    payload = EmergencyCreateInput.model_validate(payload.model_dump())
    now = TypeAdapter(UTCTimestamp).validate_python(now)
    with repository.transaction():
        if payload.emergency_id == "active":
            raise DomainError(422, "Emergency ID 'active' is reserved for the active listing")
        if repository.get_emergency(payload.emergency_id) is not None:
            raise DomainError(409, "Emergency ID already exists")
        validate_operator(repository, payload.created_by)
        for zone_id in payload.affected_zone_ids:
            if repository.get_zone(zone_id) is None:
                raise DomainError(404, f"Affected zone not found: {zone_id}")
        validate_assignments(repository, payload, payload.assigned_responder_ids)
        incident = EmergencyIncident(
            **payload.model_dump(), created_at=now,
            history=[EmergencyAuditEvent(action=EmergencyAction.TRIGGERED,
                                         actor_id=payload.created_by, at=now,
                                         responder_ids=payload.assigned_responder_ids)],
        )
        repository.add_emergency(incident)
        return incident


def validate_transition(incident: EmergencyIncident, now: datetime):
    if incident.status != EmergencyStatus.ACTIVE:
        raise DomainError(409, "Emergency is already resolved")
    if now < incident.history[-1].at:
        raise DomainError(422, "Incident transition cannot precede the latest audit event")


def resolve_emergency(repository: Repository, emergency_id: str,
                      payload: EmergencyResolveInput, now: datetime) -> EmergencyIncident:
    payload = EmergencyResolveInput.model_validate(payload.model_dump())
    now = TypeAdapter(UTCTimestamp).validate_python(now)
    with repository.transaction():
        incident = get_emergency(repository, emergency_id)
        validate_operator(repository, payload.resolved_by)
        validate_transition(incident, now)
        event = EmergencyAuditEvent(action=EmergencyAction.RESOLVED,
                                    actor_id=payload.resolved_by, at=now)
        updated = EmergencyIncident.model_validate(incident.model_dump() | {
            "status": EmergencyStatus.RESOLVED, "resolved_at": now,
            "resolved_by": payload.resolved_by, "history": [*incident.history, event],
        })
        repository.update_emergency(updated)
        return updated


def assign_responders(repository: Repository, emergency_id: str,
                      payload: EmergencyAssignInput, now: datetime) -> EmergencyIncident:
    payload = EmergencyAssignInput.model_validate(payload.model_dump())
    now = TypeAdapter(UTCTimestamp).validate_python(now)
    with repository.transaction():
        incident = get_emergency(repository, emergency_id)
        validate_operator(repository, payload.assigned_by)
        validate_transition(incident, now)
        new_ids = sorted(set(payload.responder_ids) - set(incident.assigned_responder_ids))
        if not new_ids:
            raise DomainError(409, "Responders are already assigned")
        validate_assignments(repository, incident, new_ids)
        event = EmergencyAuditEvent(action=EmergencyAction.RESPONDERS_ASSIGNED,
                                    actor_id=payload.assigned_by, at=now, responder_ids=new_ids)
        updated = EmergencyIncident.model_validate(incident.model_dump() | {
            "assigned_responder_ids": sorted(set(incident.assigned_responder_ids) | set(new_ids)),
            "history": [*incident.history, event],
        })
        repository.update_emergency(updated)
        return updated
