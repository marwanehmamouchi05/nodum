"""Configured product topology; independent of legacy/demo hardware records."""
from enum import Enum
from typing import Literal
from pydantic import Field, model_validator
from app.models.authorization import Record, Role
from app.models.access import NonEmptyString, UTCTimestamp


class NodeKind(str, Enum):
    ORGANIZATION = "organization"
    BUILDING = "building"
    FLOOR = "floor"
    LOCATION = "location"
    UNIT = "unit"
    BUSINESS = "business"
    ROOM = "room"
    INTEGRATION = "integration"
    DEVICE = "device"


class ConnectionPath(str, Enum):
    CLOUD = "cloud"
    EDGE = "edge"
    SIMULATION = "simulation"


class StructureNode(Record):
    id: NonEmptyString
    name: NonEmptyString
    kind: NodeKind
    organization_id: NonEmptyString
    building_id: NonEmptyString | None = None
    parent_id: NonEmptyString | None = None
    scope_id: NonEmptyString
    demo: bool = False
    building_type: Literal["residential", "commercial", "mixed_use"] = "mixed_use"
    address: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=1000)
    restricted: bool = False
    common: bool = False  # Description only; never an access grant.
    floor_order: int | None = None
    connection_path: ConnectionPath | None = None
    integration_id: NonEmptyString | None = None
    device_type: NonEmptyString | None = None
    capabilities: list[NonEmptyString] = Field(default_factory=list)

    @model_validator(mode="after")
    def hardware_fields(self):
        if self.capabilities:
            raise ValueError("Hardware capabilities require a verified adapter; none are enabled in Phase B")
        hardware = self.kind in {NodeKind.INTEGRATION, NodeKind.DEVICE}
        if hardware != (self.connection_path is not None):
            raise ValueError("Hardware requires an explicit connection path")
        if self.kind == NodeKind.DEVICE:
            if not self.integration_id or not self.device_type:
                raise ValueError("Devices require integration and device type")
        elif self.integration_id or self.device_type or self.capabilities:
            raise ValueError("Device fields are only valid for devices")
        if self.floor_order is not None and self.kind != NodeKind.FLOOR:
            raise ValueError("Floor order is only valid for floors")
        return self


class Affiliation(Record):
    id: NonEmptyString
    user_id: NonEmptyString
    role: Role
    target_id: NonEmptyString
    starts_at: UTCTimestamp | None = None
    ends_at: UTCTimestamp | None = None
    active: bool = True

    @model_validator(mode="after")
    def dates(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("Affiliation end must follow start")
        return self
