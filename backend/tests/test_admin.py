"""Admin configuration, actual sessions, migrations, and isolated storage."""
import sqlite3
import pytest
from app.models.admin import AccountInput, OrganizationInput, SetupInput
from app.models.authorization import Permission as P, Principal, Role, RoleAssignment, Scope, ScopeKind
from app.models.structure import NodeKind as K, StructureNode
from app.services.admin import AdminService
from app.services.authorization import AuthorizationService
from app.services.errors import DomainError
from app.sqlite_repository import SQLiteRepository
from app.database import MIGRATIONS
from test_structure import structure, user_service
from test_authorization import headers
from conftest import NOW


@pytest.fixture
def admin(structure):
    grant = structure.repo.get_role_assignment("admin-grant")
    structure.repo.save_role_assignment(grant.model_copy(update={"permissions": grant.permissions + [P.ACCOUNTS_MANAGE, P.AUTHORIZATION_MANAGE]}))
    return AdminService(structure.auth)


def create(admin, suffix="101"):
    return admin.create_account(AccountInput(name="Synthetic Resident", username="resident-" + suffix,
        password="Synthetic-only-fixture-password", scope_id="demo-org:reference:apartment-" + suffix))


def test_created_account_private_binding_no_grants_no_password_disclosure(admin):
    result = create(admin)
    account = admin.repo.get_auth_user(result["id"])
    assert account.password_hash.startswith("pbkdf2_sha256$")
    assert account.password_hash != "Synthetic-only-fixture-password"
    assert admin.repo.get_resource_binding("account", account.id).scope_id == result["scope_id"]
    assert admin.repo.get_resource_binding("person", account.person_id).scope_id == result["scope_id"]
    assert admin.repo.get_scope(result["scope_id"]).kind == ScopeKind.PERSON
    assert admin.repo.get_scope(result["scope_id"]).parent_id == "demo-org:reference:apartment-101"
    assert not any(a.user_id == account.id for a in admin.repo.list_role_assignments())
    assert not any(p.person_id == account.person_id for p in admin.repo.list_permissions())
    assert "password" not in str(admin.accounts()).lower()
    assert "fixture-password" not in str(admin.audit_records())


@pytest.mark.parametrize("username,password,scope", [
    ("x", "Synthetic-only-fixture-password", "demo-org:reference:apartment-101"),
    ("bad name", "Synthetic-only-fixture-password", "demo-org:reference:apartment-101"),
    ("valid-name", "short", "demo-org:reference:apartment-101"),
    ("valid-name", "Synthetic-only-fixture-password", "missing"),
    ("valid-name", "Synthetic-only-fixture-password", "demo-org"),
])
def test_invalid_account_no_partial_person_or_scope(admin, username, password, scope):
    before = (admin.repo.list_people(), admin.repo.list_scopes(), admin.repo.list_auth_users())
    with pytest.raises((DomainError, ValueError)):
        admin.create_account(AccountInput(name="Synthetic", username=username, password=password, scope_id=scope))
    assert before == (admin.repo.list_people(), admin.repo.list_scopes(), admin.repo.list_auth_users())


def test_duplicate_login_and_revocation(admin):
    create(admin)
    with pytest.raises(DomainError):
        create(admin)
    grant = admin.repo.get_role_assignment("admin-grant")
    admin.repo.save_role_assignment(grant.model_copy(update={"active": False}))
    assert admin.accounts() == []
    with pytest.raises(DomainError):
        create(admin, "102")


def test_business_and_resident_account_list_isolation(admin):
    first = create(admin)
    second = create(admin, "102")
    resident = user_service(admin, "resident", "demo-org:reference:apartment-101", Role.ADMIN, [P.ACCOUNTS_READ])
    assert [a["id"] for a in AdminService(resident.auth).accounts()] == [first["id"]]
    assert second["id"] not in str(AdminService(resident.auth).accounts())
    x = admin.create_account(AccountInput(name="Synthetic X", username="business-x-new",
        password="Synthetic-only-fixture-password", scope_id="demo-org:reference:business-x"))
    admin.create_account(AccountInput(name="Synthetic Y", username="business-y-new",
        password="Synthetic-only-fixture-password", scope_id="demo-org:reference:business-y"))
    business = user_service(admin, "business", "demo-org:reference:business-x", Role.ADMIN, [P.ACCOUNTS_READ])
    assert [a["id"] for a in AdminService(business.auth).accounts()] == [x["id"]]


def test_grant_options_conservative_and_manager_without_setup(admin):
    options = admin.grant_options("demo-org:reference:building")
    assert "owner" not in options
    assert "incidents.manage" not in options["manager"]
    assert "camera.view" not in options["admin"]
    assert "accounts.manage" in options["manager"]
    manager = user_service(admin, "resident", "demo-org:reference:building", Role.MANAGER, [P.LOCATIONS_READ])
    with pytest.raises(DomainError):
        AdminService(manager.auth).create_account(AccountInput(name="Blocked", username="blocked-user",
            password="Synthetic-only-fixture-password", scope_id="demo-org:reference:building"))


