"""Explicit application operation contracts shared by HTTP and AI."""
from app.models.authorization import Permission as P
from app.services.errors import DomainError
from app.services.scoped_repository import bind_created


def authorize_operation(authorization, route, body, params=None):
    """Explicit mutation allowlist; new endpoints fail closed until reviewed."""
    params = params or {}
    repo = authorization.repository
    def require(permission, kind, identifier):
        if not isinstance(identifier, str):
            raise DomainError(422, "Missing resource identifier")
        authorization.require(permission, kind, identifier)
    if route == "/access/check":
        require(P.ACCESS_CHECK, "person", body.get("person_id"))
        require(P.ACCESS_CHECK, "location", body.get("zone_id"))
    elif route == "/guests/invite":
        require(P.VISITORS_INVITE, "person", authorization.principal.person_id)
        for zone in body.get("allowed_zone_ids", []):
            require(P.VISITORS_INVITE, "location", zone)
        if repo.get_person(body.get("guest_id")):
            require(P.VISITORS_INVITE, "person", body["guest_id"])
    elif route == "/appointments":
        require(P.VISITORS_INVITE, "business", body.get("business_id"))
        require(P.VISITORS_INVITE, "location", body.get("destination_zone_id"))
        if repo.get_appointment(body.get("id")):
            require(P.VISITORS_INVITE, "appointment", body["id"])
    elif route == "/appointments/{appointment_id}/check-in":
        require(P.VISITORS_CHECK_IN, "appointment", params.get("appointment_id"))
        appointment = repo.get_appointment(params["appointment_id"])
        if not appointment:
            raise DomainError(404, "Appointment not found")
        require(P.VISITORS_CHECK_IN, "business", appointment.business_id)
        require(P.VISITORS_CHECK_IN, "location", appointment.destination_zone_id)
        if repo.get_person(appointment.visitor_id):
            require(P.VISITORS_CHECK_IN, "person", appointment.visitor_id)
    elif route == "/emergencies":
        for zone in body.get("affected_zone_ids", []):
            require(P.INCIDENTS_MANAGE, "location", zone)
        for person in body.get("assigned_responder_ids", []):
            require(P.PEOPLE_READ, "person", person)
        if repo.get_emergency(body.get("emergency_id")):
            require(P.INCIDENTS_MANAGE, "incident", body["emergency_id"])
    elif route in {"/emergencies/{emergency_id}/resolve", "/emergencies/{emergency_id}/responders"}:
        require(P.INCIDENTS_MANAGE, "incident", params.get("emergency_id"))
        for person in body.get("responder_ids", []):
            require(P.PEOPLE_READ, "person", person)
    elif route == "/agent/chat":
        if not any(authorization.allowed_scope(P.AI_USE, a.scope_id)
                   for a in repo.list_role_assignments() if a.user_id == authorization.principal.user_id):
            raise DomainError(403, "AI assistance is not permitted")
    elif route == "/agent/actions/{action_id}/confirm":
        # Exact proposal ownership and fresh scope checks occur before consumption.
        pass
    elif route == "/ring/simulation/scenarios/{scenario}":
        require(P.SIMULATION_RUN, "simulation", "ring")
    elif route == "/ring/events/{event_id}/process":
        require(P.RING_PROCESS, "ring_event", params.get("event_id"))
        require(P.RING_READ, "ring_event", params.get("event_id"))
        if body.get("zone_id"):
            require(P.INCIDENTS_MANAGE, "location", body["zone_id"])
    elif route == "/ring/link":
        # Ring ownership remains independently enforced. Account-link configuration
        # requires an explicit grant on this installation's linking resource.
        require(P.RING_MANAGE, "ring_link", "installation")
    else:
        raise DomainError(403, "This operation is not enabled in scoped mode")


def perform_authorized_write(authorization, repository, route, body, operation, params=None):
    """Recheck grants under the same transaction as the domain mutation/binding."""
    if authorization is None:
        return operation(repository)
    with repository.transaction():
        authorize_operation(authorization, route, body, params)
        kind, parent = None, None
        if route == "/guests/invite":
            kind, parent = "person", authorization.principal.person_id
        elif route == "/appointments":
            kind, parent = "business", body["business_id"]
        elif route == "/appointments/{appointment_id}/check-in":
            kind, parent = "appointment", params["appointment_id"]
        if kind:
            binding = repository.get_resource_binding(kind, parent)
            scope_id = binding.scope_id
            # No ownership transfer of a reused visitor identity.
            person_id = body.get("guest_id") or body.get("visitor_id")
            existing = repository.get_resource_binding("person", person_id) if person_id else None
            if existing and existing.scope_id != scope_id:
                raise DomainError(403, "Visitor identity belongs to another scope")
        elif route == "/emergencies":
            scopes = [repository.get_resource_binding("location", z).scope_id for z in body["affected_zone_ids"]]
            if not scopes:
                raise DomainError(422, "At least one affected location is required")
            common = set.intersection(*(authorization.ancestors(s) for s in scopes))
            if not common:
                raise DomainError(403, "Incident locations cross organization boundaries")
            scope_id = max(common, key=lambda s: len(authorization.ancestors(s)))
            authorization.require_scope(P.INCIDENTS_MANAGE, scope_id)
        result = operation(repository)
        if route == "/guests/invite":
            bind_created(repository, "person", result["guest_id"], scope_id)
            bind_created(repository, "access_permission", result["permission"].id, scope_id)
        elif route == "/appointments":
            bind_created(repository, "appointment", result.id, scope_id)
        elif route == "/appointments/{appointment_id}/check-in":
            bind_created(repository, "person", result.appointment.visitor_id, scope_id)
            bind_created(repository, "access_permission", result.permission.id, scope_id)
        elif route == "/emergencies":
            bind_created(repository, "incident", result.emergency_id, scope_id)
        return result


