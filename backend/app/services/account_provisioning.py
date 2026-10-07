"""Shared trusted account storage; callers enforce their scoped capability first."""
import re
from uuid import uuid4
from app.models.auth import NodumUser
from app.models.building import Person, PersonRole
from app.models.authorization import Scope, ScopeKind
from app.services.auth import hash_password
from app.services.scoped_repository import bind_created
from app.services.errors import DomainError


def provision_account(auth, payload):
    repo, username = auth.repository, payload.username.strip().lower()
    if not re.fullmatch(r'[a-z0-9][a-z0-9@._+-]{2,127}',username) or not payload.name.strip():
        raise DomainError(422,'Enter a name and valid login name')
    scope = repo.get_scope(payload.scope_id)
    if not scope or not auth.ancestors(scope.id) or scope.kind not in {ScopeKind.BUILDING,ScopeKind.BUSINESS,ScopeKind.LOCATION}:
        raise DomainError(422,'Choose an authorized building, unit, business or area')
    if any(u.username==username for u in repo.list_auth_users()):
        raise DomainError(409,'Login name already exists')
    encoded = hash_password(payload.password.get_secret_value())
    person_id,user_id,scope_id = str(uuid4()),str(uuid4()),str(uuid4())
    auth.save_scope(Scope(id=scope_id,organization_id=scope.organization_id,kind=ScopeKind.PERSON,parent_id=scope.id))
    repo.save_configured_person(Person(id=person_id,name=payload.name.strip(),role=PersonRole.EMPLOYEE))
    repo.save_auth_user(NodumUser(id=user_id,username=username,person_id=person_id,password_hash=encoded,created_at=auth.now))
    bind_created(repo,'person',person_id,scope_id); bind_created(repo,'account',user_id,scope_id)
    return {'id':user_id,'username':username,'name':payload.name.strip(),'person_id':person_id,'active':True,'scope_id':scope_id}
