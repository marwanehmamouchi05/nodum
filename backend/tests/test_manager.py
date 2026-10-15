"""Phase D real session, default-deny, operational lifecycle and scoped AI tests."""
from datetime import timedelta
import pytest
from app.models.authorization import Permission as P, Role, ResourceBinding
from app.models.manager import AnnouncementInput, MaintenanceInput, MaintenanceUpdate, VisitorInput
from app.services.manager import ManagerService
from app.services.errors import DomainError
from app.services.agent_actions import PendingActionStore
from app.services.agent_tools import AgentTools
from app.services.authorization import ROLE_CEILINGS
from test_structure import structure, user_service
from test_authorization import headers
from conftest import NOW

ROOT = "demo-org:reference:"


@pytest.fixture
def manager(structure):
    service = user_service(structure, "resident", ROOT + "building", Role.MANAGER,
        [p for p in ROLE_CEILINGS[Role.MANAGER] if p not in {P.STRUCTURE_CONFIGURE, P.HARDWARE_CONFIGURE, P.ACCOUNTS_MANAGE}])
    return ManagerService(service.auth)


def report(manager, target="apartment-101"):
    return manager.create("maintenance", MaintenanceInput(location_id=ROOT + target,
        title="Synthetic water leak", description="Fixture issue", priority="high"))


def announce(manager, target="building", **kwargs):
    return manager.create("announcement", AnnouncementInput(location_id=ROOT + target,
        title="Elevator maintenance", message="Synthetic notice", **kwargs))


def test_manager_is_operational_not_admin(manager):
    for permission in (P.STRUCTURE_CONFIGURE, P.HARDWARE_CONFIGURE, P.AUTHORIZATION_MANAGE, P.OWNERSHIP_MANAGE):
        assert not manager.auth.allowed(permission, "structure", ROOT + "building")
    snapshot = manager.snapshot()
    assert snapshot["status"] == "Attention needed"
    assert snapshot["unverified_devices"] == 4
    assert all(d["status"] == "unverified" for d in snapshot["devices"])
    assert not snapshot["visitors"] and not snapshot["people"]


@pytest.mark.parametrize("kind", ["announcement", "maintenance"])
@pytest.mark.parametrize("target", ["missing", "demo-org", ROOT + "simulation", "lobby"])
def test_default_deny_wrong_or_unbound_target(manager, kind, target):
    payload = AnnouncementInput(location_id=target, title="x", message="x") if kind == "announcement" else MaintenanceInput(location_id=target, title="x", description="x")
    with pytest.raises(DomainError):
        manager.create(kind, payload)
    assert not manager.repo.list_operational_records(kind)


@pytest.mark.parametrize("role,own,other", [(Role.RESIDENT, "apartment-101", "apartment-102"), (Role.BUSINESS_ADMIN, "business-x", "business-y")])
def test_resident_business_isolation(manager, structure, role, own, other):
    own_request = report(manager, own)
    other_request = report(manager, other)
    announce(manager, own)
    announce(manager, other)
    user = user_service(structure, "business", ROOT + own, role,
        [P.LOCATIONS_READ, P.MAINTENANCE_READ, P.MAINTENANCE_CREATE, P.ANNOUNCEMENTS_READ])
    service = ManagerService(user.auth)
    snapshot = service.snapshot()
    assert [r["id"] for r in snapshot["maintenance"]] == [own_request["id"]]
    assert len(snapshot["announcements"]) == 1
    assert snapshot["coverage"]["maintenance"] is False
    with pytest.raises(DomainError):
        report(service, other)
    with pytest.raises(DomainError):
        service.update_maintenance(other_request["id"], MaintenanceUpdate(status="resolved"))
    with pytest.raises(DomainError):
        announce(service, own)


def test_maintenance_lifecycle_and_identity(manager):
    r = report(manager)
    assert r["reporter_id"] == manager.auth.principal.person_id
    assert manager.repo.get_resource_binding("maintenance", r["id"]).scope_id == ROOT + "apartment-101"
    for status in ("in_progress", "resolved", "closed", "new"):
        result = manager.update_maintenance(r["id"], MaintenanceUpdate(status=status, note="Synthetic update"))
        assert result["status"] == status
        assert bool(result["resolved_at"]) == (status in {"resolved", "closed"})
        assert result["history"][-1]["actor_id"] == manager.auth.principal.person_id
    assert len(result["history"]) == 4
    assert len(manager.snapshot()["activity"]) == 5


