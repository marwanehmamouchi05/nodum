import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
import os
import sqlite3
import subprocess
import sys
from threading import Barrier
from unittest.mock import MagicMock

import pytest

from app.database import BACKEND_DIRECTORY, SQLiteDatabase, database_path
from app.main import app
from app.models.access import AccessCheckInput, GuestInviteInput
from app.models.business import AppointmentCreateInput, VisitorCheckInInput
from app.models.emergency import (
    EmergencyAssignInput, EmergencyCreateInput, EmergencyResolveInput, EmergencyStatus,
)
from app.services.access import check_access
from app.services.agent_actions import PendingActionStore
from app.services.agent_tools import AgentTools, confirm_action
from app.services.appointments import create_appointment, check_in_visitor
from app.services.emergencies import create_emergency, assign_responders, resolve_emergency
from app.services.errors import DomainError
from app.services.guests import create_invitation
from app.sqlite_repository import SQLiteRepository


NOW = datetime(2026, 9, 29, 12, tzinfo=timezone.utc)


@pytest.fixture
def database_url(tmp_path):
    return f"sqlite:///{tmp_path / 'nodum.db'}"


def reopen(url):
    repository = SQLiteRepository(url)
    repository.initialize()
    return repository


def invite(repo, **changes):
    payload = dict(resident_id="resident-1", guest_id="persisted-guest", guest_name="Guest",
                   allowed_zone_ids=["floor-5"], valid_for_hours=3) | changes
    return create_invitation(repo, GuestInviteInput(**payload), NOW)


def schedule(repo, **changes):
    payload = dict(id="appointment", visitor_id="visitor", visitor_name="Visitor",
                   business_id="atlas-dental", destination_zone_id="office-106",
                   appointment_time=NOW + timedelta(minutes=10)) | changes
    return create_appointment(repo, AppointmentCreateInput(**payload), NOW)


def check_in(repo):
    return check_in_visitor(repo, "appointment",
                            VisitorCheckInInput(visitor_id="visitor", visitor_name="Visitor"), NOW)


def incident(repo, **changes):
    payload = dict(emergency_id="incident", emergency_type="water_leak", severity="high",
                   affected_zone_ids=["floor-5"], description="Leak", created_by="manager-1") | changes
    return create_emergency(repo, EmergencyCreateInput(**payload), NOW)


def resolve(repo):
    return resolve_emergency(repo, "incident",
                             EmergencyResolveInput(resolved_by="manager-1"), NOW + timedelta(minutes=1))


def access(repo, person_id="persisted-guest", zone_id="floor-5", at=NOW):
    return check_access(repo, AccessCheckInput(person_id=person_id, zone_id=zone_id, purpose="Test"), at)


def test_guest_permissions_and_people_survive_recreation(database_url):
    original = reopen(database_url)
    result = invite(original)
    loaded = reopen(database_url)
    assert loaded.get_person("persisted-guest").name == "Guest"
    assert loaded.list_permissions() == [result["permission"]]
    assert loaded.list_permissions()[0].valid_from.tzinfo == timezone.utc
    assert access(loaded).allowed
    assert not access(loaded, zone_id="machine-room").allowed
    assert not access(loaded, at=NOW + timedelta(hours=3)).allowed


def test_appointments_and_check_in_survive_separate_restarts(database_url):
    repo = reopen(database_url)
    scheduled = schedule(repo)
    repo = reopen(database_url)
    assert repo.get_appointment("appointment") == scheduled
    assert repo.list_permissions() == [] and repo.get_person("visitor") is None
    checked_in = check_in(repo)
    repo = reopen(database_url)
    assert repo.get_appointment("appointment") == checked_in.appointment
    assert repo.list_permissions() == [checked_in.permission]
    assert access(repo, person_id="visitor", zone_id="office-106").allowed
    assert not access(repo, person_id="visitor", zone_id="floor-5").allowed
    assert not access(repo, person_id="visitor", zone_id="office-106", at=NOW + timedelta(hours=2)).allowed


