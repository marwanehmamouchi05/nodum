from datetime import datetime
from fastapi import APIRouter, Depends, Request
from app.api.authorization import perform_write

from app.api.dependencies import get_repository, get_scoped_repository, utc_now
from app.models.access import AccessPermission, GuestInviteInput
from app.repository import Repository
from app.services.guests import create_invitation, list_guest_permissions as get_guest_permissions


router = APIRouter(prefix="/guests", tags=["guests"])


@router.post("/invite")
def invite_guest(payload: GuestInviteInput, request: Request,
                 repository: Repository = Depends(get_scoped_repository),
                 now: datetime = Depends(utc_now)):
    return perform_write(request, repository, "/guests/invite", payload.model_dump(),
                         lambda repo: create_invitation(repo, payload, now))


@router.get("/permissions", response_model=list[AccessPermission])
def list_guest_permissions(repository: Repository = Depends(get_scoped_repository)):
    return get_guest_permissions(repository)
