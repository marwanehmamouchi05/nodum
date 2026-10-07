"""Phase B contracts exercised against both isolated repository backends."""
from datetime import timedelta
import sqlite3
import pytest
from app.models.auth import NodumUser
from app.models.authorization import Principal, Role, Permission as P, ResourceBinding, RoleAssignment
from app.models.structure import NodeKind as K, StructureNode, Affiliation
from app.repository import InMemoryRepository
from app.sqlite_repository import SQLiteRepository
from app.database import MIGRATIONS
from app.services.authorization import AuthorizationService
from app.services.structure import StructureService
from app.services.reference_building import load_reference_building
from app.services.errors import DomainError
from conftest import NOW


@pytest.fixture
def structure(repo, monkeypatch):
    monkeypatch.setenv("NODUM_AUTHORIZATION_MODE", "scoped")
    monkeypatch.setenv("AUTH_PUBLIC_ORIGIN", "http://test")
    monkeypatch.setenv("APP_ENV", "development")
    for identifier, person in (("admin", "manager-1"), ("resident", "resident-1"), ("business", "contractor-1")):
        repo.save_auth_user(NodumUser(id=identifier, username=identifier, person_id=person,
            password_hash="test-fixture-no-login-password", created_at=NOW))
    auth = AuthorizationService(repo, Principal(user_id="admin", person_id="manager-1"), NOW)
    service = StructureService(auth)
    service.bootstrap_organization("demo-org", "Synthetic demo organization", demo=True)
    repo.save_role_assignment(RoleAssignment(id="admin-grant", user_id="admin", role=Role.ADMIN,
        scope_id="demo-org", permissions=[P.STRUCTURE_CONFIGURE, P.HARDWARE_CONFIGURE,
            P.LOCATIONS_READ, P.HARDWARE_READ, P.AFFILIATIONS_MANAGE, P.ACCOUNTS_READ]))
    load_reference_building(service, "demo-org")
    return service


def user_service(structure, user, scope, role, permissions):
    repo = structure.repo
    repo.save_role_assignment(RoleAssignment(id=user + "-grant", user_id=user, role=role,
        scope_id=scope, permissions=permissions))
    return StructureService(AuthorizationService(repo,
        Principal(user_id=user, person_id=repo.get_auth_user(user).person_id), NOW))


def test_reference_complete_idempotent_and_legacy_untouched(structure):
    repo = structure.repo
    before = (repo.list_zones(), repo.list_businesses(), repo.list_people(), repo.list_permissions())
    load_reference_building(structure, "demo-org")
    nodes = repo.list_structure_nodes()
    assert len([n for n in nodes if n.kind == K.FLOOR]) == 6
    assert len([n for n in nodes if n.kind == K.UNIT]) == 10
    assert len([n for n in nodes if n.kind == K.BUSINESS]) == 2
    assert len([n for n in nodes if n.kind == K.DEVICE]) == 4
    assert all(n.demo for n in nodes)
    assert before == (repo.list_zones(), repo.list_businesses(), repo.list_people(), repo.list_permissions())
    assert repo.get_resource_binding("business", "atlas-dental") is None


@pytest.mark.parametrize("user,role,own,other", [
    ("business", Role.BUSINESS_ADMIN, "business-x", "business-y"),
    ("resident", Role.RESIDENT, "apartment-101", "apartment-102")])
def test_private_scope_list_detail_and_guessed_ids(structure, user, role, own, other):
    prefix = "demo-org:reference:"
    service = user_service(structure, user, prefix + own, role, [P.LOCATIONS_READ, P.HARDWARE_READ])
    assert service.get(prefix + own).name
    visible = {n.id for n in service.catalog()["nodes"]}
    assert prefix + own in visible and prefix + other not in visible
    for identifier in (prefix + other, "unknown", "demo-org", prefix + "floor2"):
        with pytest.raises(DomainError) as error:
            service.get(identifier)
        assert error.value.status_code == 403
    with pytest.raises(DomainError):
        service.save(structure.repo.get_structure_node(prefix + other))
    assert not service.auth.allowed_scope(P.ACCESS_CHECK, prefix + own)


def test_business_floor_authority_does_not_inherit_private_business(structure):
    service = user_service(structure, "resident", "demo-org:reference:floor2", Role.RESIDENT, [P.LOCATIONS_READ])
    assert not service.auth.allowed(P.LOCATIONS_READ, "structure", "demo-org:reference:business-x")


@pytest.mark.parametrize("suffix,expected", [
    ("lobby-camera", "Ground Floor"), ("entrance-lock", "Main entrance zone"),
    ("business-x-camera", "Business X"), ("machine-room-sensor", "Elevator machine room")])
