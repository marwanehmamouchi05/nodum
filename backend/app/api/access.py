from datetime import datetime
from fastapi import APIRouter, Depends, Request
from app.api.authorization import perform_write
from app.services.authorization import authorization_mode, scoped_decision

from app.api.dependencies import get_repository, utc_now
from app.models.access import AccessCheckInput, AccessDecision
from app.repository import Repository
from app.services.access import check_access as evaluate_stored_access


router = APIRouter(prefix="/access", tags=["access"])


@router.post("/check", response_model=AccessDecision)
def check_access(payload: AccessCheckInput, request: Request,
                 repository: Repository = Depends(get_repository),
                 now: datetime = Depends(utc_now)):
    decision = perform_write(request, repository, "/access/check", payload.model_dump(),
        lambda repo: evaluate_stored_access(repo, payload, now, legacy_role_access=authorization_mode() == "legacy_demo"))
    return scoped_decision(request.state.authorization, decision) if authorization_mode() == "scoped" else decision
