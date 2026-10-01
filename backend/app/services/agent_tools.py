"""Fixed tool registry: validation/adaptation only; domain rules stay in services."""
from datetime import datetime
from typing import Callable

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.models.access import AccessCheckInput, GuestInviteInput, NonEmptyString
from app.models.agent import AgentToolResult
from app.models.building import PersonRole
from app.models.business import AppointmentCreateInput, VisitorCheckInInput
from app.repository import Repository
from app.services import access, appointments, emergencies, guests
from app.services.agent_actions import PendingActionStore
from app.services.errors import DomainError


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchInput(EmptyInput):
    query: str = Field(default="", max_length=200)
    limit: int = Field(default=20, ge=1, le=100, strict=True)


class AppointmentSearchInput(EmptyInput):
    visitor_id: NonEmptyString | None = None
    business_id: NonEmptyString | None = None
    limit: int = Field(default=20, ge=1, le=100, strict=True)


class WorkOrderInput(EmptyInput):
    contractor_id: NonEmptyString | None = None
    limit: int = Field(default=20, ge=1, le=100, strict=True)


class CheckAccessInput(AccessCheckInput):
    model_config = ConfigDict(extra="forbid")


class InviteInput(GuestInviteInput):
    model_config = ConfigDict(extra="forbid")


class CheckInInput(VisitorCheckInInput):
    appointment_id: NonEmptyString


# No arbitrary Python, URLs, repository writes, permission grants, override roles,
# incident resolution, or action confirmation are exposed to the model.
TOOL_SPECS = {
    "find_people": (SearchInput, "Find people by a specific ID or name (at least 2 characters). No directory export."),
    "find_zones": (SearchInput, "Find zones by ID or name, including type and floor."),
    "find_businesses": (SearchInput, "Find businesses by ID or name and their destination zone IDs."),
    "list_work_orders": (WorkOrderInput, "Read work order summaries for a specified contractor ID."),
    "list_appointments": (AppointmentSearchInput, "Find appointments for a specified visitor ID, optionally filtered by business. Ask for visitor identity first."),
    "list_active_emergencies": (EmptyInput, "Read currently active incidents; never resolve incidents."),
    "check_access": (CheckAccessInput, "Ask Nodum's deterministic engine whether a person may enter a zone now."),
    "invite_guest": (InviteInput, "PROPOSE a guest invitation for the request actor. Does not execute; user confirmation is required."),
    "create_appointment": (AppointmentCreateInput, "PROPOSE an appointment. Does not execute; manager confirmation is required."),
    "check_in_visitor": (CheckInInput, "PROPOSE check-in against an existing appointment. Does not execute; user confirmation is required."),
}
WRITE_TOOLS = frozenset({"invite_guest", "create_appointment", "check_in_visitor"})


def tool_config() -> dict:
    return {"tools": [
        {"toolSpec": {"name": name, "description": description,
                      "inputSchema": {"json": schema.model_json_schema()}}}
        for name, (schema, description) in TOOL_SPECS.items()
    ]}


def validate_write_scope(repository: Repository, actor_id: str | None, name: str, payload):
    """Agent capability boundary, in addition to domain service validation."""
    if not actor_id:
        raise DomainError(403, "An actor_id is required to propose or confirm this action")
    actor = repository.get_person(actor_id)
    is_manager = actor is not None and actor.role == PersonRole.MANAGER
    if name == "invite_guest" and payload.resident_id != actor_id:
        raise DomainError(403, "Inviter must match the request actor")
    if name == "create_appointment" and not is_manager:
        raise DomainError(403, "Agent appointment creation requires a manager actor")
    if name == "check_in_visitor" and payload.visitor_id != actor_id and not is_manager:
        raise DomainError(403, "Check-in must be for the request actor or confirmed by a manager")


def execute_write(repository: Repository, name: str, payload, now: datetime):
    # Every mutation goes through existing services, which revalidate current state.
    if name == "invite_guest":
        return guests.create_invitation(repository, payload, now)
    if name == "create_appointment":
        return appointments.create_appointment(repository, payload, now)
    if name == "check_in_visitor":
        return appointments.check_in_visitor(
            repository, payload.appointment_id,
            VisitorCheckInInput(visitor_id=payload.visitor_id, visitor_name=payload.visitor_name), now,
        )
    raise DomainError(400, "Unsupported action")


