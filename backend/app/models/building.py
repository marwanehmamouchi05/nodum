from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional


class PersonRole(str, Enum):
    RESIDENT = "resident"
    GUEST = "guest"
    CONTRACTOR = "contractor"
    BUSINESS_VISITOR = "business_visitor"
    EMPLOYEE = "employee"
    DELIVERY = "delivery"
    MANAGER = "manager"
    EMERGENCY_RESPONDER = "emergency_responder"


class ZoneType(str, Enum):
    LOBBY = "lobby"
    RESIDENTIAL = "residential"
    BUSINESS = "business"
    MAINTENANCE = "maintenance"
    EMERGENCY = "emergency"
    PARKING = "parking"


class Zone(BaseModel):
    id: str
    name: str
    zone_type: ZoneType
    floor: Optional[int] = None
    restricted: bool = False


class Person(BaseModel):
    id: str
    name: str
    role: PersonRole
    guest_zone_ids: list[str] = Field(default_factory=list)


class WorkOrder(BaseModel):
    id: str
    contractor_id: str
    description: str
    allowed_zone_ids: List[str]
    active: bool = True
