"""Fail-closed action/resource/scope evaluation with live, revocable grants."""
import os
from app.config import ConfigurationError
from app.models.authorization import Permission as P, Role, ScopeKind, Principal
from app.services.errors import DomainError


def authorization_mode():
    mode = os.getenv("NODUM_AUTHORIZATION_MODE", "legacy_demo")
    if mode not in {"legacy_demo", "scoped"}:
        raise ConfigurationError("NODUM_AUTHORIZATION_MODE must be legacy_demo or scoped")
    return mode


def scoped_decision(authorization, decision):
    """Return policy outcome without exposing an unreadable physical grant."""
    if decision.permission and not authorization.allowed(P.ACCESS_READ, "access_permission", decision.permission.id):
        return decision.model_copy(update={"permission": None})
    return decision


COMMON = {P.LOCATIONS_READ, P.AI_USE, P.ANNOUNCEMENTS_READ}
ROLE_CEILINGS = {
    Role.OWNER: {P.OWNERSHIP_MANAGE},
    Role.ADMIN: {P.BUSINESS_STAFF_MANAGE, P.ACCOUNTS_MANAGE, P.STRUCTURE_CONFIGURE, P.AFFILIATIONS_MANAGE, P.AUTHORIZATION_MANAGE, P.ACCOUNTS_READ, P.LOCATIONS_READ,
                 P.BUSINESSES_READ, P.HARDWARE_READ, P.HARDWARE_CONFIGURE, P.RING_MANAGE, P.AI_USE},
    Role.MANAGER: COMMON | {P.ANNOUNCEMENTS_PUBLISH, P.MAINTENANCE_CREATE, P.MAINTENANCE_MANAGE,P.ACCOUNTS_MANAGE, P.STRUCTURE_CONFIGURE, P.AFFILIATIONS_MANAGE, P.PEOPLE_READ, P.BUSINESSES_READ, P.HARDWARE_READ,
        P.VISITORS_READ, P.VISITORS_INVITE, P.VISITORS_CHECK_IN, P.ACCESS_READ,
        P.ACCESS_CHECK, P.MAINTENANCE_READ, P.INCIDENTS_READ, P.INCIDENTS_MANAGE,
        P.ACTIVITY_READ, P.RING_READ, P.RING_PROCESS, P.CAMERA_VIEW, P.SIMULATION_RUN, P.HARDWARE_CONFIGURE},
    Role.SECURITY: COMMON | {P.PEOPLE_READ, P.VISITORS_READ, P.VISITORS_CHECK_IN,
        P.ACCESS_READ, P.ACCESS_CHECK, P.INCIDENTS_READ, P.INCIDENTS_MANAGE,
        P.ACTIVITY_READ, P.RING_READ, P.RING_PROCESS, P.CAMERA_VIEW, P.HARDWARE_READ},
    Role.MAINTENANCE: COMMON | {P.MAINTENANCE_MANAGE,P.MAINTENANCE_READ, P.HARDWARE_READ, P.ACCESS_READ, P.ACCESS_CHECK},
    Role.BUSINESS_ADMIN: COMMON | {P.BUSINESS_STAFF_MANAGE, P.ACTIVITY_READ, P.MAINTENANCE_CREATE,P.PEOPLE_READ, P.BUSINESSES_READ, P.VISITORS_READ,
        P.VISITORS_INVITE, P.VISITORS_CHECK_IN, P.ACCESS_READ, P.ACCESS_CHECK,
        P.MAINTENANCE_READ, P.CAMERA_VIEW, P.RING_READ, P.HARDWARE_READ},
    Role.BUSINESS_STAFF: COMMON | {P.ACTIVITY_READ, P.MAINTENANCE_CREATE,P.BUSINESSES_READ, P.VISITORS_READ, P.VISITORS_INVITE,
        P.VISITORS_CHECK_IN, P.ACCESS_READ, P.ACCESS_CHECK, P.MAINTENANCE_READ},
    Role.RESIDENT: COMMON | {P.MAINTENANCE_CREATE,P.PEOPLE_READ, P.VISITORS_READ, P.VISITORS_INVITE,
        P.ACCESS_READ, P.ACCESS_CHECK, P.MAINTENANCE_READ, P.CAMERA_VIEW, P.RING_READ, P.HARDWARE_READ},
}

SCOPE_PARENTS = {ScopeKind.BUILDING: {ScopeKind.ORGANIZATION},
    ScopeKind.BUSINESS: {ScopeKind.BUILDING},
    ScopeKind.LOCATION: {ScopeKind.BUILDING, ScopeKind.LOCATION, ScopeKind.BUSINESS},
    ScopeKind.PERSON: {ScopeKind.BUILDING, ScopeKind.BUSINESS, ScopeKind.LOCATION}}


