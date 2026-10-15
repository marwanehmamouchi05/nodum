"""Bounded three-building/device/user read-write acceptance, not a fleet SLA."""

from concurrent.futures import ThreadPoolExecutor
import threading

import pytest

from app.integrations.mqtt_sensor import ContactIngestor, SensorBinding
from app.models.authorization import Principal
from app.services.activity import ActivityService
from app.services.authorization import AuthorizationService
from app.services.errors import DomainError
from conftest import NOW
from test_mqtt_sensor import payload
from test_security_tenants import buildings  # noqa: F401
from test_structure import structure  # noqa: F401


def test_three_building_concurrent_ingestion_reads_and_revocation(repo, buildings):
    barrier = threading.Barrier(6)
    ingestors = []
    for user, prefix, _, _ in buildings:
        principal = Principal(
            user_id=user, person_id=repo.get_auth_user(user).person_id
        )
        ingestors.append(
            ContactIngestor(
                lambda p=principal: AuthorizationService(repo, p, NOW),
                SensorBinding(prefix + "building", prefix + "machine-room-sensor"),
            )
        )

    def write(ingest):
        barrier.wait(timeout=10)
        for i in range(8):
            assert (
                ingest.receive(ingest.binding.topic, payload(event_id=f"bounded-{i}"))
                == "recorded"
            )

    def read(ingest):
        barrier.wait(timeout=10)
        for _ in range(12):
            page = ActivityService(ingest.authorization_factory()).page(limit=10)
            assert all(
                row["resource_id"] == ingest.binding.device_id
                for row in page["items"]
                if row.get("source") == "MQTT contact observation"
            )

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [
            pool.submit(task, ingest) for task in (write, read) for ingest in ingestors
        ]
        for future in futures:
            future.result(timeout=30)
    for ingest, (user, _, _, _) in zip(ingestors, buildings):
        assert repo.count_contact_observations(ingest.binding.device_id) == 8
        grant = repo.get_role_assignment(user + "-grant")
        repo.save_role_assignment(grant.model_copy(update={"active": False}))
        with pytest.raises(DomainError) as error:
            ingest.receive(ingest.binding.topic, payload(event_id="revoked-after-load"))
        assert error.value.status_code == 403
        assert repo.count_contact_observations(ingest.binding.device_id) == 8
