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
from app.models.authorization import Permission as P
from app.services.scoped_repository import ScopedRepository
from app.services.authorization import scoped_decision
from app.models.resident import ResidentVisitInput, ResidentMaintenanceInput
from app.models.business_workspace import BusinessVisitInput, BusinessMaintenanceInput


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
    "business_context": (EmptyInput, "Read only your affiliated business notices, visitors, staff, maintenance, personal access and permitted devices. No global operations."),
    "business_invite_visitor": (BusinessVisitInput, "PROPOSE a visitor for your active business. Ask for name and exact start/end timestamps. Explicit confirmation required. No physical access."),
    "business_report_maintenance": (BusinessMaintenanceInput, "PROPOSE a maintenance issue for your active business. Ask for problem and description. Explicit confirmation required."),
    "resident_context": (EmptyInput, "Read your own Resident units, current notices, visitors, maintenance and personal access. No global building feeds."),
    "resident_invite_visitor": (ResidentVisitInput, "PROPOSE your own visitor. Destination derives from active resident affiliation. Ask for visitor name and exact start/end timestamps. Explicit application confirmation required; no physical access."),
    "resident_report_maintenance": (ResidentMaintenanceInput, "PROPOSE a maintenance request for your affiliated unit. Ask for problem and description. Explicit application confirmation required."),
    "manager_operations": (EmptyInput, "Read scoped building attention, offline devices, unresolved maintenance and expected visitors. Available only in scoped installations; no actions."),
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
RESIDENT_WRITE_TOOLS = frozenset({"resident_invite_visitor", "resident_report_maintenance", "business_invite_visitor", "business_report_maintenance"})
WRITE_TOOLS = frozenset({"invite_guest", "create_appointment", "check_in_visitor"}) | RESIDENT_WRITE_TOOLS


def tenant_service(name, authorization):
    from app.services.resident import ResidentService
    from app.services.business_workspace import BusinessService
    return (BusinessService if name.startswith("business_") else ResidentService)(authorization, ai_context=True)


def tool_config() -> dict:
    return {"tools": [
        {"toolSpec": {"name": name, "description": description,
                      "inputSchema": {"json": schema.model_json_schema()}}}
        for name, (schema, description) in TOOL_SPECS.items()
    ]}


def validate_write_scope(repository: Repository, actor_id: str | None, name: str, payload, authorization=None):
    """Agent capability boundary, in addition to domain service validation."""
    if not actor_id:
        raise DomainError(403, "An actor_id is required to propose or confirm this action")
    if name in RESIDENT_WRITE_TOOLS:
        if not authorization or actor_id != authorization.principal.person_id:
            raise DomainError(403, "Resident actions require your authenticated account")
        permission = P.VISITORS_INVITE if name.endswith("invite_visitor") else P.MAINTENANCE_CREATE
        _, node = tenant_service(name, authorization).target(payload.affiliation_id, permission)
        return node.scope_id
    if authorization:
        if actor_id != authorization.principal.person_id:
            raise DomainError(403, "Acting identity must match the authenticated account")
        route, body, params, kind, identifier = tool_operation(name, payload, actor_id)
        from app.services.authorization_operations import authorize_operation
        authorize_operation(authorization, route, body, params)
        binding = repository.get_resource_binding(kind, identifier)
        if not binding:
            raise DomainError(403, "AI action requires explicit resource ownership")
        authorization.require_scope(P.AI_USE, binding.scope_id)
        return binding.scope_id
    actor = repository.get_person(actor_id)
    is_manager = actor is not None and actor.role == PersonRole.MANAGER
    if name == "invite_guest" and payload.resident_id != actor_id:
        raise DomainError(403, "Inviter must match the request actor")
    if name == "create_appointment" and not is_manager:
        raise DomainError(403, "Agent appointment creation requires a manager actor")
    if name == "check_in_visitor" and payload.visitor_id != actor_id and not is_manager:
        raise DomainError(403, "Check-in must be for the request actor or confirmed by a manager")


