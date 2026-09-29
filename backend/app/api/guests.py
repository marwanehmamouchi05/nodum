from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.access import AccessPermission


router = APIRouter(prefix="/guests", tags=["guests"])


class GuestInviteInput(BaseModel):
    resident_id: str
    guest_id: str
    guest_name: str
    allowed_zone_ids: list[str]
    valid_for_hours: int = 3


guest_permissions: list[AccessPermission] = []


@router.post("/invite")
def invite_guest(payload: GuestInviteInput):
    if payload.valid_for_hours <= 0:
        raise HTTPException(
            status_code=400,
            detail="valid_for_hours must be greater than 0",
        )

    now = datetime.now()

    permission = AccessPermission(
        person_id=payload.guest_id,
        allowed_zone_ids=payload.allowed_zone_ids,
        valid_from=now,
        valid_until=now + timedelta(hours=payload.valid_for_hours),
        reason=f"Guest invited by resident {payload.resident_id}",
    )

    guest_permissions.append(permission)

    return {
        "guest_id": payload.guest_id,
        "guest_name": payload.guest_name,
        "status": "approved",
        "permission": permission,
    }


@router.get("/permissions")
def list_guest_permissions():
    return guest_permissions