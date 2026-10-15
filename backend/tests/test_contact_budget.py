from concurrent.futures import ThreadPoolExecutor

import pytest

from app.integrations.mqtt_sensor import ContactIngestor
from app.services.errors import DomainError
from test_mqtt_sensor import sensor, structure, payload  # noqa: F401


def test_contact_capacity_preserves_duplicates_and_rejects_new_ids(sensor):
    original, repo, _ = sensor
    ingest = ContactIngestor(
        original.authorization_factory, original.binding, max_observations=1
    )
    assert ingest.receive(ingest.binding.topic, payload()) == "recorded"
    assert ingest.receive(ingest.binding.topic, payload()) == "duplicate"
    with pytest.raises(DomainError) as error:
        ingest.receive(ingest.binding.topic, payload(event_id="second-event"))
    assert error.value.status_code == 429
    assert repo.count_contact_observations(ingest.binding.device_id) == 1


def test_concurrent_contact_capacity_cannot_overrun(sensor):
    original, repo, _ = sensor
    ingest = ContactIngestor(
        original.authorization_factory, original.binding, max_observations=1
    )

    def deliver(identifier):
        try:
            return ingest.receive(ingest.binding.topic, payload(event_id=identifier))
        except DomainError as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(deliver, ["first", "second"]))
    assert results.count("recorded") == 1 and results.count(429) == 1
    assert repo.count_contact_observations(ingest.binding.device_id) == 1


def test_budget_does_not_count_other_devices_or_non_sensor_journal(sensor):
    ingest, repo, _ = sensor
    record = {
        "id": "unrelated",
        "scope_id": ingest.binding.building_id,
        "source": "visitor activity",
        "resource_id": ingest.binding.device_id,
    }
    repo.save_operational_record("operation_activity", record)
    assert repo.count_contact_observations(ingest.binding.device_id) == 0
    assert repo.count_contact_observations("foreign-device") == 0


def test_capacity_status_surfaces_without_a_broker(sensor):
    from types import SimpleNamespace
    from app.integrations.mqtt_sensor import ContactSubscriber

    ingest, _, _ = sensor
    ingest = ContactIngestor(
        ingest.authorization_factory, ingest.binding, max_observations=1
    )
    ingest.receive(ingest.binding.topic, payload())
    subscriber = ContactSubscriber(ingest, host="127.0.0.1", loopback_fixture=True)
    subscriber._message(
        None,
        None,
        SimpleNamespace(
            topic=ingest.binding.topic, payload=payload(event_id="second"), retain=False
        ),
    )
    assert (
        subscriber.status == "capacity_reached" and subscriber.counts["rejected"] == 1
    )


def test_sqlite_capacity_survives_restart_and_uses_index(sensor, request):
    if request.config.getoption("--repository-backend") != "sqlite":
        pytest.skip("SQLite restart and query plan")
    from app.sqlite_repository import SQLiteRepository
    from app.services.authorization import AuthorizationService

    original, repo, authority = sensor
    ingest = ContactIngestor(
        original.authorization_factory, original.binding, max_observations=1
    )
    ingest.receive(ingest.binding.topic, payload())
    restarted = SQLiteRepository("sqlite:///" + str(repo.database.path))
    resumed = ContactIngestor(
        lambda: AuthorizationService(restarted, authority().principal, authority().now),
        original.binding,
        max_observations=1,
    )
    with pytest.raises(DomainError) as error:
        resumed.receive(resumed.binding.topic, payload(event_id="after-restart"))
    assert error.value.status_code == 429
    with restarted.transaction():
        statements = []
        restarted.database.connection.set_trace_callback(statements.append)
        assert restarted.count_contact_observations(resumed.binding.device_id) == 1
        restarted.database.connection.set_trace_callback(None)
        query = next(s for s in statements if s.startswith("SELECT count(*)"))
        plan = " ".join(
            r[3]
            for r in restarted.database.connection.execute(
                "EXPLAIN QUERY PLAN " + query
            )
        )
        assert "product_contact_budget" in plan