def test_emergency_active_resolved_and_history_persist(database_url):
    repo = reopen(database_url)
    invite(repo)
    initial = incident(repo)
    repo = reopen(database_url)
    assert repo.get_emergency("incident") == initial
    assert not access(repo).allowed
    assigned = assign_responders(repo, "incident",
        EmergencyAssignInput(assigned_by="manager-1", responder_ids=["responder-1"]), NOW)
    repo = reopen(database_url)
    assert repo.get_emergency("incident").history == assigned.history
    resolved = resolve(repo)
    repo = reopen(database_url)
    assert repo.get_emergency("incident") == resolved
    assert resolved.status == EmergencyStatus.RESOLVED
    assert resolved.resolved_at.tzinfo == timezone.utc
    assert access(repo).allowed
    with closing(sqlite3.connect(repo.database.path)) as connection:
        assert connection.execute("SELECT count(*) FROM emergency_events").fetchone()[0] == 3
        assert connection.execute("SELECT json_extract(data, '$.history') FROM emergencies").fetchone()[0] is None


def test_work_orders_zones_and_businesses_persist(database_url):
    repo = reopen(database_url)
    expected = (repo.list_people(), repo.list_zones(), repo.list_work_orders(), repo.list_businesses())
    repo = reopen(database_url)
    assert (repo.list_people(), repo.list_zones(), repo.list_work_orders(), repo.list_businesses()) == expected
    assert access(repo, person_id="contractor-1", zone_id="machine-room").allowed
    assert not access(repo, person_id="contractor-1", zone_id="floor-5").allowed


def test_seed_idempotent_and_does_not_reset_changed_records(database_url):
    repo = reopen(database_url)
    invite(repo)
    schedule(repo)
    incident(repo)
    with closing(sqlite3.connect(repo.database.path)) as connection:
        connection.execute("UPDATE work_orders SET data=json_set(data, '$.active', json('false')) WHERE id='wo-001'")
        connection.execute("UPDATE people SET data=json_set(data, '$.name', 'Renamed resident') WHERE id='resident-1'")
        connection.commit()
    for _ in range(3):
        repo = reopen(database_url)
    assert len(repo.list_people()) == 7
    assert len(repo.list_zones()) == 5
    assert len(repo.list_work_orders()) == 2
    assert len(repo.list_businesses()) == 1
    assert len(repo.list_permissions()) == len(repo.list_appointments()) == len(repo.list_emergencies()) == 1
    assert repo.get_person("resident-1").name == "Renamed resident"
    assert not access(repo, person_id="contractor-1", zone_id="machine-room").allowed
    assert not access(repo).allowed


@pytest.mark.parametrize("operation", ["invite", "schedule", "incident", "check_in", "resolve"])
def test_duplicate_operations_rejected_after_restart(database_url, operation):
    repo = reopen(database_url)
    operations = {"invite": invite, "schedule": schedule, "incident": incident,
                  "check_in": check_in, "resolve": resolve}
    if operation == "check_in":
        schedule(repo)
    if operation == "resolve":
        incident(repo)
    operations[operation](repo)
    repo = reopen(database_url)
    with pytest.raises(DomainError) as exc:
        operations[operation](repo)
    assert exc.value.status_code == 409


def test_pending_action_survives_restart_and_cannot_replay(database_url):
    repo = reopen(database_url)
    registry = AgentTools(repo, PendingActionStore(repo), "resident-1", lambda: NOW)
    proposal = registry.run("invite_guest", dict(
        resident_id="resident-1", guest_id="agent-guest", guest_name="Agent Guest",
        allowed_zone_ids=["floor-5"]))
    repo = reopen(database_url)
    store = PendingActionStore(repo)
    assert repo.get_pending_action(proposal.data["id"]).arguments == proposal.data["arguments"]
    confirmed = confirm_action(repo, store, proposal.data["id"], "resident-1", NOW)
    assert confirmed.status == "success"
    repo = reopen(database_url)
    assert access(repo, person_id="agent-guest").allowed
    with pytest.raises(DomainError) as exc:
        confirm_action(repo, PendingActionStore(repo), proposal.data["id"], "resident-1", NOW)
    assert exc.value.status_code == 404 and len(repo.list_permissions()) == 1