class AuthorizationService:
    def __init__(self, repository, principal: Principal, now):
        self.repository, self.principal, self.now = repository, principal, now

    def ancestors(self, scope_id):
        seen, organization = set(), None
        current = self.repository.get_scope(scope_id)
        while current:
            if not current.active or current.id in seen:
                return set()
            if organization is None:
                organization = current.organization_id
            if current.organization_id != organization:
                return set()
            seen.add(current.id)
            if current.parent_id is None:
                return seen if (current.kind == ScopeKind.ORGANIZATION
                                and current.id == organization) else set()
            parent = self.repository.get_scope(current.parent_id)
            if not parent or parent.kind not in SCOPE_PARENTS.get(current.kind, set()):
                return set()
            current = parent
        return set()

    def allowed_scope(self, permission: P, scope_id):
        user = self.repository.get_auth_user(self.principal.user_id)
        if (not user or not user.active or user.person_id != self.principal.person_id
                or not self.repository.get_person(user.person_id)):
            return False
        ancestors = self.ancestors(scope_id)
        return any(a.user_id == user.id and a.active and a.scope_id in ancestors
                   and (a.expires_at is None or self.now < a.expires_at)
                   and permission in a.permissions and permission in ROLE_CEILINGS[a.role]
                   for a in self.repository.list_role_assignments())

    def allowed(self, permission: P, resource_type, resource_id):
        binding = self.repository.get_resource_binding(resource_type, resource_id)
        if not binding or not self.allowed_scope(permission, binding.scope_id):
            return False
        from app.services.resident_boundary import confined, owned
        if confined(self):
            return owned(self, resource_type, resource_id)
        from app.services.business_boundary import confined as business_confined, tenant_owned
        return not business_confined(self) or tenant_owned(self, permission, resource_type, resource_id)

    def require(self, permission: P, resource_type, resource_id):
        if not self.allowed(permission, resource_type, resource_id):
            raise DomainError(403, "Action is not permitted for this resource and scope")

    def require_scope(self, permission: P, scope_id):
        if not self.allowed_scope(permission, scope_id):
            raise DomainError(403, "Action is not permitted in this scope")

    def save_scope(self, scope):
        # Trusted provisioning only. No HTTP scope creation until Phase B.
        with self.repository.transaction():
            old = self.repository.get_scope(scope.id)
            if old and old.model_dump(exclude={"active"}) != scope.model_dump(exclude={"active"}):
                raise DomainError(409, "Scope identity and parent are immutable")
            if scope.kind == ScopeKind.ORGANIZATION:
                if scope.parent_id is not None or scope.id != scope.organization_id:
                    raise DomainError(422, "Invalid organization root")
            else:
                parent = self.repository.get_scope(scope.parent_id)
                if (not parent or not parent.active or parent.organization_id != scope.organization_id
                        or scope.id in self.ancestors(parent.id)):
                    raise DomainError(422, "Invalid scope parent")
                if parent.kind not in SCOPE_PARENTS[scope.kind]:
                    raise DomainError(422, "Invalid typed scope parent")
            self.repository.save_scope(scope)

    def grant(self, assignment):
        with self.repository.transaction():
            owner_appointment = assignment.role == Role.ADMIN and self.allowed_scope(P.OWNERSHIP_MANAGE, assignment.scope_id)
            if not owner_appointment:
                self.require_scope(P.AUTHORIZATION_MANAGE, assignment.scope_id)
            old = self.repository.get_role_assignment(assignment.id)
            if old and (old.user_id, old.scope_id, old.role) != (assignment.user_id, assignment.scope_id, assignment.role):
                raise DomainError(409, "Assignment identity is immutable")
            if old and not owner_appointment:
                self.require_scope(P.AUTHORIZATION_MANAGE, old.scope_id)
            if assignment.role == Role.OWNER:
                raise DomainError(403, "Ownership provisioning requires a trusted recovery operator")
            if not self.repository.get_auth_user(assignment.user_id) or not self.ancestors(assignment.scope_id):
                raise DomainError(422, "Invalid assignment user or scope")
            if not set(assignment.permissions) <= ROLE_CEILINGS[assignment.role]:
                raise DomainError(422, "Permissions exceed the role ceiling")
            # Configuration power never grants operational privileges by itself.
            if not owner_appointment:
                for permission in assignment.permissions:
                    self.require_scope(permission, assignment.scope_id)
            self.repository.save_role_assignment(assignment)

    def revoke(self, identifier):
        with self.repository.transaction():
            assignment = self.repository.get_role_assignment(identifier)
            if not assignment:
                raise DomainError(404, "Assignment not found")
            if not (assignment.role == Role.ADMIN and self.allowed_scope(P.OWNERSHIP_MANAGE, assignment.scope_id)):
                self.require_scope(P.AUTHORIZATION_MANAGE, assignment.scope_id)
            if assignment.role == Role.OWNER:
                raise DomainError(403, "Ownership changes require a trusted recovery operator")
            self.repository.save_role_assignment(assignment.model_copy(update={"active": False}))