def confirm_action(repository: Repository, actions: PendingActionStore,
                   action_id: str, actor_id: str, now: datetime) -> AgentToolResult:
    action = actions.consume(action_id, actor_id, now)
    if action.tool not in WRITE_TOOLS:
        raise DomainError(400, "Unsupported action")
    payload = TOOL_SPECS[action.tool][0].model_validate(action.arguments)
    with repository.transaction():
        validate_write_scope(repository, actor_id, action.tool, payload)
        result = execute_write(repository, action.tool, payload, now)
    return AgentToolResult(tool=action.tool, status="success", data=jsonable_encoder(result))


class AgentTools:
    def __init__(self, repository: Repository, actions: PendingActionStore,
                 actor_id: str | None, clock: Callable[[], datetime]):
        self.repository = repository
        self.actions = actions
        self.actor_id = actor_id
        self.clock = clock

    def run(self, name: str, arguments: dict) -> AgentToolResult:
        try:
            if name not in TOOL_SPECS:
                raise DomainError(400, "Unknown tool")
            payload = TOOL_SPECS[name][0].model_validate(arguments)
            if name in WRITE_TOOLS:
                validate_write_scope(self.repository, self.actor_id, name, payload)
                action = self.actions.propose(
                    self.actor_id, name, payload.model_dump(mode="json"), self.clock())
                return AgentToolResult(tool=name, status="confirmation_required",
                                       data=action.model_dump(mode="json"))
            result = self.read(name, payload)
            return AgentToolResult(tool=name, status="success", data=jsonable_encoder(result))
        except ValidationError as exc:
            return AgentToolResult(tool=name, status="error",
                data={"status_code": 422, "detail": exc.errors(include_input=False, include_context=False)})
        except DomainError as exc:
            return AgentToolResult(tool=name, status="error",
                                   data={"status_code": exc.status_code, "detail": exc.detail})

    def read(self, name: str, payload):
        if name == "check_access":
            return access.check_access(self.repository, payload, self.clock())
        if name == "list_active_emergencies":
            # Bounded context; API remains available for full incident detail.
            records = emergencies.list_emergencies(self.repository, active_only=True)
            return {"items": [r.model_dump(mode="json", include={
                "emergency_id", "emergency_type", "severity", "affected_zone_ids", "status", "created_at"
            }) for r in records[:20]], "truncated": len(records) > 20}
        if name == "list_appointments":
            if not payload.visitor_id:
                raise DomainError(400, "Specify a visitor ID; appointment directory export is unavailable")
            records = [a for a in appointments.list_appointments(self.repository)
                       if (payload.visitor_id is None or a.visitor_id == payload.visitor_id)
                       and (payload.business_id is None or a.business_id == payload.business_id)]
        elif name == "list_work_orders":
            if not payload.contractor_id:
                raise DomainError(400, "Specify a contractor ID")
            records = [w for w in self.repository.list_work_orders()
                       if payload.contractor_id is None or w.contractor_id == payload.contractor_id]
        else:
            readers = {"find_people": self.repository.list_people,
                       "find_zones": self.repository.list_zones,
                       "find_businesses": self.repository.list_businesses}
            query = payload.query.casefold()
            if name == "find_people" and len(query.strip()) < 2:
                raise DomainError(400, "Specify a person ID or name with at least two characters")
            records = [record for record in readers[name]()
                       if query in record.id.casefold() or query in record.name.casefold()]
        limit = min(payload.limit, 10) if name in {"find_people", "list_appointments", "list_work_orders"} else payload.limit
        items = []
        for record in records[:limit]:
            data = record.model_dump(mode="json")
            if name == "find_people" and record.id != self.actor_id:
                data.pop("guest_zone_ids", None)
            if name == "list_work_orders":
                data.pop("description", None)
            items.append(data)
        return {"items": items, "truncated": len(records) > limit}