def test_failed_confirmation_consumption_survives_restart(database_url):
    repo = reopen(database_url)
    store = PendingActionStore(repo)
    action = store.propose("resident-1", "invite_guest", dict(
        resident_id="resident-1", guest_id="denied", guest_name="Denied",
        allowed_zone_ids=["machine-room"]), NOW)
    with pytest.raises(DomainError) as exc:
        confirm_action(repo, store, action.id, "resident-1", NOW)
    assert exc.value.status_code == 403
    repo = reopen(database_url)
    assert repo.get_pending_action(action.id) is None
    assert repo.get_person("denied") is None and repo.list_permissions() == []


def test_expired_action_is_consumed_durably(database_url):
    repo = reopen(database_url)
    store = PendingActionStore(repo)
    action = store.propose("resident-1", "invite_guest", {}, NOW)
    repo = reopen(database_url)
    with pytest.raises(DomainError) as exc:
        PendingActionStore(repo).consume(action.id, "resident-1", NOW + timedelta(minutes=5))
    assert exc.value.status_code == 410
    assert reopen(database_url).get_pending_action(action.id) is None


def test_wrong_actor_does_not_consume_action(database_url):
    repo = reopen(database_url)
    action = PendingActionStore(repo).propose("resident-1", "invite_guest", {}, NOW)
    with pytest.raises(DomainError) as exc:
        PendingActionStore(repo).consume(action.id, "manager-1", NOW)
    assert exc.value.status_code == 403
    assert reopen(database_url).get_pending_action(action.id) == action


@pytest.mark.parametrize("operation", ["invite", "schedule", "incident", "resolve", "check_in", "confirm"])
def test_concurrent_repository_instances_serialize_mutations(database_url, operation):
    first = reopen(database_url)
    second = reopen(database_url)
    if operation == "resolve":
        incident(first)
    elif operation == "check_in":
        schedule(first)
    elif operation == "confirm":
        action = PendingActionStore(first).propose("resident-1", "invite_guest", dict(
            resident_id="resident-1", guest_id="concurrent", guest_name="Concurrent",
            allowed_zone_ids=["floor-5"]), NOW)
    barrier = Barrier(2)

    def execute(repository):
        barrier.wait(timeout=5)
        try:
            if operation == "confirm":
                confirm_action(repository, PendingActionStore(repository), action.id, "resident-1", NOW)
            else:
                {"invite": invite, "schedule": schedule, "incident": incident,
                 "resolve": resolve, "check_in": check_in}[operation](repository)
            return 200
        except DomainError as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(execute, [first, second])) == [200, 404 if operation == "confirm" else 409]


def test_transaction_rollback_and_nested_savepoints(database_url):
    repo = reopen(database_url)
    with pytest.raises(RuntimeError):
        with repo.transaction():
            invite(repo)
            schedule(repo)
            raise RuntimeError("rollback outer transaction")
    assert reopen(database_url).get_person("persisted-guest") is None
    assert repo.list_permissions() == repo.list_appointments() == []
    with repo.transaction():
        schedule(repo)
        try:
            with repo.transaction():
                invite(repo)
                raise RuntimeError("rollback nested transaction only")
        except RuntimeError:
            pass
    assert len(repo.list_appointments()) == 1 and repo.list_permissions() == []


