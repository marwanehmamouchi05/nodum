from datetime import datetime
from fastapi import APIRouter, Depends

from app.api.dependencies import get_repository, utc_now
from app.models.access import AccessCheckInput, AccessDecision
from app.repository import Repository
from app.services.access import check_access as evaluate_stored_access


router = APIRouter(prefix="/access", tags=["access"])


@router.post("/check", response_model=AccessDecision)
def check_access(payload: AccessCheckInput,
                 repository: Repository = Depends(get_repository),
                 now: datetime = Depends(utc_now)):
    return evaluate_stored_access(repository, payload, now)
