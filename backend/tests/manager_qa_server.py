"""Explicit synthetic Manager browser fixture. Temporary DB only."""
import os
from tempfile import TemporaryDirectory
from datetime import datetime, timezone, timedelta
from cryptography.fernet import Fernet
import uvicorn
from app.sqlite_repository import SQLiteRepository
from app.models.building import Person, PersonRole
from app.models.authorization import RoleAssignment, Role, ResourceBinding, Principal
from app.models.structure import Affiliation
from app.models.manager import MaintenanceInput, AnnouncementInput, VisitorInput, MaintenanceUpdate
from app.models.integrations import BuildingIntegration, BuildingDevice
from app.services.authorization import AuthorizationService, ROLE_CEILINGS
from app.services.auth import AuthService
from app.auth_config import AuthSettings
from app.services.structure import StructureService
from app.services.reference_building import load_reference_building
from app.services.manager import ManagerService


if __name__ == "__main__":
    with TemporaryDirectory(prefix="nodum-manager-qa-") as directory:
        os.environ.update(DATABASE_URL="sqlite:///" + directory + "/manager.db",
            NODUM_AUTHORIZATION_MODE="scoped", APP_ENV="development",
            AUTH_PUBLIC_ORIGIN="http://127.0.0.1:8767", AUTH_TRUSTED_ORIGINS="http://127.0.0.1:5175",
            CORS_ALLOWED_ORIGINS="http://127.0.0.1:5175", CORS_ALLOW_CREDENTIALS="true",
            RING_MODE="simulation", RING_SIGNING_KEY="Synthetic-QA-signing-only",
            RING_ENCRYPTION_KEY=Fernet.generate_key().decode())
        for key in ("AUTH_BOOTSTRAP_USERNAME", "AUTH_BOOTSTRAP_PASSWORD", "AUTH_BOOTSTRAP_PERSON_ID"):
            os.environ.pop(key, None)
        now = datetime.now(timezone.utc)
        repo = SQLiteRepository(os.environ["DATABASE_URL"])
        repo.initialize(seed_demo=True)
        def account(identifier, name):
            repo.save_configured_person(Person(id=identifier, name=name, role=PersonRole.EMPLOYEE))
            return AuthService(repo, AuthSettings.from_env()).create_user(identifier, "Synthetic-local-QA-only", identifier, now)
        admin = account("qa-config", "Synthetic Admin")
        auth = AuthorizationService(repo, Principal(user_id=admin.id, person_id=admin.person_id), now)
        structure = StructureService(auth)
        structure.bootstrap_organization("qa-demo", "Synthetic QA organization", demo=True)
        repo.save_role_assignment(RoleAssignment(id="qa-config-grant", user_id=admin.id, role=Role.ADMIN,
            scope_id="qa-demo", permissions=list(ROLE_CEILINGS[Role.ADMIN])))
        load_reference_building(structure, "qa-demo")
        prefix = "qa-demo:reference:"
        building = prefix + "building"
        def bind(kind, identifier, scope):
            repo.save_resource_binding(ResourceBinding(resource_type=kind, resource_id=identifier, scope_id=scope))
        manager = account("qa-manager", "Marwane (Synthetic)")
        ops = [p for p in ROLE_CEILINGS[Role.MANAGER] if p.value not in {"structure.configure", "hardware.configure", "accounts.manage"}]
        repo.save_role_assignment(RoleAssignment(id="qa-manager-grant", user_id=manager.id, role=Role.MANAGER,
            scope_id=building, permissions=ops))
        bind("person", manager.person_id, building)
        # Explicit test-only legacy/product associations, never startup inference.
        for identifier, name, role, target in (
            ("qa-resident", "Ahmed Benali (Synthetic)", Role.RESIDENT, "apartment-101"),
            ("qa-staff", "Youssef (Synthetic)", Role.BUSINESS_STAFF, "business-x"),
            ("qa-maintenance", "Maintenance team (Synthetic)", Role.MAINTENANCE, "building")):
            user = account(identifier, name)
            bind("person", user.person_id, prefix + target)
            affiliation = Affiliation(id=identifier + "-affiliation", user_id=user.id, role=role,
                target_id=prefix + target, ends_at=now + timedelta(days=365))
            repo.save_affiliation(affiliation)
            bind("affiliation", affiliation.id, prefix + target)
        for identifier, scope in (("lobby", "ground-location-0"), ("machine-room", "underground-room-0"), ("office-106", "business-x")):
            bind("location", identifier, prefix + scope)
        for identifier in ("resident-1", "manager-1"):
            bind("person", identifier, building)
        bind("business", "atlas-dental", prefix + "business-x")
        bind("simulation", "ring", building)
        integration = BuildingIntegration(id="qa-sim-security", name="Synthetic security connector", kind="sensing",
            provider="simulator", enabled=True, created_at=now, updated_at=now)
        repo.save_integration(integration)
        device = BuildingDevice(id="qa-lobby-camera", name="Lobby camera (Synthetic)", integration_id=integration.id,
            device_type="ring_device", zone_id="lobby", capabilities=["motion"], connection_status="offline",
            provider="simulator", simulated=True, created_at=now)
        repo.save_device(device)
        bind("device", device.id, prefix + "ground-location-0")
        service = ManagerService(AuthorizationService(repo, Principal(user_id=manager.id, person_id=manager.person_id), now))
        request = service.create("maintenance", MaintenanceInput(location_id=prefix + "apartment-304",
            title="Kitchen water leak — Apartment 304", description="Synthetic maintenance issue for Manager QA.", priority="high"))
        service.update_maintenance(request["id"], MaintenanceUpdate(status="in_progress", assignee_id="qa-maintenance", note="Synthetic team investigating"))
        service.create("announcement", AnnouncementInput(location_id=building, title="Elevator maintenance",
            message="Synthetic notice: planned inspection tomorrow.", audience="all"))
        service.invite(VisitorInput(location_id=prefix + "business-x", name="Atlas visitor (Synthetic)",
            starts_at=now - timedelta(minutes=30), ends_at=now + timedelta(hours=3)))
        uvicorn.run("app.main:app", host="127.0.0.1", port=8767, log_level="warning")