@pytest.mark.parametrize("operation", ["invite", "check_in", "incident", "resolve"])
def test_storage_failure_rolls_back_all_related_writes(database_url, operation):
    repo = reopen(database_url)
    if operation == "check_in":
        schedule(repo)
    if operation == "resolve":
        incident(repo)
    target = "emergency_events" if operation in {"incident", "resolve"} else "permissions"
    with closing(sqlite3.connect(repo.database.path)) as connection:
        connection.execute(f"CREATE TRIGGER fail_write BEFORE INSERT ON {target} BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        connection.commit()
    with pytest.raises(sqlite3.IntegrityError):
        {"invite": invite, "check_in": check_in, "incident": incident, "resolve": resolve}[operation](repo)
    repo = reopen(database_url)
    assert repo.list_permissions() == []
    assert repo.get_person("persisted-guest") is None and repo.get_person("visitor") is None
    if operation == "check_in":
        assert repo.get_appointment("appointment").status.value == "scheduled"
    if operation == "incident":
        assert repo.get_emergency("incident") is None
    if operation == "resolve":
        assert repo.get_emergency("incident").status == EmergencyStatus.ACTIVE
        assert len(repo.get_emergency("incident").history) == 1


def test_emergency_history_cannot_be_rewritten(database_url):
    repo = reopen(database_url)
    original = incident(repo)
    changed = original.model_copy(deep=True)
    changed.created_by = "responder-1"
    changed.history[0].actor_id = "responder-1"
    with pytest.raises(ValueError, match="cannot be rewritten"):
        repo.update_emergency(changed)
    assert reopen(database_url).get_emergency("incident") == original


def test_persisted_maintenance_assignment_still_requires_work_order(database_url):
    repo = reopen(database_url)
    incident(repo, affected_zone_ids=["machine-room"], assigned_responder_ids=["contractor-1"])
    repo = reopen(database_url)
    assert access(repo, person_id="contractor-1", zone_id="machine-room").allowed
    with closing(sqlite3.connect(repo.database.path)) as connection:
        connection.execute("UPDATE work_orders SET data=json_set(data, '$.active', json('false')) WHERE id='wo-001'")
        connection.commit()
    assert not access(reopen(database_url), person_id="contractor-1", zone_id="machine-room").allowed


def test_schema_version_and_foreign_keys(database_url):
    repo = reopen(database_url)
    with repo.database.transaction() as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("SELECT version FROM schema_migrations").fetchall()[0][0] == 1
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"people", "zones", "permissions", "work_orders", "businesses", "appointments",
            "emergencies", "emergency_events", "pending_actions", "schema_migrations"} <= tables
    with closing(sqlite3.connect(repo.database.path)) as connection:
        connection.execute("INSERT INTO schema_migrations VALUES (99, 'future')")
        connection.commit()
    with pytest.raises(RuntimeError, match="schema version"):
        reopen(database_url)


def test_migration_failure_is_atomic(tmp_path, monkeypatch):
    from app import database
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setattr(database, "MIGRATIONS", ((1, ("CREATE TABLE example (id INTEGER)", "INVALID SQL")),))
    with pytest.raises(sqlite3.OperationalError):
        SQLiteDatabase(url).initialize()
    with closing(sqlite3.connect(database_path(url))) as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='example'").fetchone() is None


def test_seeding_disabled_stays_empty(database_url):
    repo = SQLiteRepository(database_url)
    repo.initialize(seed_demo=False)
    assert repo.list_people() == [] and repo.list_zones() == []
    repo.seed_demo_data()
    assert len(repo.list_people()) == 6


@pytest.mark.parametrize("url", ["postgresql://localhost/db", "sqlite://", "sqlite:///:memory:",
                                "sqlite:///", "sqlite:///nodum.db?mode=ro"])
def test_invalid_database_urls_fail_explicitly(url):
    with pytest.raises(ValueError):
        database_path(url)


def test_database_configuration_and_relative_path(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)
    assert database_path() == BACKEND_DIRECTORY / "nodum.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'configured.db'}")
    assert database_path() == tmp_path / "configured.db"


