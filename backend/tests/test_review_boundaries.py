"""Independent adversarial cases missing from the foundation acceptance suite."""

from datetime import timedelta
import pytest

from conftest import NOW
from test_building_integrations import action, building  # noqa: F401
from test_ring import event, signed, service, settings, remote  # noqa: F401
from app.integrations.building import SimulatedAccessControl
from app.services.errors import DomainError
from test_security_tenants import buildings  # noqa: F401
from test_structure import structure, user_service  # noqa: F401
from test_authorization import headers


@pytest.mark.parametrize(
    "subtype,signal",
    [
        ("human", "person"),
        ("package_delivery", "package"),
        ("vehicle", "motion"),
        ("future_value", "motion"),
    ],
)
def test_official_motion_classification(service, subtype, signal):
    payload = event("motion_detected")
    payload["data"]["attributes"]["sub_type"] = subtype
    raw, signature = signed(service, payload)
    reply = service.receive_event(raw, signature, NOW)
    assert service.repository.get_ring_event(reply["id"]).signal == signal
    assert not service.repository.list_emergencies()


def test_ring_conflicting_classification_is_not_a_duplicate(service):
    payload = event("motion_detected")
    payload["data"]["attributes"]["sub_type"] = "human"
    service.receive_event(*signed(service, payload), NOW)
    payload["data"]["attributes"]["sub_type"] = "package_delivery"
    with pytest.raises(DomainError, match="Conflicting"):
        service.receive_event(*signed(service, payload), NOW)


@pytest.mark.parametrize(
    "corruption", ["expiry", "correlation", "authority", "unrelated_state"]
)
def test_adapter_cannot_expand_authorized_result(building, repo, corruption):
    class FaultyAdapter:
        def execute(self, command, state, context):
            updated = SimulatedAccessControl().execute(command, state, context)
            if corruption == "expiry":
                updated.unlocked_until = context.expires_at + timedelta(days=1)
            elif corruption == "correlation":
                updated.last_command_id = "another-command"
            elif corruption == "authority":
                updated.authorized_person_id = "another-person"
            else:
                updated.current_floor = 99
            return updated

    building.registry.access["simulator"] = FaultyAdapter()
    response = building.action("demo-entrance", action(), NOW)
    assert response.status == "failed"
    assert not response.executed
    assert building.status("demo-entrance", NOW)["state"].locked
    assert repo.get_actuator_event("command-1").status == "failed"


def test_retry_after_lost_response_does_not_redispatch(building, repo):
    class CountingAdapter(SimulatedAccessControl):
        count = 0

        def execute(self, command, state, context):
            self.count += 1
            return super().execute(command, state, context)

    adapter = CountingAdapter()
    building.registry.access["simulator"] = adapter
    building.action("demo-entrance", action(), NOW)  # caller loses this response
    building.connection("demo-entrance", "offline", "manager-1", NOW)
    replay = building.action("demo-entrance", action(), NOW + timedelta(minutes=1))
    assert replay.executed  # historical simulated receipt, never a fresh command
    assert adapter.count == 1
    assert building.status("demo-entrance", NOW + timedelta(minutes=1))["state"].locked


def test_in_place_adapter_fault_cannot_poison_saved_state(building, repo):
    class MutatingFailure:
        def execute(self, command, state, context):
            state.locked = False
            state.route.append("Unauthorized destination")
            raise TimeoutError("private transport detail")

    building.registry.access["simulator"] = MutatingFailure()
    assert building.action("demo-entrance", action(), NOW).status == "failed"
    state = repo.get_device_state("demo-entrance")
    assert state.locked and not state.route


@pytest.mark.parametrize("index", [0, 1, 2])
def test_scoped_commands_cannot_use_foreign_or_replayed_ids(
    api, repo, buildings, index
):
    user, _, _, _ = buildings[index]
    session = headers(repo, user)
    for target in ["demo-entrance", buildings[(index + 1) % 3][1] + "entrance-lock"]:
        status, _ = api(
            "POST",
            "/building/devices/" + target + "/actions",
            action().model_dump(mode="json"),
            headers=session,
        )
        assert status == 403
    assert not repo.list_actuator_events()


def test_independent_display_adapter_extension(repo):
    from test_building_integrations import demo
    from app.services.building import BuildingService
    from app.integrations.building import ConnectorRegistry
    from app.models.integrations import Command

    journey = demo(repo)

    class DisplayAdapter:
        """Alternate pure text-display implementation, no domain imports or I/O."""

        def execute(self, command, state, context):
            assert command == Command.SHOW
            return state.model_copy(
                update={
                    "route": list(context.route),
                    "destination_label": context.destination_label,
                    "authorized_zone_id": context.zone_id,
                    "authorized_person_id": context.person_id,
                    "authorization_expires_at": context.expires_at,
                    "last_command_id": context.command_id,
                    "updated_at": context.at,
                }
            )

    registry = ConnectorRegistry()
    registry.wayfinding["simulator"] = DisplayAdapter()
    display = next(
        d for d in repo.list_building_devices() if "show_destination" in d.capabilities
    )
    result = BuildingService(repo, registry).action(
        display.id,
        action(
            id="alternate-display",
            person_id=journey.person_id,
            command="show_destination",
            journey_id=journey.id,
        ),
        NOW,
    )
    assert result.executed and result.simulated
    assert (
        repo.get_device_state(display.id).destination_label
        == "Atlas Dental - Office 106"
    )


def test_delayed_adapter_and_competing_lock_are_serialized(building, repo):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    entered, release = Event(), Event()

    class DelayedAdapter(SimulatedAccessControl):
        def execute(self, command, state, context):
            if context.command_id == "command-1":
                entered.set()
                if not release.wait(2):
                    raise TimeoutError("fixture timeout")
            return super().execute(command, state, context)

    building.registry.access["simulator"] = DelayedAdapter()
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(building.action, "demo-entrance", action(), NOW)
        try:
            assert entered.wait(2)
            second = executor.submit(
                building.action,
                "demo-entrance",
                action(id="competing-lock", command="lock"),
                NOW + timedelta(seconds=1),
            )
        finally:
            release.set()
        assert first.result().executed and second.result().executed
    assert repo.get_device_state("demo-entrance").locked
    assert len(repo.list_actuator_events()) == 2


def test_failed_dispatch_is_a_terminal_receipt_not_an_automatic_retry(building, repo):
    class TimeoutAdapter:
        calls = 0

        def execute(self, command, state, context):
            self.calls += 1
            raise TimeoutError("private")

    adapter = TimeoutAdapter()
    building.registry.access["simulator"] = adapter
    first = building.action("demo-entrance", action(), NOW)
    assert first.status == "failed"
    assert (
        building.action("demo-entrance", action(), NOW + timedelta(seconds=1)) == first
    )
    assert adapter.calls == 1 and len(repo.list_actuator_events()) == 1


def test_sqlite_audit_write_failure_rolls_back_state(
    building, repo, request, monkeypatch
):
    if request.config.getoption("--repository-backend") != "sqlite":
        pytest.skip("SQLite atomic state/receipt persistence")

    def fail(record):
        raise RuntimeError("fixture storage failure")

    monkeypatch.setattr(repo, "save_actuator_event", fail)
    with pytest.raises(RuntimeError):
        building.action("demo-entrance", action(), NOW)
    assert repo.get_device_state("demo-entrance").locked
    assert not repo.list_actuator_events()
