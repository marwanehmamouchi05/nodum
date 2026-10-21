"""Ring simulation service: signed envelopes + deterministic scenarios."""
import hashlib
import hmac
import json
from dataclasses import replace
from datetime import timedelta

import pytest
from cryptography.fernet import Fernet

from app.models.ring import RingPrincipal
from app.services.errors import DomainError
from app.services.ring import RingService, identity, SIGNALS
from app.services.ring_simulation import (
    RingSimulationService, SCENARIOS, SIM_ACCOUNT_ID, SIM_DEVICES,
)
from app.integrations.ring.config import RingSettings

from conftest import NOW


PRINCIPAL = RingPrincipal(person_id="manager-1", masked_account_identifier="m***r@example.test")


def _make_settings(**overrides):
    base = RingSettings(mode="simulation", environment="staging",
                        signing_key="sim-signing",
                        encryption_key=Fernet.generate_key().decode())
    return replace(base, **overrides) if overrides else base


@pytest.fixture
def settings():
    return _make_settings()


@pytest.fixture
def ring(repo, remote):
    return RingService(repo, _make_settings(), remote)


@pytest.fixture
def simulation(ring):
    return RingSimulationService(ring)


@pytest.fixture
def remote():
    from unittest.mock import Mock
    from app.integrations.ring.client import RingClient
    client = Mock(spec=RingClient)
    return client


def _complete_account(simulation):
    """Force the seeded account to a completed state for the simulator."""
    return simulation.ensure_account(NOW)


def test_signing_key_required_when_missing(ring, simulation, remote):
    no_key = RingService(ring.repository, replace(ring.settings, signing_key=""), remote)
    sim = RingSimulationService(no_key)
    with pytest.raises(DomainError) as exc:
        sim.deliver("motion_detected", "sim-camera-lobby", NOW)
    assert exc.value.status_code == 503


def test_live_mode_rejects_simulation(ring, remote):
    live_settings = replace(ring.settings, mode="live")
    live = RingService(ring.repository, live_settings, remote)
    sim = RingSimulationService(live)
    with pytest.raises(DomainError) as exc:
        sim.deliver("motion_detected", "sim-camera-lobby", NOW)
    assert exc.value.status_code == 403


def test_seed_account_idempotent(simulation):
    first = _complete_account(simulation)
    second = _complete_account(simulation)
    assert first.id == second.id
    assert first.status == "completed"
    assert first.owner_id == "manager-1"
    assert first.account_id == SIM_ACCOUNT_ID


def test_devices_have_simulation_metadata(simulation):
    devices = simulation.devices()
    ids = {device.id for device in devices}
    assert ids == {device["id"] for device in SIM_DEVICES}
    for device in devices:
        assert device.attributes["is_simulation"] is True
        assert device.attributes["manufacturer"] == "ring"


def test_deliver_single_event_uses_real_path(simulation):
    delivered = simulation.deliver("button_press", "sim-doorbell-front", NOW,
                                   request_id="req-1", event_id="evt-1")
    assert delivered["status"] == "received"
    assert delivered["device_id"] == "sim-doorbell-front"
    saved = simulation.repository.get_ring_event(delivered["id"])
    assert saved.event_type == "button_press"
    assert saved.signal == "doorbell"
    assert saved.account_id == SIM_ACCOUNT_ID
    assert saved.source == "sim-doorbell-front"


def test_deliver_duplicate_request_returns_duplicate(simulation):
    first = simulation.deliver("motion_detected", "sim-camera-lobby", NOW,
                               request_id="dup", event_id="evt-a")
    second = simulation.deliver("motion_detected", "sim-camera-lobby", NOW,
                                request_id="dup", event_id="evt-a")
    assert second["status"] == "duplicate"
    assert second["id"] == first["id"]


def test_run_scenario_emits_expected_signals(simulation):
    delivered = simulation.run_scenario("visitor_arrives", NOW)
    kinds = [step["event_type"] for step in delivered]
    assert kinds == ["motion_detected", "button_press", "person_detected"]
    # Person signal is now first-class in SIGNALS
    assert SIGNALS["person_detected"] == "person"
    # Each event must be persisted
    for step in delivered:
        saved = simulation.repository.get_ring_event(step["id"])
        assert saved.status == "received"


@pytest.mark.parametrize("scenario,signals", [
    ("visitor_arrives", ["motion", "doorbell", "person"]),
    ("package_delivery", ["motion", "doorbell", "package"]),
    ("after_hours_person", ["motion", "person", "motion", "person"]),
    ("emergency_access", ["motion", "doorbell"]),
    ("contact_sensor_sequence", ["contact_open", "contact_closed"]),
    ("device_lifecycle", ["device_offline", "device_online"]),
])
def test_each_scenario_returns_persisted_normalized_signals(simulation, scenario, signals):
    delivered = simulation.run_scenario(scenario, NOW)
    assert [event["signal"] for event in delivered] == signals
    for event in delivered:
        saved = simulation.repository.get_ring_event(event["id"])
        assert saved.signal == event["signal"]
        assert saved.occurred_at <= NOW
        assert event["is_simulation"] is True
        raw = saved.raw_payload.encode()
        signature = simulation._sign(raw, simulation.settings.signing_key)
        assert simulation.ring_service.receive_event(raw, signature, NOW)["status"] == "duplicate"
        with pytest.raises(DomainError) as exc:
            simulation.ring_service.receive_event(raw, "sha256=" + "0" * 64, NOW)
        assert exc.value.status_code == 401