def test_app_lifespan_uses_configured_database_and_restores_data(monkeypatch, database_url):
    monkeypatch.setenv("DATABASE_URL", database_url)
    previous_repo = getattr(app.state, "repository", None)
    previous_actions = getattr(app.state, "agent_actions", None)

    async def lifecycle():
        async with app.router.lifespan_context(app):
            assert isinstance(app.state.repository, SQLiteRepository)
            assert app.state.agent_actions.repository is app.state.repository
            invite(app.state.repository)
        async with app.router.lifespan_context(app):
            assert access(app.state.repository).allowed

    try:
        asyncio.run(lifecycle())
    finally:
        app.state.repository = previous_repo
        app.state.agent_actions = previous_actions


def test_actual_process_restart_reads_permissions(database_url):
    invite(reopen(database_url))
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    program = """
from datetime import datetime, timezone
from app.sqlite_repository import SQLiteRepository
from app.models.access import AccessCheckInput
from app.services.access import check_access
repo = SQLiteRepository()
repo.initialize()
decision = check_access(repo, AccessCheckInput(person_id='persisted-guest', zone_id='floor-5', purpose='Test'),
                        datetime(2026, 9, 29, 12, tzinfo=timezone.utc))
assert decision.allowed
print('persisted-access-ok')
"""
    result = subprocess.run([sys.executable, "-B", "-c", program], env=environment,
                            cwd=BACKEND_DIRECTORY, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "persisted-access-ok"


def test_concurrent_initialization_is_idempotent(database_url):
    barrier = Barrier(2)

    def initialize(_):
        barrier.wait(timeout=5)
        repository = reopen(database_url)
        return len(repository.list_people())

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(initialize, range(2))) == [6, 6]
    assert len(reopen(database_url).list_work_orders()) == 2


def test_documented_initialization_command(database_url):
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    for _ in range(2):
        result = subprocess.run([sys.executable, "-B", "-m", "app.database"], env=environment,
                                cwd=BACKEND_DIRECTORY, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stderr
        assert "Nodum database initialized:" in result.stdout
    assert len(reopen(database_url).list_people()) == 6


def test_import_and_openapi_do_not_create_database(database_url):
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    result = subprocess.run(
        [sys.executable, "-B", "-c", "from app.main import app; assert '/agent/chat' in app.openapi()['paths']"],
        env=environment, cwd=BACKEND_DIRECTORY, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert not database_path(database_url).exists()


def test_wal_startup_retries_contention_and_closes_connections(database_url, monkeypatch):
    from app import database
    locked = sqlite3.OperationalError("database is locked")
    locked.sqlite_errorcode = sqlite3.SQLITE_BUSY
    first, second = MagicMock(), MagicMock()
    first.execute.side_effect = locked
    second.execute.return_value.fetchone.return_value = ("wal",)
    db = SQLiteDatabase(database_url)
    monkeypatch.setattr(db, "_connect", MagicMock(side_effect=[first, second]))
    monkeypatch.setattr(database, "sleep", lambda _: first.close.assert_called_once())
    db._enable_wal()
    assert db._connect.call_count == 2
    second.close.assert_called_once()


def test_wal_startup_does_not_retry_unrelated_errors(database_url, monkeypatch):
    db = SQLiteDatabase(database_url)
    connection = MagicMock()
    connection.execute.side_effect = sqlite3.OperationalError("disk I/O error")
    monkeypatch.setattr(db, "_connect", MagicMock(return_value=connection))
    with pytest.raises(sqlite3.OperationalError, match="disk I/O"):
        db._enable_wal()
    assert db._connect.call_count == 1
    connection.close.assert_called_once()


def test_wal_startup_retry_is_bounded(database_url, monkeypatch):
    from app import database
    locked = sqlite3.OperationalError("database is locked")
    locked.sqlite_errorcode = sqlite3.SQLITE_BUSY
    connection = MagicMock()
    connection.execute.side_effect = locked
    db = SQLiteDatabase(database_url)
    monkeypatch.setattr(db, "_connect", MagicMock(return_value=connection))
    monkeypatch.setattr(database, "monotonic", MagicMock(side_effect=[0, 6]))
    with pytest.raises(sqlite3.OperationalError, match="locked"):
        db._enable_wal()
    assert db._connect.call_count == 1
    connection.close.assert_called_once()
