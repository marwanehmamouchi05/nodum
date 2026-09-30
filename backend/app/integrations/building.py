"""Connector contracts and pure software simulators, with no permission logic.

Only services may dispatch commands after policy evaluation. Future physical
adapters must additionally support durable command IDs and delivery reconciliation.
No manufacturer adapters or physical I/O are implemented here.
"""
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Protocol

from app.models.integrations import Command, DeviceState


@dataclass(frozen=True)
class CommandContext:
    command_id: str
    person_id: str
    zone_id: str
    at: datetime
    expires_at: datetime
    floor: int | None = None
    route: tuple[str, ...] = ()
    destination_label: str = ""


class AccessControlAdapter(Protocol):
    def execute(self, command: Command, state: DeviceState, context: CommandContext) -> DeviceState: ...


class ElevatorAdapter(Protocol):
    def execute(self, command: Command, state: DeviceState, context: CommandContext) -> DeviceState: ...


class CredentialReaderAdapter(Protocol):
    def fingerprint(self, kind: str, value: str) -> str: ...


class WayfindingAdapter(Protocol):
    def execute(self, command: Command, state: DeviceState, context: CommandContext) -> DeviceState: ...


def updated(state, context, **changes):
    return DeviceState.model_validate(state.model_dump() | changes | {
        "last_command_id": context.command_id, "updated_at": context.at})


class SimulatedAccessControl:
    def execute(self, command, state, context):
        if command not in {Command.LOCK, Command.UNLOCK, Command.TEMPORARY_UNLOCK}:
            raise ValueError("Unsupported access command")
        locked = command == Command.LOCK
        return updated(state, context, locked=locked,
                       unlocked_until=None if locked else context.expires_at)


class SimulatedElevator:
    def execute(self, command, state, context):
        if command == Command.CALL:
            # A call is a request, not confirmation that the cabin moved.
            return updated(state, context, requested_floor=context.floor)
        if command == Command.AUTHORIZE_FLOOR:
            return updated(state, context, authorized_floor=context.floor,
                           authorized_zone_id=context.zone_id, authorized_person_id=context.person_id,
                           authorization_expires_at=context.expires_at)
        raise ValueError("Unsupported elevator command")


class SimulatedCredentialReader:
    def fingerprint(self, kind, value):
        return sha256((kind + "\0" + value).encode()).hexdigest()


class SimulatedWayfinding:
    def execute(self, command, state, context):
        if command == Command.CLEAR:
            return updated(state, context, route=[], destination_label=None)
        if command not in {Command.ILLUMINATE, Command.SHOW}:
            raise ValueError("Unsupported wayfinding command")
        return updated(state, context, route=list(context.route), destination_label=context.destination_label,
                       authorized_zone_id=context.zone_id, authorized_person_id=context.person_id,
                       authorization_expires_at=context.expires_at)


class ConnectorRegistry:
    """Server-owned registry. Public requests cannot load code, URLs or providers."""
    def __init__(self):
        self.access: dict[str, AccessControlAdapter] = {"simulator": SimulatedAccessControl()}
        self.elevators: dict[str, ElevatorAdapter] = {"simulator": SimulatedElevator()}
        self.readers: dict[str, CredentialReaderAdapter] = {"simulator": SimulatedCredentialReader()}
        self.wayfinding: dict[str, WayfindingAdapter] = {"simulator": SimulatedWayfinding()}

    def actuator(self, provider, kind):
        return {"access_control": self.access, "elevator": self.elevators,
                "wayfinding": self.wayfinding}.get(kind, {}).get(provider)