def test_maintenance_assignment_requires_active_visible_person(manager):
    r = report(manager)
    for identifier in ("missing", "plumber-1", manager.auth.principal.person_id):
        with pytest.raises(DomainError):
            manager.update_maintenance(r["id"], MaintenanceUpdate(status="assigned", assignee_id=identifier))
    assert manager.repo.list_operational_records("maintenance")[0]["status"] == "new"


@pytest.mark.parametrize("audience", ["all", "residential", "business"])
def test_announcement_schedule_expiry_and_identity(manager, audience):
    r = announce(manager, "floor2", audience=audience, publish_at=NOW + timedelta(hours=1), expires_at=NOW + timedelta(days=1))
    assert r["creator_id"] == manager.auth.principal.person_id
    assert r["scope_id"] == ROOT + "floor2"
    assert r["audience"] == audience
    assert manager.records("announcement", P.ANNOUNCEMENTS_READ) == [r]


def test_bad_announcement_dates_make_no_write(manager):
    with pytest.raises(DomainError):
        announce(manager, expires_at=NOW)
    assert not manager.repo.list_operational_records("announcement")


def test_revoked_write_and_suspended_account(manager):
    r = report(manager)
    grant = manager.repo.get_role_assignment("resident-grant")
    manager.repo.save_role_assignment(grant.model_copy(update={"permissions": [P.MAINTENANCE_READ]}))
    with pytest.raises(DomainError):
        manager.update_maintenance(r["id"], MaintenanceUpdate(status="resolved"))
    with pytest.raises(DomainError):
        announce(manager)
    user = manager.repo.get_auth_user("resident")
    manager.repo.save_auth_user(user.model_copy(update={"active": False}))
    assert not manager.snapshot()["maintenance"]


def test_visitor_real_record_window_arrival_no_access(manager):
    before = manager.repo.list_permissions()
    r = manager.invite(VisitorInput(location_id=ROOT + "business-x", name="Synthetic guest",
        starts_at=NOW - timedelta(minutes=10), ends_at=NOW + timedelta(hours=1)))
    assert r["host_id"] == manager.auth.principal.person_id
    assert manager.snapshot()["visitors"][0]["status"] == "expected"
    assert manager.arrive(r["id"])["checked_in_at"] == NOW.isoformat()
    assert manager.snapshot()["visitors"][0]["status"] == "arrived"
    assert before == manager.repo.list_permissions()
    with pytest.raises(DomainError):
        manager.arrive(r["id"])


def test_visitor_arrival_outside_window_and_cross_scope(manager, structure):
    r = manager.invite(VisitorInput(location_id=ROOT + "business-y", name="Future visitor",
        starts_at=NOW + timedelta(hours=1), ends_at=NOW + timedelta(hours=2)))
    with pytest.raises(DomainError):
        manager.arrive(r["id"])
    other = ManagerService(user_service(structure, "business", ROOT + "business-x", Role.MANAGER,
        [P.VISITORS_READ, P.VISITORS_CHECK_IN]).auth)
    assert not other.snapshot()["visitors"]
    with pytest.raises(DomainError):
        other.arrive(r["id"])


def test_real_http_session_csrf_and_client_authority_rejected(manager, api):
    body = {"location_id": ROOT + "apartment-101", "title": "Issue", "description": "Synthetic issue"}
    assert api("POST", "/manager/maintenance", body)[0] == 401
    auth_headers = headers(manager.repo, "resident")
    assert api("POST", "/manager/maintenance", body, headers=auth_headers[:1])[0] == 403
    status, r = api("POST", "/manager/maintenance", body, headers=auth_headers)
    assert status == 200 and r["reporter_id"] == manager.auth.principal.person_id
    for field in ("reporter_id", "creator_id", "scope_id", "building_id"):
        assert api("POST", "/manager/maintenance", body | {field: "forged"}, headers=auth_headers)[0] == 422
    assert api("GET", "/manager/snapshot", headers=auth_headers)[0] == 200


