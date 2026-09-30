"""Hardware-neutral inventory, simulated observations and command audit records."""
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.access import AccessDecision, NonEmptyString, UTCTimestamp


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConnectorKind(str, Enum):
    ACCESS = "access_control"
    ELEVATOR = "elevator"
    READER = "credential_reader"
    WAYFINDING = "wayfinding"
    SENSING = "sensing"


class DeviceType(str, Enum):
    DOOR = "door"
    LOCK = "smart_lock"
    READER = "credential_reader"
    TURNSTILE = "turnstile"
    ELEVATOR = "elevator"
    FLOOR_CONTROLLER = "elevator_floor_controller"
    LIGHT = "navigation_light"
    SIGN = "digital_sign"
    RING_DEVICE = "ring_device"


class Command(str, Enum):
    LOCK = "lock"
    UNLOCK = "unlock"
    TEMPORARY_UNLOCK = "temporary_unlock"
    CALL = "call_elevator"
    AUTHORIZE_FLOOR = "authorize_floor"
    ILLUMINATE = "illuminate_route"
    SHOW = "show_destination"
    CLEAR = "clear_route"


class DeviceMetadata(Record):
    """Allowlisted public fields. No credentials, arbitrary URLs or provider config."""
    description: str = Field(default="", max_length=500)
    location_label: str = Field(default="", max_length=200)


class IntegrationInput(Record):
    id: NonEmptyString
    name: NonEmptyString
    provider: NonEmptyString = "simulator"
    kind: ConnectorKind
    enabled: bool = False


class BuildingIntegration(IntegrationInput):
    mode: Literal["simulated", "ring"] = "simulated"
    created_at: UTCTimestamp
    updated_at: UTCTimestamp


class DeviceInput(Record):
    id: NonEmptyString
    integration_id: NonEmptyString
    device_type: DeviceType
    name: NonEmptyString
    zone_id: NonEmptyString  # Physical location, not authorization scope.
    capabilities: list[NonEmptyString] = Field(min_length=1)
    connection_status: Literal["online", "offline"] = "online"
    metadata: DeviceMetadata = Field(default_factory=DeviceMetadata)
    target_device_id: NonEmptyString | None = None  # Reader -> controlled access point.


class BuildingDevice(DeviceInput):
    provider: NonEmptyString
    simulated: bool = True
    external_device_id: str | None = None
    external_account_key: str | None = None
    created_at: UTCTimestamp


class DeviceMapping(Record):
    id: NonEmptyString  # Device ID; one mapping record per device.
    zone_ids: list[NonEmptyString] = Field(min_length=1)
    updated_at: UTCTimestamp
    updated_by: NonEmptyString


class DeviceState(Record):
    id: NonEmptyString
    locked: bool = True
    unlocked_until: UTCTimestamp | None = None
    current_floor: int | None = None
    requested_floor: int | None = None
    authorized_floor: int | None = None
    authorized_zone_id: str | None = None
    authorized_person_id: str | None = None
    authorization_expires_at: UTCTimestamp | None = None
    route: list[str] = Field(default_factory=list)
    destination_label: str | None = None
    last_command_id: str | None = None
    updated_at: UTCTimestamp


class CredentialKind(str, Enum):
    NFC = "nfc"
    BADGE = "badge"
    QR = "qr_mobile"


class CredentialInput(Record):
    id: NonEmptyString
    kind: CredentialKind
    value: str = Field(min_length=1, max_length=256, repr=False)
    person_id: NonEmptyString


class CredentialBinding(Record):
    id: NonEmptyString
    kind: CredentialKind
    fingerprint: str = Field(repr=False)
    person_id: NonEmptyString
    active: bool = True
    created_at: UTCTimestamp


class ActionInput(Record):
    id: NonEmptyString  # Caller idempotency key.
    person_id: NonEmptyString
    zone_id: NonEmptyString
    purpose: NonEmptyString
    command: Command
    journey_id: NonEmptyString | None = None
    duration_seconds: int = Field(default=10, ge=1, le=30, strict=True)


class ActuatorEvent(Record):
    id: NonEmptyString
    request_fingerprint: str
    device_id: NonEmptyString
    integration_id: NonEmptyString
    provider: NonEmptyString
    command: Command
    person_id: NonEmptyString
    zone_id: NonEmptyString
    journey_id: str | None = None
    at: UTCTimestamp
    simulated: Literal[True] = True
    executed: bool
    status: Literal["executed", "failed"]
    message: str
    decision: AccessDecision
    state: DeviceState | None = None


class ActionResult(Record):
    status: Literal["executed", "denied", "manual_action_required", "failed"]
    simulated: bool = True
    executed: bool = False
    decision: AccessDecision
    message: str
    actuator_event_id: str | None = None


class ScanInput(Record):
    id: NonEmptyString
    reader_id: NonEmptyString
    kind: CredentialKind
    value: str = Field(min_length=1, max_length=256, repr=False)
    zone_id: NonEmptyString
    purpose: NonEmptyString = "Simulated credential scan"
    journey_id: NonEmptyString | None = None


class CredentialEvent(Record):
    id: NonEmptyString
    request_fingerprint: str
    reader_id: NonEmptyString
    kind: CredentialKind
    person_id: str | None = None
    credential_id: str | None = None
    zone_id: NonEmptyString
    at: UTCTimestamp
    simulated: Literal[True] = True
    result: ActionResult


class JourneyInput(Record):
    id: NonEmptyString
    person_id: NonEmptyString
    purpose: NonEmptyString
    starting_zone_id: NonEmptyString
    destination_zone_id: NonEmptyString
    appointment_id: NonEmptyString | None = None
    arrival_ring_event_id: NonEmptyString | None = None
    use_connectors: bool = True


class JourneyStep(Record):
    kind: str
    zone_id: str
    result: ActionResult


class Journey(JourneyInput):
    request_fingerprint: str
    authorized_zone_ids: list[str] = Field(default_factory=list)
    current_confirmed_zone_id: str | None = None
    status: Literal["denied", "ready", "manual_action_required", "in_progress", "completed", "failed"]
    created_at: UTCTimestamp
    updated_at: UTCTimestamp
    route: list[str] = Field(default_factory=list)
    steps: list[JourneyStep] = Field(default_factory=list)


class TransitionInput(Record):
    id: NonEmptyString
    source_device_id: NonEmptyString
    zone_id: NonEmptyString


class JourneyTransition(TransitionInput):
    journey_id: NonEmptyString
    person_id: NonEmptyString
    at: UTCTimestamp
    simulated: Literal[True] = True
    request_fingerprint: str
