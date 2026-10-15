import base64
import json

import pytest

from app.services.activity import ActivityService
from app.services.scoped_repository import bind_created
from test_authorization import headers
from test_manager import manager, structure, ROOT  # noqa: F401
from conftest import NOW


def events(manager, count=30):
    repo = manager.repo
    for prefix, scope in (("own", ROOT + "apartment-101"), ("foreign", "demo-org")):
        for i in range(count):
            record = {
                "id": f"{prefix}-{i:04}",
                "scope_id": scope,
                "at": NOW.isoformat(),
                "action": "sensor.contact.open",
                "resource_id": ROOT + "machine-room-sensor",
                "location_id": ROOT + "apartment-101",
                "actor_id": "resident-1",
                "simulated": True,
                "observation_digest": "private-internal-field",
            }
            repo.save_operational_record("operation_activity", record)
            bind_created(repo, "operation_activity", record["id"], scope)


def test_pages_do_not_skip_same_timestamp_or_leak_foreign_histories(manager, api):
    events(manager)
    session = headers(manager.repo, "resident")
    all_ids, cursor = [], None
    for _ in range(10):
        query = "/manager/activity?limit=7" + ("&cursor=" + cursor if cursor else "")
        status, page = api("GET", query, headers=session)
        assert status == 200 and page["schema_version"] == 1
        assert "private-internal-field" not in json.dumps(page)
        all_ids += [r["id"] for r in page["items"]]
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert all_ids == [f"own-{i:04}" for i in reversed(range(30))]
    # A valid cursor and requested scope never grant authority after revocation.
    cursor = ActivityService(manager.auth).page(limit=1)["next_cursor"]
    grant = manager.repo.get_role_assignment("resident-grant")
    manager.repo.save_role_assignment(grant.model_copy(update={"active": False}))
    assert ActivityService(manager.auth).page(cursor=cursor)["items"] == []
    assert api("GET", "/manager/activity?scope_id=demo-org", headers=session)[0] == 403


@pytest.mark.parametrize(
    "raw",
    [
        b"{}",
        b'[2,"x","y"]',
        b'[true,"x","y"]',
        b'[1,null,"x"]',
        b'[1,"2026-10-15","x"]',
    ],
)
def test_invalid_cursors_are_redacted(manager, api, raw):
    cursor = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    status, result = api(
        "GET",
        "/manager/activity?cursor=" + cursor,
        headers=headers(manager.repo, "resident"),
    )
    assert status == 422 and result == {"detail": "Invalid activity cursor"}


def test_snapshot_does_not_bulk_load_operational_activity(manager, monkeypatch):
    events(manager, 120)
    original = manager.repo.list_operational_records

    def guarded(kind):
        assert kind != "operation_activity", "snapshot loaded full activity history"
        return original(kind)

    monkeypatch.setattr(manager.repo, "list_operational_records", guarded)
    assert len(manager.snapshot()["activity"]) == 100


def test_binding_mismatch_cannot_be_injected_into_page(manager):
    from app.models.authorization import ResourceBinding

    events(manager, 1)
    manager.repo.save_resource_binding(
        ResourceBinding(
            resource_type="operation_activity",
            resource_id="own-0000",
            scope_id="demo-org",
        )
    )
    assert ActivityService(manager.auth).page()["items"] == []


def test_sqlite_page_plan_and_bounded_decode(manager, request, monkeypatch):
    if request.config.getoption("--repository-backend") != "sqlite":
        pytest.skip("SQLite query plan and JSON materialization")
    events(manager, 200)
    repo = manager.repo
    with repo.transaction():
        statements = []
        repo.database.connection.set_trace_callback(statements.append)
        result = repo.page_operation_activity([ROOT + "apartment-101"], limit=6)
        repo.database.connection.set_trace_callback(None)
        query = next(s for s in statements if s.startswith("SELECT o.data"))
        plan = " ".join(
            r[3]
            for r in repo.database.connection.execute("EXPLAIN QUERY PLAN " + query)
        )
        assert "product_activity_page" in plan and "TEMP B-TREE" not in plan
    assert len(result) == 6
