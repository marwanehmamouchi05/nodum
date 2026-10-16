"""Read-only lifecycle planning cannot erase history or widen visibility."""

from datetime import timedelta
import pytest

from conftest import NOW
from test_mqtt_sensor import sensor, structure, payload  # noqa: F401
from app.services.retention import plan_contact_retention
from app.services.errors import DomainError
from app.services.scoped_repository import bind_created


def plan(sensor, **changes):
    ingest, _, auth = sensor
    return plan_contact_retention(
        auth(),
        **(
            {
                "scope_id": ingest.binding.building_id,
                "before": NOW + timedelta(seconds=1),
                "now": NOW + timedelta(seconds=2),
            }
            | changes
        ),
    )


def test_candidates_holds_and_protected_history_do_not_mutate(sensor):
    ingest, repo, _ = sensor
    ingest.receive(ingest.binding.topic, payload())
    original = repo.list_operational_records("operation_activity")
    own = original[0]
    for identifier, scope, source in [
        ("foreign", "demo-org", "MQTT contact observation"),
        ("security", own["scope_id"], "Security audit"),
    ]:
        row = own | {"id": identifier, "scope_id": scope, "source": source}
        repo.save_operational_record("operation_activity", row)
        bind_created(repo, "operation_activity", identifier, scope)
    before = repo.list_operational_records("operation_activity")
    report = plan(sensor)
    assert report["candidate_count"] == 1 and report["protected_count"] == 1
    assert not report["apply_enabled"] and not report["truncated"]
    held = plan(sensor, held_ids=[own["id"]])
    assert held["candidate_count"] == 0 and held["held_count"] == 1
    assert repo.list_operational_records("operation_activity") == before
    assert ingest.receive(ingest.binding.topic, payload()) == "duplicate"


def test_scan_is_bounded_and_cutoff_is_strict(sensor):
    ingest, _, _ = sensor
    for i in range(4):
        ingest.receive(ingest.binding.topic, payload(event_id=f"event-{i}"))
    report = plan(sensor, max_scan=2)
    assert report["candidate_count"] == 2 and report["truncated"]
    assert report["scan_budget_used"] == 2
    assert plan(sensor, before=NOW)["candidate_count"] == 0


def test_foreign_scope_and_revocation_rejected(sensor):
    _, repo, _ = sensor
    with pytest.raises(DomainError) as exc:
        plan(sensor, scope_id="demo-org")
    assert exc.value.status_code == 403
    grant = repo.get_role_assignment("sensor-operator")
    repo.save_role_assignment(grant.model_copy(update={"active": False}))
    with pytest.raises(DomainError) as exc:
        plan(sensor)
    assert exc.value.status_code == 403


@pytest.mark.parametrize(
    "changes",
    [
        {"max_scan": True},
        {"max_scan": 1001},
        {"before": NOW.replace(tzinfo=None)},
        {"before": NOW + timedelta(days=1)},
        {"scope_id": ""},
    ],
)
def test_invalid_plans_rejected(sensor, changes):
    with pytest.raises(DomainError) as exc:
        plan(sensor, **changes)
    assert exc.value.status_code == 422
