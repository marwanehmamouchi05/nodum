from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.access import AccessRequest
from app.models.building import Person, PersonRole, WorkOrder, Zone, ZoneType
from app.services.access_engine import evaluate_access


router = APIRouter(prefix="/access", tags=["access"])


class AccessCheckInput(BaseModel):
    person_id: str
    zone_id: str
    purpose: str


people = {
    "contractor-1": Person(
        id="contractor-1",
        name="Ahmed",
        role=PersonRole.CONTRACTOR,
    ),
}

zones = {
    "machine-room": Zone(
        id="machine-room",
        name="Elevator Machine Room",
        zone_type=ZoneType.MAINTENANCE,
        floor=-1,
    ),
    "floor-5": Zone(
        id="floor-5",
        name="Residential Floor 5",
        zone_type=ZoneType.RESIDENTIAL,
        floor=5,
    ),
}

work_orders = [
    WorkOrder(
        id="wo-001",
        contractor_id="contractor-1",
        description="Repair Elevator 2",
        allowed_zone_ids=["machine-room"],
        active=True,
    )
]


@router.post("/check")
def check_access(payload: AccessCheckInput):
    person = people.get(payload.person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    zone = zones.get(payload.zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    request = AccessRequest(
        person_id=payload.person_id,
        zone_id=payload.zone_id,
        purpose=payload.purpose,
        requested_at=datetime.now(),
    )

    return evaluate_access(
        request=request,
        person=person,
        zone=zone,
        permissions=[],
        work_orders=work_orders,
    )