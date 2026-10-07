"""Explicit first-install provisioning. No public bootstrap authorization."""
import re
from uuid import uuid4
from app.models.auth import NodumUser
from app.models.building import Person, PersonRole
from app.models.authorization import Scope, ScopeKind, ResourceBinding, RoleAssignment, Role
from app.services.authorization import ROLE_CEILINGS
from app.services.auth import hash_password
from app.services.errors import DomainError


def provision_first_admin(repo, name, username, password, now):
    username = username.strip().lower()
    if not name.strip() or not re.fullmatch(r"[a-z0-9][a-z0-9@._+-]{2,127}", username):
        raise DomainError(422, "Provide a name and valid login name")
    encoded = hash_password(password)
    with repo.transaction():
        if (repo.list_people() or repo.list_zones() or repo.list_auth_users()
                or repo.list_scopes() or repo.list_structure_nodes()):
            raise DomainError(409, "First-install provisioning requires an empty installation")
        person_id, user_id, organization_id = str(uuid4()), str(uuid4()), str(uuid4())
        repo.save_configured_person(Person(id=person_id, name=name.strip(), role=PersonRole.EMPLOYEE))
        repo.save_auth_user(NodumUser(id=user_id, username=username, person_id=person_id,
            password_hash=encoded, created_at=now))
        repo.save_scope(Scope(id=organization_id, organization_id=organization_id, kind=ScopeKind.ORGANIZATION))
        for resource_type, identifier in (("person", person_id), ("account", user_id)):
            repo.save_resource_binding(ResourceBinding(resource_type=resource_type, resource_id=identifier, scope_id=organization_id))
        for role in (Role.OWNER, Role.ADMIN):
            repo.save_role_assignment(RoleAssignment(id=str(uuid4()), user_id=user_id,
                role=role, scope_id=organization_id, permissions=list(ROLE_CEILINGS[role])))
        return {"user_id": user_id, "organization_id": organization_id}
