"""Explicit topology, ownership, and affiliations. No implicit authority grants."""
from app.models.authorization import Scope, ScopeKind, Permission as P, Role
from app.models.structure import NodeKind as K, StructureNode, Affiliation
from app.services.errors import DomainError
from app.services.scoped_repository import bind_created


PARENTS = {K.BUILDING: {K.ORGANIZATION}, K.FLOOR: {K.BUILDING},
    K.LOCATION: {K.FLOOR, K.LOCATION}, K.UNIT: {K.LOCATION},
    K.BUSINESS: {K.LOCATION}, K.ROOM: {K.LOCATION, K.UNIT, K.BUSINESS, K.ROOM},
    K.INTEGRATION: {K.BUILDING}, K.DEVICE: {K.BUILDING, K.LOCATION, K.UNIT, K.BUSINESS, K.ROOM}}


def read_permission(node):
    return P.HARDWARE_READ if node.kind in {K.DEVICE, K.INTEGRATION} else P.LOCATIONS_READ


class StructureService:
    def __init__(self, authorization):
        self.auth = authorization
        self.repo = authorization.repository

    def bootstrap_organization(self, identifier, name, *, demo=False):
        """Trusted provisioning only; deliberately has no HTTP route."""
        node = StructureNode(id=identifier, name=name, kind=K.ORGANIZATION,
            organization_id=identifier, scope_id=identifier, demo=demo)
        with self.repo.transaction():
            if self.repo.get_structure_node(identifier) or self.repo.get_scope(identifier):
                raise DomainError(409, "Organization identity already exists")
            self.auth.save_scope(Scope(id=identifier, organization_id=identifier, kind=ScopeKind.ORGANIZATION))
            self.repo.save_structure_node(node)
            bind_created(self.repo, "structure", node.id, node.scope_id)
        return node

    def save(self, node: StructureNode):
        with self.repo.transaction():
            parent = self.repo.get_structure_node(node.parent_id) if node.parent_id else None
            if not parent:
                raise DomainError(403, "Parent is unavailable")
            permission = P.HARDWARE_CONFIGURE if node.kind in {K.INTEGRATION, K.DEVICE} else P.STRUCTURE_CONFIGURE
            self.auth.require(permission, "structure", parent.id)
            if parent.kind not in PARENTS.get(node.kind, set()):
                raise DomainError(422, "Invalid hierarchy parent")
            building = node.id if node.kind == K.BUILDING else parent.building_id
            if node.kind == K.BUSINESS:
                # Its authorization parent is the building, so a floor-only
                # delegate cannot create a resource outside delegated authority.
                self.auth.require(P.STRUCTURE_CONFIGURE, "structure", building)
            scope_id = parent.scope_id if node.kind in {K.INTEGRATION, K.DEVICE} else node.id
            if (node.organization_id != parent.organization_id or node.building_id != building
                    or node.scope_id != scope_id or node.demo != parent.demo):
                raise DomainError(422, "Ownership and scope must match the configured parent")
            existing = self.repo.get_structure_node(node.id)
            if existing:
                self.auth.require(permission, "structure", existing.id)
                # Moves require a future dedicated, audited remapping operation.
                immutable = {"id", "kind", "parent_id", "organization_id", "building_id", "scope_id", "demo", "integration_id", "connection_path"}
                if any(getattr(node, field) != getattr(existing, field) for field in immutable):
                    raise DomainError(409, "Structural identity and ownership cannot be changed")
            elif self.repo.get_scope(node.id):
                raise DomainError(409, "Scope identity already exists")
            binding = self.repo.get_resource_binding("structure", node.id)
            if binding and binding.scope_id != scope_id:
                raise DomainError(409, "Resource ownership conflict")
            if node.kind == K.DEVICE:
                integration = self.repo.get_structure_node(node.integration_id)
                if not integration or integration.kind != K.INTEGRATION:
                    raise DomainError(403, "Integration is unavailable")
                self.auth.require(P.HARDWARE_CONFIGURE, "structure", integration.id)
                if (integration.building_id != building or integration.connection_path != node.connection_path
                        or integration.organization_id != node.organization_id):
                    raise DomainError(422, "Device and integration connection/ownership must match")
            if not existing and node.kind not in {K.INTEGRATION, K.DEVICE}:
                scope_kind = ScopeKind.BUILDING if node.kind == K.BUILDING else ScopeKind.BUSINESS if node.kind == K.BUSINESS else ScopeKind.LOCATION
                # Business authority is independent of physical floor placement.
                scope_parent = building if node.kind == K.BUSINESS else parent.scope_id
                self.auth.save_scope(Scope(id=scope_id, organization_id=node.organization_id,
                    kind=scope_kind, parent_id=scope_parent))
            self.repo.save_structure_node(node)
            bind_created(self.repo, "structure", node.id, scope_id)
            return node

    def get(self, identifier):
        with self.repo.transaction():
            node = self.repo.get_structure_node(identifier)
            if not node:
                raise DomainError(403, "Resource is unavailable")
            self.auth.require(read_permission(node), "structure", identifier)
            return node

    def catalog(self):
        with self.repo.transaction():
            nodes = [n for n in self.repo.list_structure_nodes()
                     if self.auth.allowed(read_permission(n), "structure", n.id)]
            # A scoped partial projection never leaks names of hidden ancestors.
            visible = {n.id for n in nodes}
            return {"schema_version": 1, "nodes": nodes,
                "device_mappings": [{"device_id": n.id, "location_id": n.parent_id,
                    "scope_id": n.scope_id} for n in nodes if n.kind == K.DEVICE and n.parent_id in visible]}

    def device_context(self, identifier):
        with self.repo.transaction():
            node = self.get(identifier)
            if node.kind != K.DEVICE:
                raise DomainError(422, "Resource is not a device")
            path = []
            current = self.repo.get_structure_node(node.parent_id)
            while current:
                if self.auth.allowed(read_permission(current), "structure", current.id):
                    path.append({"id": current.id, "name": current.name, "kind": current.kind})
                current = self.repo.get_structure_node(current.parent_id) if current.parent_id else None
            return {"device_id": node.id, "organization_id": node.organization_id,
                "building_id": node.building_id, "location_id": node.parent_id,
                "scope_id": node.scope_id, "path": list(reversed(path)),
                "connection_path": node.connection_path, "demo": node.demo}

    def save_affiliation(self, record: Affiliation):
        with self.repo.transaction():
            target = self.repo.get_structure_node(record.target_id)
            if not target:
                raise DomainError(403, "Affiliation target unavailable")
            self.auth.require(P.AFFILIATIONS_MANAGE, "structure", target.id)
            user = self.repo.get_auth_user(record.user_id)
            person_binding = self.repo.get_resource_binding("person", user.person_id) if user else None
            if (not user or not user.active or not person_binding
                    or not (self.auth.allowed_scope(P.ACCOUNTS_READ, person_binding.scope_id)
                            or self.auth.allowed(P.PEOPLE_READ, "person", user.person_id))
                    or target.organization_id not in self.auth.ancestors(person_binding.scope_id)):
                raise DomainError(403, "Account unavailable in organization")
            valid = {Role.RESIDENT: {K.UNIT}, Role.BUSINESS_ADMIN: {K.BUSINESS},
                Role.BUSINESS_STAFF: {K.BUSINESS}, Role.MANAGER: {K.BUILDING, K.LOCATION},
                Role.SECURITY: {K.BUILDING, K.LOCATION}, Role.MAINTENANCE: {K.BUILDING, K.LOCATION, K.ROOM}}
            if target.kind not in valid.get(record.role, set()):
                raise DomainError(422, "Role and affiliation target do not match")
            for existing in self.repo.list_affiliations():
                if existing.id == record.id:
                    if (existing.user_id, existing.target_id, existing.role) != (record.user_id, record.target_id, record.role):
                        raise DomainError(409, "Affiliation identity cannot change")
                    continue
                if (record.active and existing.active and existing.user_id == record.user_id
                        and record.role in {Role.BUSINESS_ADMIN, Role.BUSINESS_STAFF}
                        and existing.role in {Role.BUSINESS_ADMIN, Role.BUSINESS_STAFF}
                        and existing.target_id != record.target_id
                        and not (record.ends_at and existing.starts_at and record.ends_at <= existing.starts_at)
                        and not (existing.ends_at and record.starts_at and existing.ends_at <= record.starts_at)):
                    raise DomainError(409, "Overlapping business affiliations are not allowed")
            binding = self.repo.get_resource_binding("affiliation", record.id)
            if binding and binding.scope_id != target.scope_id:
                raise DomainError(409, "Affiliation ownership conflict")
            self.repo.save_affiliation(record)
            bind_created(self.repo, "affiliation", record.id, target.scope_id)
            return record

    def affiliations(self):
        with self.repo.transaction():
            return [a for a in self.repo.list_affiliations()
                    if self.auth.allowed(P.AFFILIATIONS_MANAGE, "structure", a.target_id)]
