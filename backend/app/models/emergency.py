from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.access import NonEmptyString, UTCTimestamp


class EmergencyType(str, Enum):
    WATER_LEAK = "water_leak"
    FIRE_ALARM = "fire_alarm"
    ELEVATOR_FAILURE = "elevator_failure"
    SECURITY_INCIDENT = "security_incident"


MAINTENANCE_EMERGENCY_TYPES = frozenset({
    EmergencyType.WATER_LEAK, EmergencyType.ELEVATOR_FAILURE,
})


class EmergencySeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EmergencyStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"


class EmergencyAction(str, Enum):
    TRIGGERED = "triggered"
    RESPONDERS_ASSIGNED = "responders_assigned"
    RESOLVED = "resolved"


class EmergencyCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    emergency_id: NonEmptyString
    emergency_type: EmergencyType
    severity: EmergencySeverity
    affected_zone_ids: list[NonEmptyString] = Field(min_length=1)
    description: NonEmptyString
    created_by: NonEmptyString
    assigned_responder_ids: list[NonEmptyString] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_ids(self):
        self.affected_zone_ids = sorted(set(self.affected_zone_ids))
        self.assigned_responder_ids = sorted(set(self.assigned_responder_ids))
        return self


class EmergencyAuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: EmergencyAction
    actor_id: NonEmptyString
    at: UTCTimestamp
    responder_ids: list[NonEmptyString] = Field(default_factory=list)


class EmergencyIncident(EmergencyCreateInput):
    status: EmergencyStatus = EmergencyStatus.ACTIVE
    created_at: UTCTimestamp
    resolved_at: UTCTimestamp | None = None
    resolved_by: NonEmptyString | None = None
    history: list[EmergencyAuditEvent] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_history(self):
        first = self.history[0]
        if (first.action != EmergencyAction.TRIGGERED or first.at != self.created_at
                or first.actor_id != self.created_by):
            raise ValueError("Incident history must start with its creation")
        responders = set(first.responder_ids)
        previous = first.at
        resolved = False
        for event in self.history[1:]:
            if event.at < previous or resolved:
                raise ValueError("Incident history must be chronological and end at resolution")
            if event.action == EmergencyAction.RESPONDERS_ASSIGNED:
                if not event.responder_ids or responders.intersection(event.responder_ids):
                    raise ValueError("Assignment events must add new responders")
                responders.update(event.responder_ids)
            elif event.action == EmergencyAction.RESOLVED:
                if event.responder_ids:
                    raise ValueError("Resolution cannot assign responders")
                resolved = True
            else:
                raise ValueError("Incident may only be triggered once")
            previous = event.at
        if sorted(responders) != self.assigned_responder_ids:
            raise ValueError("Responder assignments must match the audit history")
        if self.status == EmergencyStatus.RESOLVED:
            last = self.history[-1]
            if (not resolved or self.resolved_at != last.at
                    or self.resolved_by != last.actor_id):
                raise ValueError("Resolution fields must match the audit history")
        elif resolved or self.resolved_at is not None or self.resolved_by is not None:
            raise ValueError("Active incidents cannot have resolution data")
        return self


class EmergencyResolveInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resolved_by: NonEmptyString


class EmergencyAssignInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assigned_by: NonEmptyString
    responder_ids: list[NonEmptyString] = Field(min_length=1)
