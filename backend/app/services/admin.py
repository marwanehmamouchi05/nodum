"""Admin configuration boundary. All authority derives from live Phase A grants."""
from uuid import uuid4
from app.models.authorization import Scope, ScopeKind, Permission as P, Role, ResourceBinding
from app.models.structure import StructureNode, NodeKind as K
from app.services.authorization import ROLE_CEILINGS
from app.services.structure import StructureService
from app.services.scoped_repository import bind_created
from app.services.errors import DomainError
from app.services.reference_building import load_reference_building


class AdminService(StructureService):
    def audit(self, action, identifier, scope_id):
        self.repo.append_configuration_audit({"id": str(uuid4()), "action": action,
            "resource_id": identifier, "scope_id": scope_id,
            "actor_user_id": self.auth.principal.user_id, "at": self.auth.now.isoformat()})

    def organizations(self):
        return [s for s in self.repo.list_scopes() if s.kind == ScopeKind.ORGANIZATION
            and any(self.auth.allowed_scope(p, s.id) for p in
                (P.STRUCTURE_CONFIGURE, P.ACCOUNTS_READ, P.AUTHORIZATION_MANAGE, P.HARDWARE_CONFIGURE, P.OWNERSHIP_MANAGE))]

    def create_organization(self, payload):
        with self.repo.transaction():
            self.auth.require_scope(P.STRUCTURE_CONFIGURE, payload.scope_id)
            scope = self.repo.get_scope(payload.scope_id)
            if not scope or scope.kind != ScopeKind.ORGANIZATION:
                raise DomainError(422, "Choose your provisioned organization")
            if self.repo.get_structure_node(scope.id):
                raise DomainError(409, "Organization already configured")
            if not payload.name.strip():
                raise DomainError(422, "Enter an organization name")
            node = StructureNode(id=scope.id, name=payload.name.strip(), kind=K.ORGANIZATION,
                organization_id=scope.id, scope_id=scope.id, demo=payload.demo)
            self.repo.save_structure_node(node)
            bind_created(self.repo, "structure", node.id, scope.id)
            self.audit("organization.created", node.id, node.scope_id)
            return node

    def save(self, node):
        with self.repo.transaction():
            result = super().save(node)
            self.audit("structure.saved", result.id, result.scope_id)
            return result

    def map_device(self, identifier, location_id):
        with self.repo.transaction():
            self.auth.require(P.HARDWARE_CONFIGURE, "structure", identifier)
            self.auth.require(P.HARDWARE_CONFIGURE, "structure", location_id)
            device, location = self.repo.get_structure_node(identifier), self.repo.get_structure_node(location_id)
            if (not device or device.kind != K.DEVICE or not location
                    or location.kind not in {K.LOCATION, K.UNIT, K.BUSINESS, K.ROOM}
                    or device.building_id != location.building_id
                    or device.organization_id != location.organization_id):
                raise DomainError(422, "Choose a location in this device's building")
            mapped = device.model_copy(update={"parent_id": location.id, "scope_id": location.scope_id})
            self.repo.save_structure_node(mapped)
            self.repo.save_resource_binding(ResourceBinding(resource_type="structure", resource_id=device.id, scope_id=location.scope_id))
            self.audit("device.mapped", device.id, location.scope_id)
            return mapped

    def accounts(self):
        with self.repo.transaction():
            result = []
            for user in self.repo.list_auth_users():
                if not self.auth.allowed(P.ACCOUNTS_READ, "account", user.id):
                    continue
                person = self.repo.get_person(user.person_id)
                result.append({"id": user.id, "username": user.username, "name": person.name if person else "Account",
                    "person_id": user.person_id, "active": user.active,
                    "scope_id": self.repo.get_resource_binding("account", user.id).scope_id})
            return result

    def create_account(self, payload):
        from app.services.account_provisioning import provision_account
        with self.repo.transaction():
            self.auth.require_scope(P.ACCOUNTS_MANAGE, payload.scope_id)
            account = provision_account(self.auth, payload)
            self.audit("account.created", account["id"], account["scope_id"])
            return account

    def set_account_state(self, identifier, active):
        with self.repo.transaction():
            self.auth.require(P.ACCOUNTS_MANAGE, "account", identifier)
            user = self.repo.get_auth_user(identifier)
            if not user or identifier == self.auth.principal.user_id:
                raise DomainError(409, "Your own account cannot be suspended here")
            if any(a.user_id == identifier and a.role == Role.OWNER and a.active for a in self.repo.list_role_assignments()):
                raise DomainError(403, "Owner changes require the recovery operator")
            self.repo.save_auth_user(user.model_copy(update={"active": active}))
            self.audit("account.activated" if active else "account.suspended", identifier,
                self.repo.get_resource_binding("account", identifier).scope_id)
            return {"id": identifier, "active": active}

    def grant_options(self, scope_id):
        if self.auth.allowed_scope(P.OWNERSHIP_MANAGE, scope_id):
            return {Role.ADMIN.value: [p.value for p in sorted(ROLE_CEILINGS[Role.ADMIN], key=lambda p: p.value)]}
        self.auth.require_scope(P.AUTHORIZATION_MANAGE, scope_id)
        return {role.value: [p.value for p in sorted(ceiling, key=lambda p: p.value)
            if self.auth.allowed_scope(p, scope_id)] for role, ceiling in ROLE_CEILINGS.items() if role != Role.OWNER}

    def setup(self, building_id, payload=None):
        with self.repo.transaction():
            self.auth.require(P.STRUCTURE_CONFIGURE, "structure", building_id)
            building = self.repo.get_structure_node(building_id)
            if not building or building.kind != K.BUILDING:
                raise DomainError(422, "Choose a building")
            if payload:
                if payload.completed:
                    nodes = [n for n in self.repo.list_structure_nodes() if n.building_id == building_id]
                    if (not payload.policy_reviewed or not any(n.kind == K.FLOOR for n in nodes)
                            or not any(n.kind == K.LOCATION for n in nodes)
                            or any(n.kind == K.DEVICE and n.parent_id == building_id for n in nodes)):
                        raise DomainError(422, "Add floors and areas, assign registered devices, and review policy boundaries before finishing setup")
                self.repo.save_admin_settings(building_id, building.scope_id, payload.model_dump())
                self.audit("setup.saved", building_id, building.scope_id)
            return self.repo.get_admin_settings(building_id) or {"step": "Building", "policy_reviewed": False, "completed": False}

    def demo(self, organization_id):
        with self.repo.transaction():
            self.auth.require_scope(P.STRUCTURE_CONFIGURE, organization_id)
            self.auth.require_scope(P.HARDWARE_CONFIGURE, organization_id)
            root = self.repo.get_structure_node(organization_id)
            # Production root is never converted to demo. Create a separate
            # demo organization only through trusted Phase B provisioning.
            if not root or not root.demo:
                raise DomainError(409, "Choose a separately provisioned demo organization")
            result = load_reference_building(self, organization_id)
            self.audit("demo.loaded", organization_id, organization_id)
            return result

    def audit_records(self):
        with self.repo.transaction():
            return [r for r in self.repo.list_configuration_audit()
                if self.auth.allowed_scope(P.STRUCTURE_CONFIGURE, r["scope_id"])]

    def ring_configuration(self):
        """Owner/configuration metadata only, never tokens, events or cameras."""
        with self.repo.transaction():
            principal = self.auth.principal
            accounts = [a for a in self.repo.list_ring_accounts()
                if a.owner_user_id == principal.user_id and a.owner_id == principal.person_id
                and self.auth.allowed(P.RING_MANAGE, "ring_account", a.id)]
            return {"accounts": [{"status": a.status, "environment": a.environment} for a in accounts],
                "state": "connected" if any(a.status == "completed" for a in accounts) else "not_connected",
                "discovery_verified": False}

    def prepare_ring(self, building_id):
        """Explicit installation binding for the preserved signed Ring flow."""
        with self.repo.transaction():
            self.auth.require(P.HARDWARE_CONFIGURE, "structure", building_id)
            self.auth.require(P.RING_MANAGE, "structure", building_id)
            building = self.repo.get_structure_node(building_id)
            if not building or building.kind != K.BUILDING:
                raise DomainError(422, "Choose a building")
            old = self.repo.get_resource_binding("ring_link", "installation")
            if old:
                self.auth.require_scope(P.RING_MANAGE, old.scope_id)
                if building.organization_id not in self.auth.ancestors(old.scope_id):
                    raise DomainError(409, "Ring installation is configured for another organization")
            identifier = "ring-configuration:" + building.id
            existing = self.repo.get_structure_node(identifier)
            node = StructureNode(id=identifier, name="Ring cloud configuration", kind=K.INTEGRATION,
                organization_id=building.organization_id, building_id=building.id,
                parent_id=building.id, scope_id=building.scope_id, demo=building.demo,
                connection_path="cloud")
            if existing and existing != node:
                raise DomainError(409, "Ring configuration identity has existing settings")
            self.save(node)
            if not old:
                bind_created(self.repo, "ring_link", "installation", building.scope_id)
            self.audit("ring.setup_prepared", identifier, building.scope_id)
            return {"integration": node, "connection_state": "provider_confirmation_required"}
