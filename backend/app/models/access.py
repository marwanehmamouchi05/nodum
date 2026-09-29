from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional


class AccessRequest(BaseModel):
    person_id: str
    zone_id: str
    purpose: str
    requested_at: datetime


class AccessPermission(BaseModel):
    person_id: str
    allowed_zone_ids: List[str]
    valid_from: datetime
    valid_until: datetime
    reason: str


class AccessDecision(BaseModel):
    allowed: bool
    reason: str
    permission: Optional[AccessPermission] = None