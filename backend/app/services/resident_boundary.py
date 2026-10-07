"""Additional personal ownership boundary for configured Resident-only principals.

Legacy/unaffiliated Phase A identities retain their audited scope behavior. Once
resident affiliation is configured, inactive/expired residency never falls back.
Delegated operational multi-role principals keep their separate operator authority.
"""
from app.models.authorization import Role


def affiliations(auth, *, active=True):
    now, repo = auth.now, auth.repository
    records = [a for a in repo.list_affiliations() if a.user_id == auth.principal.user_id and a.role == Role.RESIDENT]
    if active:
        records = [a for a in records if a.active and (a.starts_at is None or a.starts_at <= now)
                   and (a.ends_at is None or now < a.ends_at)]
    return records


def confined(auth):
    roles = {a.role for a in auth.repository.list_role_assignments() if a.user_id == auth.principal.user_id
             and a.active and (a.expires_at is None or auth.now < a.expires_at)
             and auth.ancestors(a.scope_id)}
    return roles == {Role.RESIDENT} and bool(affiliations(auth, active=False))


def units(auth):
    return [n for a in affiliations(auth) if (n := auth.repository.get_structure_node(a.target_id))
            and n.kind.value == "unit" and auth.ancestors(n.scope_id)]


def owned(auth, kind, identifier):
    repo, person = auth.repository, auth.principal.person_id
    homes = units(auth)
    scope = repo.get_resource_binding(kind, identifier)
    if not scope:
        return False
    own_scope = any(n.scope_id in auth.ancestors(scope.scope_id) for n in homes)
    if kind in {"visitor", "maintenance"}:
        field = "host_id" if kind == "visitor" else "reporter_id"
        return own_scope and any(r["id"] == identifier and r.get(field) == person
                                and r.get("location_id") in {n.id for n in homes}
                                for r in repo.list_operational_records(kind))
    if kind == "person":
        return identifier == person or (own_scope and any(p.person_id == identifier and p.granted_by == person for p in repo.list_permissions()))
    if kind == "access_permission":
        return bool(homes) and any(p.id == identifier and (p.person_id == person or own_scope and p.granted_by == person) for p in repo.list_permissions())
    if kind in {"credential", "credential_event", "actuator_event", "journey"}:
        readers = {"credential": repo.get_credential, "credential_event": repo.get_credential_event,
                   "actuator_event": repo.get_actuator_event, "journey": repo.get_journey}
        record = readers[kind](identifier)
        return bool(record and getattr(record, "person_id", None) == person and own_scope)
    if kind == "structure":
        node = repo.get_structure_node(identifier)
        if not node:
            return False
        if node.kind.value in {"device", "integration"}:
            return own_scope
        return any(node.id in physical_path(repo, home.id) for home in homes)
    if kind in {"announcement", "affiliation", "device", "location", "ring_event"}:
        if kind == "affiliation":
            return any(a.id == identifier for a in affiliations(auth))
        if kind == "ring_event":
            from app.services.ring import identity
            event = repo.get_ring_event(identifier)
            return own_scope and bool(event) and any(d.external_device_id == event.source
                and d.external_account_key == identity(event.environment, event.account_id)
                and (b := repo.get_resource_binding("device", d.id))
                and any(n.scope_id in auth.ancestors(b.scope_id) for n in homes)
                for d in repo.list_building_devices())
        if kind == "device":
            return own_scope
        if kind == "location":
            return own_scope or bool(homes) and any(p.person_id == person and identifier in p.allowed_zone_ids for p in repo.list_permissions())
        return own_scope
    # Resident does not read another business's visits, operational incidents,
    # work orders, configuration, or global activity through generic endpoints.
    return False


def physical_path(repo, identifier):
    result, seen = [], set()
    while identifier and identifier not in seen:
        seen.add(identifier)
        node = repo.get_structure_node(identifier)
        if not node:
            break
        result.append(node.id)
        identifier = node.parent_id
    return result