def test_scoped_ai_summary_requires_ai_on_each_resource(manager):
    report(manager)
    tools = AgentTools(manager.repo, PendingActionStore(manager.repo), manager.auth.principal.person_id, lambda: NOW, manager.auth)
    result = tools.run("manager_operations", {})
    assert result.status == "success" and result.data["counts"]["maintenance"] == 1
    grant = manager.repo.get_role_assignment("resident-grant")
    manager.repo.save_role_assignment(grant.model_copy(update={"permissions": [p for p in grant.permissions if p != P.AI_USE]}))
    result = tools.run("manager_operations", {})
    assert result.data["counts"]["maintenance"] == 0 and not result.data["maintenance"]
    assert result.data["status"] == "Status unavailable"


def test_unbound_operation_records_hidden(manager):
    manager.repo.save_operational_record("maintenance", {"id": "unbound", "scope_id": ROOT + "building", "secret": "hidden"})
    assert not manager.records("maintenance", P.MAINTENANCE_READ)


def test_partial_status_never_claims_building_normal(manager, structure):
    user = user_service(structure, "business", ROOT + "business-x", Role.MANAGER, [P.MAINTENANCE_READ])
    snapshot = ManagerService(user.auth).snapshot()
    assert snapshot["status"] == "Status unavailable"
    assert not any(snapshot["coverage"].values())


@pytest.mark.parametrize("scenario", ["visitor_arrives", "package_delivery", "after_hours_person", "emergency_access", "contact_sensor_sequence", "device_lifecycle"])
def test_ring_scenarios_manager_projection_no_identity_or_unlock(manager, api, scenario):
    from unittest.mock import Mock
    from app.api.ring import get_ring_service
    from app.main import app
    from app.services.ring import RingService
    from app.integrations.ring.client import RingClient
    from test_ring_simulation import _make_settings
    remote = Mock(spec=RingClient)
    app.dependency_overrides[get_ring_service] = lambda: RingService(manager.repo, _make_settings(), remote)
    manager.repo.save_resource_binding(ResourceBinding(resource_type="simulation", resource_id="ring", scope_id=ROOT + "building"))
    before = manager.repo.list_permissions()
    status, delivered = api("POST", "/ring/simulation/scenarios/" + scenario, {}, headers=headers(manager.repo, "resident"))
    assert status == 200, delivered
    snapshot = manager.snapshot()
    assert len(snapshot["ring"]) == len(delivered["events"])
    assert all(e["simulated"] for e in snapshot["ring"])
    assert all(e["location_id"] is None for e in snapshot["ring"])
    assert len(snapshot["activity"]) == len(delivered["events"])
    assert not snapshot["visitors"]
    assert before == manager.repo.list_permissions()
    assert not manager.repo.list_actuator_events()
    remote.discover.assert_not_called()
    assert all("raw_payload" not in e and "account_id" not in e for e in snapshot["ring"])


def test_migration_8_upgrade_restart_and_scope_fk(tmp_path):
    import sqlite3
    from app.database import SQLiteDatabase, MIGRATIONS
    from app.sqlite_repository import SQLiteRepository
    path = tmp_path / "phase-d.db"
    db = SQLiteDatabase("sqlite:///" + str(path))
    db.path.parent.mkdir(parents=True, exist_ok=True)
    with db.transaction() as connection:
        connection.execute("CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
        for version, statements in MIGRATIONS[:7]:
            for statement in statements:
                connection.execute(statement)
            connection.execute("INSERT INTO schema_migrations VALUES (?, 'fixture')", (version,))
    repo = SQLiteRepository("sqlite:///" + str(path))
    repo.initialize(seed_demo=False)
    repo.initialize(seed_demo=False)
    with repo.database.transaction() as connection:
        assert [r[0] for r in connection.execute("SELECT version FROM schema_migrations ORDER BY version")] == list(range(1, 9))
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO product_operations VALUES ('maintenance','x','missing','{}')")


def test_core_snapshot_survives_invalid_ring_config(manager, monkeypatch):
    monkeypatch.setenv("RING_MODE", "invalid")
    assert manager.snapshot()["status"] == "Attention needed"
    assert not manager.snapshot()["can_simulate"]