def test_unassigned_device_mapping_binding_and_context(admin):
    building = "demo-org:reference:building"
    device = StructureNode(id="unassigned-device", name="Demo unassigned sensor", kind=K.DEVICE,
        organization_id="demo-org", building_id=building, parent_id=building, scope_id=building,
        demo=True, integration_id="demo-org:reference:simulation", connection_path="simulation", device_type="sensor")
    admin.save(device)
    target = "demo-org:reference:business-x"
    mapped = admin.map_device(device.id, target)
    assert mapped.parent_id == mapped.scope_id == target
    assert admin.repo.get_resource_binding("structure", device.id).scope_id == target
    assert admin.device_context(device.id)["location_id"] == target
    assert any(r["action"] == "device.mapped" for r in admin.audit_records())


def test_mapping_cross_building_and_unavailable_destinations_denied(admin):
    original = admin.repo.get_structure_node("demo-org:reference:lobby-camera")
    for target in ("missing", "demo-org", "demo-org:reference:simulation"):
        with pytest.raises(DomainError):
            admin.map_device(original.id, target)
    assert admin.repo.get_structure_node(original.id) == original


def test_mapping_requires_source_and_destination_scope(admin):
    user = user_service(admin, "business", "demo-org:reference:business-x", Role.MANAGER, [P.HARDWARE_CONFIGURE])
    service = AdminService(user.auth)
    with pytest.raises(DomainError):
        service.map_device("demo-org:reference:lobby-camera", "demo-org:reference:business-x")
    with pytest.raises(DomainError):
        service.map_device("demo-org:reference:business-x-camera", "demo-org:reference:business-y")


def test_setup_persisted_and_not_policy_activation(admin):
    building = "demo-org:reference:building"
    before = admin.repo.list_permissions()
    payload = SetupInput(step="Policies", policy_reviewed=True)
    assert admin.setup(building, payload) == payload.model_dump()
    assert admin.setup(building) == payload.model_dump()
    assert admin.repo.list_permissions() == before
    if isinstance(admin.repo, SQLiteRepository):
        reopened = SQLiteRepository(f"sqlite:///{admin.repo.database.path}")
        reopened.initialize(seed_demo=False)
        assert reopened.get_admin_settings(building) == payload.model_dump()


def test_organization_adopts_only_explicit_provisioned_root(admin):
    scope = Scope(id="new-org", kind=ScopeKind.ORGANIZATION, organization_id="new-org")
    admin.auth.save_scope(scope)
    with pytest.raises(DomainError):
        admin.create_organization(OrganizationInput(scope_id=scope.id, name="New organization"))
    admin.repo.save_role_assignment(RoleAssignment(id="new-org-authority", user_id="admin", role=Role.ADMIN,
        scope_id=scope.id, permissions=[P.STRUCTURE_CONFIGURE]))
    result = admin.create_organization(OrganizationInput(scope_id=scope.id, name="New organization"))
    assert not result.demo
    assert admin.repo.get_resource_binding("structure", result.id).scope_id == scope.id


def test_account_suspension_invalidates_current_session(admin):
    from app.services.auth import AuthService
    from app.auth_config import AuthSettings
    account = create(admin)
    auth = AuthService(admin.repo, AuthSettings("http://test"))
    cookie, _ = auth.issue(NOW, account["id"])
    assert auth.user(cookie, NOW)
    admin.set_account_state(account["id"], False)
    assert auth.user(cookie, NOW) is None


def test_admin_http_authentication_csrf_and_delegation(admin, api):
    h = headers(admin.repo, "admin")
    payload = {"name": "Synthetic", "username": "http-synthetic", "password": "Synthetic-only-fixture-password", "scope_id": "demo-org:reference:apartment-101"}
    assert api("GET", "/admin/accounts")[0] == 401
    assert api("POST", "/admin/accounts", payload, headers=h[:1])[0] == 403
    code, user = api("POST", "/admin/accounts", payload, headers=h)
    assert code == 200 and "password" not in str(user)
    role = {"id": "resident-grant", "user_id": user["id"], "role": "resident", "scope_id": payload["scope_id"], "permissions": ["locations.read"]}
    assert api("PUT", "/admin/assignments/resident-grant", role, headers=h)[0] == 200
    role["permissions"] = ["incidents.manage"]
    assert api("PUT", "/admin/assignments/resident-grant", role, headers=h)[0] in {403, 422}
    role.update(id="guess", user_id="business", permissions=["locations.read"])
    assert api("PUT", "/admin/assignments/guess", role, headers=h)[0] == 403


def test_migration_7_upgrade_from_6_empty_idempotence_foreign_keys(tmp_path):
    path = tmp_path / "upgrade-6.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
        for version, statements in MIGRATIONS[:6]:
            for statement in statements:
                connection.execute(statement)
            connection.execute("INSERT INTO schema_migrations VALUES (?, 'test')", (version,))
    repo = SQLiteRepository(f"sqlite:///{path}")
    repo.initialize(seed_demo=False)
    repo.initialize(seed_demo=False)
    assert repo.list_configuration_audit() == [] and repo.list_structure_nodes() == []
    with repo.database.transaction() as connection:
        assert [r[0] for r in connection.execute("SELECT version FROM schema_migrations ORDER BY version")] == [v for v, _ in MIGRATIONS]
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO product_admin_settings VALUES ('missing', 'missing', '{}')")


