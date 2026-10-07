"""Additional E2 tenant confinement, including Resident + Business multi-role."""
from app.models.authorization import Role, Permission as P
from app.services.resident_boundary import physical_path, owned as resident_owned, affiliations as resident_affiliations

BUSINESS_ROLES = {Role.BUSINESS_ADMIN, Role.BUSINESS_STAFF}
TENANT_ROLES = BUSINESS_ROLES | {Role.RESIDENT}


def valid_grants(auth):
    return [a for a in auth.repository.list_role_assignments() if a.user_id == auth.principal.user_id
        and a.active and (a.expires_at is None or auth.now < a.expires_at) and auth.ancestors(a.scope_id)]


def dated(affiliation, now):
    return affiliation.active and (affiliation.starts_at is None or affiliation.starts_at <= now) and (affiliation.ends_at is None or now < affiliation.ends_at)


def contexts(auth):
    repo = auth.repository
    result = []
    for a in repo.list_affiliations():
        if a.user_id != auth.principal.user_id or a.role not in BUSINESS_ROLES or not dated(a,auth.now):
            continue
        node = repo.get_structure_node(a.target_id)
        if node and node.kind.value == 'business' and any(g.role==a.role and g.scope_id in auth.ancestors(node.scope_id)
                and P.LOCATIONS_READ in g.permissions for g in valid_grants(auth)):
            result.append((a,node))
    return result


def confined(auth):
    roles = {g.role for g in valid_grants(auth)}
    return bool(roles) and roles <= TENANT_ROLES and any(a.user_id==auth.principal.user_id and a.role in BUSINESS_ROLES for a in auth.repository.list_affiliations())


def business_permission(auth, permission, node, *, admin_only=False):
    from app.services.authorization import ROLE_CEILINGS
    return any(g.role in ({Role.BUSINESS_ADMIN} if admin_only else BUSINESS_ROLES)
        and g.scope_id in auth.ancestors(node.scope_id) and permission in g.permissions
        and permission in ROLE_CEILINGS[g.role] for g in valid_grants(auth))


def member(repo, user_id, node):
    return any(a.user_id==user_id and a.role in BUSINESS_ROLES and a.target_id==node.id for a in repo.list_affiliations())


def owned(auth, permission, kind, identifier, node):
    repo, person = auth.repository, auth.principal.person_id
    binding = repo.get_resource_binding(kind,identifier)
    if not binding or not business_permission(auth,permission,node):
        return False
    in_scope = node.scope_id in auth.ancestors(binding.scope_id)
    admin = any(a.role==Role.BUSINESS_ADMIN and n.id==node.id for a,n in contexts(auth))
    if kind == 'structure':
        target = repo.get_structure_node(identifier)
        return in_scope and bool(target) and node.id in physical_path(repo,target.id)
    if kind in {'visitor','maintenance'}:
        key = 'host_id' if kind=='visitor' else 'reporter_id'
        return in_scope and any(r['id']==identifier and node.id in physical_path(repo,r.get('location_id'))
            and (admin or r.get(key)==person) for r in repo.list_operational_records(kind))
    if kind in {'person','account'}:
        user = next((u for u in repo.list_auth_users() if (u.person_id if kind=='person' else u.id)==identifier),None)
        return in_scope and bool(user) and member(repo,user.id,node) and (admin or user.person_id==person)
    if kind=='affiliation':
        return in_scope and any(a.id==identifier and a.target_id==node.id and a.role in BUSINESS_ROLES
            and (admin or a.user_id==auth.principal.user_id) for a in repo.list_affiliations())
    if kind=='access_permission':
        return in_scope and any(p.id==identifier and p.person_id==person for p in repo.list_permissions())
    if kind=='location':
        return in_scope or any(p.person_id==person and identifier in p.allowed_zone_ids
            and (b:=repo.get_resource_binding('access_permission',p.id)) and node.scope_id in auth.ancestors(b.scope_id) for p in repo.list_permissions())
    if kind in {'credential','credential_event','actuator_event','journey'}:
        reader = getattr(repo,'get_'+kind)
        record = reader(identifier)
        return in_scope and bool(record) and getattr(record,'person_id',None)==person
    if kind=='ring_event':
        from app.services.ring import identity
        event = repo.get_ring_event(identifier)
        return in_scope and bool(event) and any(d.external_device_id==event.source and d.external_account_key==identity(event.environment,event.account_id)
            and (b:=repo.get_resource_binding('device',d.id)) and node.scope_id in auth.ancestors(b.scope_id) for d in repo.list_building_devices())
    if kind=='operation_activity':
        return in_scope and any(r['id']==identifier and node.id in physical_path(repo,r.get('location_id'))
            and (admin or r.get('actor_id')==person) for r in repo.list_operational_records(kind))
    return in_scope and kind in {'business','announcement','device'}


def tenant_owned(auth, permission, kind, identifier):
    if any(owned(auth,permission,kind,identifier,node) for _,node in contexts(auth)):
        return True
    # Combined Resident/Business authority remains a union of independently
    # authorized tenant contexts, never a client-selected acting identity.
    binding=auth.repository.get_resource_binding(kind,identifier)
    from app.services.authorization import ROLE_CEILINGS
    if binding and resident_affiliations(auth,active=False) and any(g.role==Role.RESIDENT and permission in g.permissions
            and permission in ROLE_CEILINGS[Role.RESIDENT] and g.scope_id in auth.ancestors(binding.scope_id) for g in valid_grants(auth)):
        return resident_owned(auth,kind,identifier)
    return False