def test_device_mapping_context(structure, suffix, expected):
    context = structure.device_context("demo-org:reference:" + suffix)
    assert expected in [n["name"] for n in context["path"]]
    assert context["connection_path"] == "simulation" and context["demo"]
    assert context["scope_id"] == context["location_id"]
    assert len(structure.catalog()["device_mappings"]) == 4


@pytest.mark.parametrize("field,value", [("organization_id", "other"), ("building_id", "other"),
    ("scope_id", "other"), ("parent_id", "unknown"), ("connection_path", "cloud")])
def test_ownership_and_remapping_rejected_without_changes(structure, field, value):
    node = structure.repo.get_structure_node("demo-org:reference:lobby-camera")
    modified = StructureNode.model_validate({**node.model_dump(), field: value})
    with pytest.raises(DomainError):
        structure.save(modified)
    assert structure.repo.get_structure_node(node.id) == node


def test_affiliation_no_automatic_authority_or_person_rebinding(structure):
    repo = structure.repo
    repo.save_resource_binding(ResourceBinding(resource_type="person", resource_id="resident-1", scope_id="demo-org"))
    record = Affiliation(id="stay", user_id="resident", role=Role.RESIDENT,
        target_id="demo-org:reference:apartment-101", starts_at=NOW, ends_at=NOW + timedelta(days=30))
    structure.save_affiliation(record)
    assert structure.affiliations() == [record]
    assert repo.get_resource_binding("affiliation", record.id).scope_id == record.target_id
    assert repo.get_resource_binding("person", "resident-1").scope_id == "demo-org"
    assert not AuthorizationService(repo, Principal(user_id="resident", person_id="resident-1"), NOW).allowed_scope(P.LOCATIONS_READ, record.target_id)


def test_business_affiliation_overlap_and_date_bounds(structure):
    repo = structure.repo
    repo.save_resource_binding(ResourceBinding(resource_type="person", resource_id="contractor-1", scope_id="demo-org"))
    first = Affiliation(id="x-staff", user_id="business", role=Role.BUSINESS_STAFF,
        target_id="demo-org:reference:business-x", starts_at=NOW, ends_at=NOW + timedelta(days=2))
    structure.save_affiliation(first)
    second = first.model_copy(update={"id": "y-admin", "role": Role.BUSINESS_ADMIN, "target_id": "demo-org:reference:business-y"})
    with pytest.raises(DomainError):
        structure.save_affiliation(second)
    structure.save_affiliation(second.model_copy(update={"starts_at": first.ends_at, "ends_at": NOW + timedelta(days=4)}))
    assert len(repo.list_affiliations()) == 2


def test_affiliation_unbound_account_and_wrong_target_denied(structure):
    with pytest.raises(DomainError):
        structure.save_affiliation(Affiliation(id="bad", user_id="resident", role=Role.RESIDENT,
            target_id="demo-org:reference:apartment-101"))
    structure.repo.save_resource_binding(ResourceBinding(resource_type="person", resource_id="resident-1", scope_id="demo-org"))
    with pytest.raises(DomainError):
        structure.save_affiliation(Affiliation(id="bad", user_id="resident", role=Role.RESIDENT,
            target_id="demo-org:reference:business-x"))


def test_revocation_and_unbound_default_deny(structure):
    repo = structure.repo
    grant = repo.get_role_assignment("admin-grant")
    repo.save_role_assignment(grant.model_copy(update={"active": False}))
    assert structure.catalog()["nodes"] == []
    with pytest.raises(DomainError):
        load_reference_building(structure, "demo-org")


def test_seed_collision_preflight_has_no_partial_writes(structure):
    repo = structure.repo
    node = repo.get_structure_node("demo-org:reference:business-y")
    repo.save_structure_node(node.model_copy(update={"name": "Customized"}))
    before = repo.list_structure_nodes()
    with pytest.raises(DomainError):
        load_reference_building(structure, "demo-org")
    assert repo.list_structure_nodes() == before


def test_real_organization_rejects_demo(structure):
    node = structure.bootstrap_organization("real-org", "Empty installation")
    structure.repo.save_role_assignment(RoleAssignment(id="real-admin", user_id="admin", role=Role.ADMIN,
        scope_id=node.id, permissions=[P.STRUCTURE_CONFIGURE, P.HARDWARE_CONFIGURE]))
    with pytest.raises(DomainError):
        load_reference_building(structure, node.id)


def test_empty_installation_and_restart(tmp_path):
    repo = SQLiteRepository(f"sqlite:///{tmp_path / 'empty.db'}")
    repo.initialize(seed_demo=False)
    repo.initialize(seed_demo=False)
    assert repo.list_structure_nodes() == repo.list_affiliations() == repo.list_zones() == repo.list_people() == []
    assert InMemoryRepository().list_structure_nodes() == []