def tool_operation(name, payload, actor_id):
    body = payload.model_dump(mode="json")
    if name == "invite_guest":
        if payload.resident_id != actor_id:
            raise DomainError(403, "Inviter must match the authenticated actor")
        return "/guests/invite", body, {}, "person", actor_id
    if name == "create_appointment":
        return "/appointments", body, {}, "business", payload.business_id
    if name == "check_in_visitor":
        return "/appointments/{appointment_id}/check-in", body, {"appointment_id": payload.appointment_id}, "appointment", payload.appointment_id
    raise DomainError(400, "Unsupported action")


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
                   action_id: str, actor_id: str, now: datetime, authorization=None) -> AgentToolResult:
    if authorization:
        from app.services.authorization_operations import perform_authorized_write
        with repository.transaction():
            action = repository.get_pending_action(action_id)
            if not action:
                raise DomainError(404, "Pending action not found or already consumed")
            if action.authenticated_user_id != authorization.principal.user_id:
                raise DomainError(403, "Action belongs to a different authenticated identity")
            if action.tool not in WRITE_TOOLS:
                raise DomainError(400, "Unsupported action")
            payload = TOOL_SPECS[action.tool][0].model_validate(action.arguments)
            scope_id = validate_write_scope(repository, actor_id, action.tool, payload, authorization)
            if scope_id != action.authorization_scope_id:
                raise DomainError(403, "Action ownership scope changed")
            # Commit consumption separately, preserving the audited at-most-once
            # behavior even when the later domain execution fails.
        action = actions.consume(action_id, actor_id, now,
            authenticated_user_id=authorization.principal.user_id, authorization_scope_id=scope_id)
        if action.tool in RESIDENT_WRITE_TOOLS:
            with repository.transaction():
                if validate_write_scope(repository, actor_id, action.tool, payload, authorization) != scope_id:
                    raise DomainError(403, "Your active unit assignment changed")
                resident = tenant_service(action.tool, authorization)
                result = resident.create_visit(payload) if action.tool.endswith("invite_visitor") else resident.create_maintenance(payload)
                return AgentToolResult(tool=action.tool, status="success", data=jsonable_encoder(result))
        route, body, params, _, _ = tool_operation(action.tool, payload, actor_id)
        def execute_confirmed(repo):
            current_scope = validate_write_scope(repo, actor_id, action.tool, payload, authorization)
            if current_scope != action.authorization_scope_id:
                raise DomainError(403, "Action ownership scope changed")
            return execute_write(repo, action.tool, payload, now)
        result = perform_authorized_write(authorization, repository, route, body, execute_confirmed, params)
        return AgentToolResult(tool=action.tool, status="success", data=jsonable_encoder(result))
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
                 actor_id: str | None, clock: Callable[[], datetime], authorization=None):
        self.raw_repository = repository
        self.authorization = authorization
        self.repository = ScopedRepository(repository, authorization, ai_context=True) if authorization else repository
        self.actions = actions
        self.actor_id = actor_id
        self.clock = clock

    def run(self, name: str, arguments: dict) -> AgentToolResult:
        try:
            if name not in TOOL_SPECS:
                raise DomainError(400, "Unknown tool")
            payload = TOOL_SPECS[name][0].model_validate(arguments)
            if name in WRITE_TOOLS:
                scope_id = validate_write_scope(self.raw_repository, self.actor_id, name, payload, self.authorization)
                if name in RESIDENT_WRITE_TOOLS:
                    permission = P.VISITORS_INVITE if name.endswith("invite_visitor") else P.MAINTENANCE_CREATE
                    affiliation, _ = tenant_service(name, self.authorization).target(payload.affiliation_id, permission)
                    payload = payload.model_copy(update={"affiliation_id": affiliation.id})
                action = self.actions.propose(
                    self.actor_id, name, payload.model_dump(mode="json"), self.clock(),
                    authenticated_user_id=self.authorization.principal.user_id if self.authorization else None,
                    authorization_scope_id=scope_id if self.authorization else None)
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
        if name == "business_context":
            if not self.authorization:
                raise DomainError(403, "Business help requires your authenticated account")
            snapshot = tenant_service(name, self.authorization).snapshot()
            return {**snapshot, "visitors": snapshot["visitors"][:20], "maintenance": snapshot["maintenance"][:20], "staff": snapshot["staff"][:20]}
        if name == "resident_context":
            if not self.authorization:
                raise DomainError(403, "Resident help requires your authenticated account")
            from app.services.resident import ResidentService
            snapshot = ResidentService(self.authorization, ai_context=True).snapshot()
            return {**snapshot, "visitors": snapshot["visitors"][:20], "maintenance": snapshot["maintenance"][:20], "notices": snapshot["notices"][:20]}
        if name == "manager_operations":
            if not self.authorization:
                raise DomainError(403, "Operational summary requires a scoped installation")
            from app.services.resident_boundary import confined
            from app.services.business_boundary import confined as business_confined
            if confined(self.authorization) or business_confined(self.authorization):
                raise DomainError(403, "Use your personal Resident context")
            from app.services.manager import ManagerService
            snapshot = ManagerService(self.authorization, ai_context=True).snapshot()
            return {key: snapshot[key] for key in ("status", "status_note", "coverage", "counts", "attention", "unverified_devices")} | {
                "offline_devices": [d["name"] for d in snapshot["devices"] if d["status"] == "offline"][:20],
                "expected_visitors": [{k: v[k] for k in ("name", "destination", "start", "end")} for v in snapshot["visitors"] if v["status"] == "expected"][:20],
                "maintenance": [{k: r[k] for k in ("title", "location_name", "status")} for r in snapshot["maintenance"] if r["status"] not in {"resolved", "closed"}][:20]}

        if name == "check_access":
            if self.authorization:
                from app.services.authorization_operations import authorize_operation
                authorize_operation(self.authorization, "/access/check", payload.model_dump())
                self.authorization.require(P.AI_USE, "person", payload.person_id)
                self.authorization.require(P.AI_USE, "location", payload.zone_id)
                return scoped_decision(self.authorization,
                    access.check_access(self.raw_repository, payload, self.clock(), legacy_role_access=False))
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