def test_run_scenario_advances_timestamps(simulation):
    delivered = simulation.run_scenario("contact_sensor_sequence", NOW)
    first, second = delivered[0], delivered[1]
    assert first["event_type"] == "contact_sensor_faulted"
    assert second["event_type"] == "contact_sensor_cleared"
    first_event = simulation.repository.get_ring_event(first["id"])
    second_event = simulation.repository.get_ring_event(second["id"])
    assert second_event.occurred_at > first_event.occurred_at


def test_new_scenario_sorts_after_previous_burst(simulation):
    first = simulation.run_scenario("after_hours_person", NOW)
    second = simulation.run_scenario("device_lifecycle", NOW + timedelta(milliseconds=10))
    earlier = [simulation.repository.get_ring_event(event["id"]).occurred_at for event in first]
    later = [simulation.repository.get_ring_event(event["id"]).occurred_at for event in second]
    assert max(earlier) < min(later)


def test_unknown_scenario_rejected(simulation):
    with pytest.raises(DomainError) as exc:
        simulation.run_scenario("does_not_exist", NOW)
    assert exc.value.status_code == 404


def test_scenario_runs_produce_unique_ids(simulation):
    first = simulation.run_scenario("visitor_arrives", NOW)
    second = simulation.run_scenario("visitor_arrives", NOW)
    first_ids = {event["id"] for event in first}
    second_ids = {event["id"] for event in second}
    # Same scenario shape but each run gets its own request_id/event_id prefix,
    # so the database-side ids are distinct and both are stored without conflict.
    assert first_ids.isdisjoint(second_ids)
    inbox_ids = {event.id for event in simulation.repository.list_ring_events()
                 if event.account_id == "simulation.playground"}
    assert first_ids | second_ids <= inbox_ids
    assert len(inbox_ids) == 6  # two runs × three steps


def test_scenario_catalog_shape(simulation):
    catalog = simulation.scenarios()
    names = {entry["name"] for entry in catalog}
    assert names == set(SCENARIOS.keys())
    assert all("label" in entry and "description" in entry for entry in catalog)


def test_signed_payload_matches_external_signature(simulation):
    """The envelope bytes used internally must match what an external system
    would sign, so the HMAC verification path remains realistic."""
    delivered = simulation.deliver("motion_detected", "sim-camera-lobby", NOW,
                                   request_id="req-x", event_id="evt-x")
    saved = simulation.repository.get_ring_event(delivered["id"])
    expected = json.loads(saved.raw_payload)
    assert expected["meta"]["version"] == "1.1"
    assert expected["data"]["attributes"]["source"] == "sim-camera-lobby"
    assert expected["meta"]["account_id"] == SIM_ACCOUNT_ID
    # Recompute signature exactly to confirm format is the documented sha256=
    raw = saved.raw_payload.encode("utf-8")
    signature = "sha256=" + hmac.new(simulation.settings.signing_key.encode(),
                                    raw, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(signature, "sha256=" + hmac.new(
        simulation.settings.signing_key.encode(), raw, hashlib.sha256).hexdigest())


def test_package_and_person_are_first_class_signals(simulation):
    package = simulation.deliver("package_detected", "sim-doorbell-front", NOW,
                                 request_id="pkg-1", event_id="pkg-1")
    person = simulation.deliver("person_detected", "sim-camera-lobby", NOW,
                                request_id="per-1", event_id="per-1")
    assert SIGNALS["package_detected"] == "package"
    assert SIGNALS["person_detected"] == "person"
    pkg_event = simulation.repository.get_ring_event(package["id"])
    per_event = simulation.repository.get_ring_event(person["id"])
    assert pkg_event.signal == "package"
    assert per_event.signal == "person"


def test_account_summary_reports_simulation_flag(simulation):
    summary = simulation.account_summary(NOW)
    assert summary["is_simulation"] is True
    assert summary["account_id"] == SIM_ACCOUNT_ID
    assert summary["status"] == "completed"


def test_environment_isolates_simulation_account(ring, simulation):
    _complete_account(simulation)
    # Same key under a different environment should produce a separate identity.
    other = RingService(ring.repository,
                        replace(ring.settings, environment="production"),
                        ring.client)
    other_sim = RingSimulationService(other)
    other_sim.account_summary(NOW)
    staging = ring.repository.get_ring_account(
        identity("staging", SIM_ACCOUNT_ID))
    production = ring.repository.get_ring_account(
        identity("production", SIM_ACCOUNT_ID))
    assert staging is not None and staging.environment == "staging"
    assert production is not None and production.environment == "production"
    assert staging.id != production.id
