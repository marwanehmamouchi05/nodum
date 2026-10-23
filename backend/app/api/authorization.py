"""Session-derived identity and explicit application authorization boundaries."""
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from app.api.dependencies import get_repository, utc_now
from app.auth_config import AuthSettings
from app.models.authorization import Principal, Permission as P, RoleAssignment
from app.services.auth import AuthService
from app.services.authorization import AuthorizationService, authorization_mode, ROLE_CEILINGS
from app.services.errors import DomainError
from app.services.authorization_operations import authorize_operation, perform_authorized_write
from app.config import ConfigurationError


READ_ROUTES = {
    "/access/check", "/guests/permissions", "/appointments", "/appointments/{appointment_id}",
    "/emergencies", "/emergencies/active", "/emergencies/{emergency_id}",
    "/building/catalog", "/building/integrations", "/building/devices",
    "/building/devices/{device_id}/status", "/building/actuator-events",
    "/building/credential-events", "/building/journeys", "/building/journeys/{journey_id}",
    "/building/journeys/{journey_id}/transitions", "/ring/accounts",
    "/ring/accounts/{account_id}/devices", "/ring/accounts/{account_id}/events",
    "/ring/simulation", "/ring/simulation/devices", "/ring/simulation/events",
    "/ring/playground/devices",
    "/ring/playground/evidence",
}


def session_principal(request, repository, now):
    try:
        settings = AuthSettings.from_env()
    except ConfigurationError:
        raise DomainError(503, "Nodum authentication configuration is missing or invalid") from None
    service = AuthService(repository, settings)
    cookie = request.cookies.get(service.settings.cookie_name)
    user = service.user(cookie, now)
    if not user:
        raise DomainError(401, "Sign in to Nodum to continue")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        service.check_csrf(cookie, request.headers.get("x-csrf-token"), request.headers.get("origin"), now)
    return Principal(user_id=user.id, person_id=user.person_id)


def require_scoped_context(request: Request, repository=Depends(get_repository), now: datetime = Depends(utc_now)):
    principal = session_principal(request, repository, now)
    return AuthorizationService(repository, principal, now)


async def authorize_application_request(request: Request, repository=Depends(get_repository), now=Depends(utc_now)):
    if authorization_mode() != "scoped":
        return
    route = request.scope["route"].path
    # Provider-signed ingestion and the browser login continuation are not user
    # operations. Existing signature/nonce/session boundaries remain unchanged.
    if route in {"/ring/webhooks", "/ring/token-exchange"} or (route == "/ring/link" and request.method == "GET"):
        return
    # get_repository runs before this dependency; it returns raw storage until
    # principal state is installed. Auth dependencies always retain raw storage.
    principal = session_principal(request, repository, now)
    authorization = AuthorizationService(repository, principal, now)
    request.state.principal = principal
    request.state.authorization = authorization
    method = request.method
    # Authentication routes own their unchanged session/CSRF implementation.
    if route.startswith("/authorization"):
        return
    if method in {"GET", "HEAD"}:
        if route not in READ_ROUTES:
            raise DomainError(403, "This read operation is not enabled in scoped mode")
        if route == "/building/devices/{device_id}/status":
            authorization.require(P.ACCESS_READ, "device", request.path_params["device_id"])
        if route.startswith("/ring/"):
            if route.startswith("/ring/simulation") or route.startswith("/ring/playground/"):
                authorization.require(P.SIMULATION_RUN, "simulation", "ring")
            elif "account_id" in request.path_params:
                authorization.require(P.RING_READ, "ring_account", ring_account_key(repository, request.path_params["account_id"]))
            elif route != "/ring/accounts":
                raise DomainError(403, "Ring operation is not enabled in scoped mode")
        return
    try:
        body = await request.json()
    except (ValueError, UnicodeDecodeError):
        raise DomainError(422, "Invalid JSON request") from None
    if not isinstance(body, dict):
        raise DomainError(422, "Invalid request body")
    # Caller-supplied identity may remain for wire compatibility, never authority.
    for field in ("actor_id", "resident_id", "created_by", "resolved_by", "assigned_by"):
        if field in body and body[field] != principal.person_id:
            raise DomainError(403, "Acting identity must match the authenticated account")
    authorize_operation(authorization, route, body, request.path_params)


def ring_account_key(repository, account_id):
    from app.integrations.ring.config import RingSettings
    from app.services.ring import identity
    return identity(RingSettings.from_env().environment, account_id)


def perform_write(request, repository, route, body, operation, params=None):
    authorization = request.state.authorization if authorization_mode() == "scoped" else None
    return perform_authorized_write(authorization, repository, route, body, operation, params)


router = APIRouter(prefix="/authorization", tags=["Application authorization"])


@router.get("/context")
def context(authorization=Depends(require_scoped_context)):
    return principal_context(authorization)


def principal_context(authorization):
    repo, principal = authorization.repository, authorization.principal
    assignments = [a.model_copy(update={"permissions": [p for p in a.permissions if p in ROLE_CEILINGS[a.role]]})
        for a in repo.list_role_assignments() if a.user_id == principal.user_id
        and a.active and (a.expires_at is None or authorization.now < a.expires_at)
        and authorization.ancestors(a.scope_id)]
    # Own membership changes/expiry invalidate displayed private workspace data.
    # This is a cache generation marker, never an authorization credential.
    import hashlib
    import json
    memberships = sorted((a.model_dump(mode="json") | {"effective_active": bool(a.active
        and (a.starts_at is None or a.starts_at <= authorization.now)
        and (a.ends_at is None or authorization.now < a.ends_at))}
        for a in repo.list_affiliations() if a.user_id == principal.user_id), key=lambda a: a["id"])
    context_version = hashlib.sha256(json.dumps(memberships, sort_keys=True).encode()).hexdigest()
    return {"mode": authorization_mode(), "principal": principal, "context_version": context_version,
            "assignments": assignments}


@router.get("/assignments")
def assignments(authorization=Depends(require_scoped_context)):
    return [a for a in authorization.repository.list_role_assignments()
            if authorization.allowed_scope(P.AUTHORIZATION_MANAGE, a.scope_id)
            or (a.role.value == "admin" and authorization.allowed_scope(P.OWNERSHIP_MANAGE, a.scope_id))]


@router.put("/assignments/{assignment_id}")
def grant(assignment_id: str, payload: RoleAssignment, authorization=Depends(require_scoped_context)):
    if assignment_id != payload.id:
        raise DomainError(422, "Assignment identity does not match path")
    authorization.grant(payload)
    return payload


@router.delete("/assignments/{assignment_id}")
def revoke(assignment_id: str, authorization=Depends(require_scoped_context)):
    authorization.revoke(assignment_id)
    return {"status": "revoked"}