def test_setup_completion_validates_readiness(admin):
    building = "demo-org:reference:building"
    with pytest.raises(DomainError):
        admin.setup(building, SetupInput(step="Review", completed=True))
    assert admin.setup(building, SetupInput(step="Review", completed=True, policy_reviewed=True))["completed"]


def test_owner_appointment_retains_existing_phase_a_boundary(admin, api):
    repo = admin.repo
    repo.save_role_assignment(repo.get_role_assignment("admin-grant").model_copy(update={"active": False}))
    repo.save_role_assignment(RoleAssignment(id="owner-grant", user_id="admin", role=Role.OWNER,
        scope_id="demo-org", permissions=[P.OWNERSHIP_MANAGE]))
    assert admin.accounts() == []
    options = admin.grant_options("demo-org")
    assert set(options) == {"admin"} and "camera.view" not in options["admin"]
    payload = {"id": "owner-appointed-admin", "user_id": "resident", "role": "admin", "scope_id": "demo-org", "permissions": ["structure.configure"]}
    assert api("PUT", "/admin/assignments/owner-appointed-admin", payload, headers=headers(repo, "admin"))[0] == 200
    payload.update(id="owner-escalation", role="manager", permissions=["incidents.manage"])
    assert api("PUT", "/admin/assignments/owner-escalation", payload, headers=headers(repo, "admin"))[0] == 403


def test_first_install_provisioning_is_explicit_empty_and_no_operations(tmp_path):
    from app.services.admin_provisioning import provision_first_admin
    repo = SQLiteRepository(f"sqlite:///{tmp_path / 'fresh.db'}")
    repo.initialize(seed_demo=False)
    result = provision_first_admin(repo, "Synthetic First Admin", "synthetic-first",
        "Synthetic-only-fixture-password", NOW)
    user = repo.get_auth_user(result["user_id"])
    auth = AuthorizationService(repo, Principal(user_id=user.id, person_id=user.person_id), NOW)
    assert auth.allowed_scope(P.STRUCTURE_CONFIGURE, result["organization_id"])
    assert not auth.allowed_scope(P.CAMERA_VIEW, result["organization_id"])
    assert not auth.allowed_scope(P.INCIDENTS_READ, result["organization_id"])
    assert repo.list_structure_nodes() == [] and repo.list_zones() == repo.list_permissions() == []
    with pytest.raises(DomainError):
        provision_first_admin(repo, "Another Admin", "another-admin", "Synthetic-only-fixture-password", NOW)


def test_ring_configuration_does_not_expose_other_owner_or_tokens(admin):
    from app.models.ring import RingAccount
    from datetime import timedelta
    from app.models.authorization import ResourceBinding
    repo = admin.repo
    repo.save_resource_binding(ResourceBinding(resource_type="ring_link", resource_id="installation", scope_id="demo-org"))
    grant = repo.get_role_assignment("admin-grant")
    repo.save_role_assignment(grant.model_copy(update={"permissions": grant.permissions + [P.RING_MANAGE]}))
    for identifier, owner in (("own-ring", "admin"), ("other-ring", "business")):
        user = repo.get_auth_user(owner)
        repo.save_ring_account(RingAccount(id=identifier, environment="test", account_id=identifier,
            encrypted_tokens="synthetic-encrypted-placeholder", received_at=NOW, expires_at=NOW + timedelta(hours=1),
            owner_id=user.person_id, owner_user_id=user.id, status="completed", link_verified=True))
    assert admin.ring_configuration()["accounts"] == []
    repo.save_resource_binding(ResourceBinding(resource_type="ring_account", resource_id="own-ring", scope_id="demo-org"))
    result = admin.ring_configuration()
    assert len(result["accounts"]) == 1 and result["state"] == "connected"
    assert "encrypted" not in str(result) and "other-ring" not in str(result)


def test_ring_prepare_explicit_binding_no_legacy_ownership_inference(admin):
    repo = admin.repo
    grant = repo.get_role_assignment("admin-grant")
    repo.save_role_assignment(grant.model_copy(update={"permissions": grant.permissions + [P.RING_MANAGE]}))
    building = "demo-org:reference:building"
    before = repo.list_ring_accounts()
    admin.prepare_ring(building)
    admin.prepare_ring(building)
    assert repo.get_resource_binding("ring_link", "installation").scope_id == building
    assert repo.list_ring_accounts() == before
    assert not admin.ring_configuration()["discovery_verified"]


def test_ring_prepare_requires_configuration_and_ring_permission(admin):
    with pytest.raises(DomainError):
        admin.prepare_ring("demo-org:reference:building")
    assert admin.repo.get_resource_binding("ring_link", "installation") is None