def test_upgrade_v5_no_legacy_ownership_and_foreign_keys(tmp_path):
    path = tmp_path / "upgrade.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
        for version, statements in MIGRATIONS[:5]:
            for statement in statements:
                connection.execute(statement)
            connection.execute("INSERT INTO schema_migrations VALUES (?, 'test')", (version,))
        connection.execute("INSERT INTO zones VALUES ('legacy', ?)", ('{"id":"legacy","name":"Legacy","zone_type":"common"}',))
    repo = SQLiteRepository(f"sqlite:///{path}")
    repo.initialize(seed_demo=False)
    repo.initialize(seed_demo=False)
    with repo.database.transaction() as connection:
        assert [r[0] for r in connection.execute("SELECT version FROM schema_migrations ORDER BY version")] == [v for v, _ in MIGRATIONS]
        assert connection.execute("SELECT count(*) FROM zones").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM application_resource_bindings").fetchone()[0] == 0
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO product_affiliations VALUES ('bad', 'missing', 'missing', '{}')")


def test_http_session_csrf_list_detail_and_mutation(structure, api):
    from test_authorization import headers
    repo = structure.repo
    assert api("GET", "/structure/catalog")[0] == 401
    admin_headers = headers(repo, "admin")
    assert api("GET", "/structure/catalog", headers=admin_headers)[0] == 200
    node = repo.get_structure_node("demo-org:reference:apartment-101")
    assert api("PUT", "/structure/nodes/" + node.id, node.model_dump(mode="json"), headers=admin_headers)[0] == 200
    assert api("PUT", "/structure/nodes/" + node.id, node.model_dump(mode="json"), headers=admin_headers[:1])[0] == 403
    user_service(structure, "resident", node.id, Role.RESIDENT, [P.LOCATIONS_READ])
    resident_headers = headers(repo, "resident")
    assert api("GET", "/structure/nodes/" + node.id, headers=resident_headers)[0] == 200
    assert api("GET", "/structure/nodes/demo-org:reference:apartment-102", headers=resident_headers)[0] == 403
    assert api("PUT", "/structure/nodes/" + node.id, node.model_dump(mode="json"), headers=resident_headers)[0] == 403


@pytest.mark.parametrize("path", ["cloud", "edge", "simulation"])
def test_connection_paths_are_metadata_without_runtime_capabilities(structure, path):
    building = "demo-org:reference:building"
    integration = StructureNode(id="adapter-" + path, name="Configured adapter", kind=K.INTEGRATION,
        organization_id="demo-org", building_id=building, parent_id=building,
        scope_id=building, demo=True, connection_path=path)
    structure.save(integration)
    location = "demo-org:reference:business-y"
    device = StructureNode(id="device-" + path, name="Configured device", kind=K.DEVICE,
        organization_id="demo-org", building_id=building, parent_id=location, scope_id=location,
        demo=True, connection_path=path, integration_id=integration.id, device_type="camera")
    structure.save(device)
    assert structure.device_context(device.id)["connection_path"] == path
    assert structure.get(device.id).capabilities == []


def test_configuration_ceiling_does_not_grant_camera_content(structure):
    assert not structure.auth.allowed(P.CAMERA_VIEW, "structure", "demo-org:reference:lobby-camera")
    assert not structure.auth.allowed(P.ACTIVITY_READ, "structure", "demo-org:reference:lobby-camera")


def test_legacy_mode_structure_api_not_available(structure, api, monkeypatch):
    from test_authorization import headers
    monkeypatch.setenv("NODUM_AUTHORIZATION_MODE", "legacy_demo")
    assert api("GET", "/structure/catalog", headers=headers(structure.repo, "admin"))[0] == 404


def test_sqlite_seed_foreign_keys_and_persistence(structure):
    repo = structure.repo
    if isinstance(repo, SQLiteRepository):
        with repo.database.transaction() as connection:
            assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        restarted = SQLiteRepository(f"sqlite:///{repo.database.path}")
        restarted.initialize(seed_demo=False)
        assert restarted.list_structure_nodes() == repo.list_structure_nodes()


def test_floor_delegate_cannot_create_independent_business_scope(structure):
    service = user_service(structure, "resident", "demo-org:reference:floor2", Role.MANAGER,
        [P.STRUCTURE_CONFIGURE, P.LOCATIONS_READ])
    node = StructureNode(id="new-business", name="Business Z", kind=K.BUSINESS,
        organization_id="demo-org", building_id="demo-org:reference:building",
        parent_id="demo-org:reference:floor2-location-0", scope_id="new-business", demo=True)
    with pytest.raises(DomainError):
        service.save(node)
    assert structure.repo.get_scope(node.id) is None
    assert structure.repo.get_structure_node(node.id) is None
