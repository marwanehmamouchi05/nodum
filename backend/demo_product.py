"""Explicit disposable scoped product demo. Never opens the runtime database.

Run: .venv/Scripts/python.exe demo_product.py --start
The database and generated Ring signing/encryption keys exist only for this run.
"""
import argparse
import os
import secrets
from datetime import datetime, timedelta, timezone
from tempfile import TemporaryDirectory

PASSWORD = "Synthetic-demo-only-2026"
PREFIX = "demo:reference:"


def seed_demo(repo, now):
    from app.models.authorization import Principal, Role, RoleAssignment, ResourceBinding, Permission as P
    from app.models.building import Person, PersonRole
    from app.models.structure import Affiliation
    from app.models.manager import AnnouncementInput, MaintenanceInput
    from app.services.auth import AuthService
    from app.auth_config import AuthSettings
    from app.services.authorization import AuthorizationService, ROLE_CEILINGS
    from app.services.structure import StructureService
    from app.services.reference_building import load_reference_building
    from app.services.manager import ManagerService

    users = {}
    def account(name, label):
        repo.save_configured_person(Person(id=name, name=label + " (Synthetic)", role=PersonRole.EMPLOYEE))
        users[name] = AuthService(repo, AuthSettings.from_env()).create_user(name, PASSWORD, name, now)
        return users[name]
    def grant(name, role, scope, permissions=None):
        repo.save_role_assignment(RoleAssignment(id=name+"-"+role.value, user_id=users[name].id,
            role=role, scope_id=scope, permissions=list(ROLE_CEILINGS[role] if permissions is None else permissions)))
    def affiliate(name, role, target):
        a = Affiliation(id=name+"-"+role.value+"-affiliation", user_id=users[name].id,
            role=role, target_id=target, ends_at=now+timedelta(days=365))
        repo.save_affiliation(a)
        repo.save_resource_binding(ResourceBinding(resource_type="affiliation", resource_id=a.id, scope_id=target))
    admin = account("demo-admin", "Building Admin")
    auth = AuthorizationService(repo, Principal(user_id=admin.id, person_id=admin.person_id), now)
    structure = StructureService(auth)
    structure.bootstrap_organization("demo", "Synthetic demonstration organization", demo=True)
    grant("demo-admin", Role.ADMIN, "demo")
    load_reference_building(structure, "demo")
    account("demo-owner", "Ownership recovery")
    grant("demo-owner", Role.OWNER, "demo")
    # Manager configuration powers are intentionally omitted from this operator.
    operator_permissions = ROLE_CEILINGS[Role.MANAGER] - {P.ACCOUNTS_MANAGE, P.STRUCTURE_CONFIGURE,
        P.AFFILIATIONS_MANAGE, P.HARDWARE_CONFIGURE}
    for name, label, role, target in (
        ("demo-manager", "Marwane", Role.MANAGER, "building"),
        ("demo-resident", "Ahmed", Role.RESIDENT, "apartment-101"),
        ("demo-resident-102", "Resident 102", Role.RESIDENT, "apartment-102"),
        ("demo-business", "Business X Admin", Role.BUSINESS_ADMIN, "business-x"),
        ("demo-staff", "Business X Staff", Role.BUSINESS_STAFF, "business-x"),
        ("demo-business-y", "Business Y Admin", Role.BUSINESS_ADMIN, "business-y"),
    ):
        account(name, label)
        grant(name, role, PREFIX+target, operator_permissions if role==Role.MANAGER else None)
        affiliate(name, role, PREFIX+target)
        for kind, key in (("person", name), ("account", users[name].id)):
            repo.save_resource_binding(ResourceBinding(resource_type=kind, resource_id=key, scope_id=PREFIX+target))
    # A genuine multi-role account: UI switching never changes this identity.
    account("demo-presenter", "Nodum presenter")
    for kind, key in (("person", "demo-presenter"), ("account", users["demo-presenter"].id)):
        repo.save_resource_binding(ResourceBinding(resource_type=kind, resource_id=key, scope_id=PREFIX+"building"))
    for role, target in ((Role.ADMIN, "demo"), (Role.MANAGER, PREFIX+"building"),
                         (Role.RESIDENT, PREFIX+"apartment-101"), (Role.BUSINESS_ADMIN, PREFIX+"business-x")):
        grant("demo-presenter", role, target, operator_permissions if role==Role.MANAGER else None)
        if role in {Role.RESIDENT, Role.BUSINESS_ADMIN}:
            affiliate("demo-presenter", role, target)
    repo.save_resource_binding(ResourceBinding(resource_type="simulation", resource_id="ring", scope_id=PREFIX+"building"))
    # Explicit provider-to-product association; no visitor identity/destination inference.
    from app.models.integrations import BuildingIntegration, BuildingDevice
    from app.integrations.ring.config import RingSettings
    from app.services.ring import identity
    from app.services.ring_simulation import SIM_DEVICES
    repo.save_integration(BuildingIntegration(id="demo-ring-signals", name="Synthetic Ring signals",
        kind="sensing", provider="simulator", created_at=now, updated_at=now))
    for d in SIM_DEVICES:
        identifier = "demo-"+d["id"]
        location = PREFIX+("underground-room-1" if d["zone_id"]=="utility-room" else "ground-location-1")
        repo.save_device(BuildingDevice(id=identifier, name=d["name"], integration_id="demo-ring-signals",
            device_type="ring_device", zone_id=d["zone_id"], capabilities=d["capabilities"], provider="simulator", simulated=True,
            external_device_id=d["id"], external_account_key=identity(RingSettings.from_env().environment,"simulation.playground"), created_at=now))
        repo.save_resource_binding(ResourceBinding(resource_type="device", resource_id=identifier, scope_id=location))
    manager_user = users["demo-manager"]
    manager = ManagerService(AuthorizationService(repo, Principal(user_id=manager_user.id, person_id=manager_user.person_id), now))
    manager.create("announcement", AnnouncementInput(location_id=PREFIX+"building", title="Main entrance maintenance at 18:00",
        message="Use the marked entrance during the inspection. Synthetic demonstration notice.", audience="all"))
    manager.create("announcement", AnnouncementInput(location_id=PREFIX+"floor1", title="Water inspection tomorrow",
        message="The building team will inspect the Floor 1 water supply.", audience="residential"))
    manager.create("announcement", AnnouncementInput(location_id=PREFIX+"business-x", title="Business X reception update",
        message="Reception is open until 18:00.", audience="business"))
    manager.create("maintenance", MaintenanceInput(location_id=PREFIX+"building", title="Lobby lighting inspection",
        description="Synthetic request for the building team."))
    return users


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", action="store_true", help="Explicitly load synthetic data into a disposable DB and start localhost:8770")
    args = parser.parse_args()
    if not args.start:
        parser.error("Pass --start to explicitly load the synthetic demo; no data has been changed")
    with TemporaryDirectory(prefix="nodum-product-demo-") as directory:
        from cryptography.fernet import Fernet
        os.environ.update(DATABASE_URL="sqlite:///"+directory+"/demo.db", NODUM_AUTHORIZATION_MODE="scoped",
            APP_ENV="development", AUTH_PUBLIC_ORIGIN="http://127.0.0.1:8770",
            AUTH_TRUSTED_ORIGINS="http://127.0.0.1:5178", CORS_ALLOWED_ORIGINS="http://127.0.0.1:5178",
            CORS_ALLOW_CREDENTIALS="true", RING_MODE="simulation", RING_SIGNING_KEY=secrets.token_urlsafe(32),
            RING_ENCRYPTION_KEY=Fernet.generate_key().decode())
        for key in ("AUTH_BOOTSTRAP_USERNAME", "AUTH_BOOTSTRAP_PASSWORD", "AUTH_BOOTSTRAP_PERSON_ID"):
            os.environ.pop(key, None)
        from app.sqlite_repository import SQLiteRepository
        repo = SQLiteRepository(os.environ["DATABASE_URL"])
        repo.initialize(seed_demo=False)
        users = seed_demo(repo, datetime.now(timezone.utc))
        from app.main import app
        from app.api.agent import get_gateway
        from app.integrations.bedrock import BedrockUnavailable
        class LocalDemoGateway:
            def converse(self, **kwargs):
                raise BedrockUnavailable("Local demo uses Guide; AWS inference is not enabled")
        app.dependency_overrides[get_gateway] = lambda: LocalDemoGateway()
        print("DEMO / SYNTHETIC — disposable data, no physical control, local Guide only", flush=True)
        print("Accounts: " + ", ".join(users) + "\nSynthetic local password: " + PASSWORD, flush=True)
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=8770, log_level="warning")


if __name__ == "__main__":
    main()
