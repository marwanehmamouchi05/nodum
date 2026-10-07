from datetime import datetime

from fastapi import APIRouter, Depends, Request
from app.api.authorization import perform_write

from app.api.dependencies import get_repository, get_scoped_repository, utc_now
from app.models.emergency import (
    EmergencyAssignInput, EmergencyCreateInput, EmergencyIncident, EmergencyResolveInput,
)
from app.repository import Repository
from app.services import emergencies


router = APIRouter(prefix="/emergencies", tags=["emergencies"])


@router.post("", response_model=EmergencyIncident, status_code=201)
def create_emergency(payload: EmergencyCreateInput, request: Request,
                     repository: Repository = Depends(get_scoped_repository),
                     now: datetime = Depends(utc_now)):
    return perform_write(request, repository, "/emergencies", payload.model_dump(),
                         lambda repo: emergencies.create_emergency(repo, payload, now))


@router.get("", response_model=list[EmergencyIncident])
def list_emergencies(repository: Repository = Depends(get_scoped_repository)):
    return emergencies.list_emergencies(repository)


@router.get("/active", response_model=list[EmergencyIncident])
def list_active_emergencies(repository: Repository = Depends(get_scoped_repository)):
    return emergencies.list_emergencies(repository, active_only=True)


@router.get("/{emergency_id}", response_model=EmergencyIncident)
def get_emergency(emergency_id: str, repository: Repository = Depends(get_scoped_repository)):
    return emergencies.get_emergency(repository, emergency_id)


@router.post("/{emergency_id}/resolve", response_model=EmergencyIncident)
def resolve_emergency(emergency_id: str, payload: EmergencyResolveInput, request: Request,
                      repository: Repository = Depends(get_scoped_repository),
                      now: datetime = Depends(utc_now)):
    return perform_write(request, repository, "/emergencies/{emergency_id}/resolve", payload.model_dump(),
                         lambda repo: emergencies.resolve_emergency(repo, emergency_id, payload, now),
                         {"emergency_id": emergency_id})


@router.post("/{emergency_id}/responders", response_model=EmergencyIncident)
def assign_responders(emergency_id: str, payload: EmergencyAssignInput, request: Request,
                      repository: Repository = Depends(get_scoped_repository),
                      now: datetime = Depends(utc_now)):
    return perform_write(request, repository, "/emergencies/{emergency_id}/responders", payload.model_dump(),
                         lambda repo: emergencies.assign_responders(repo, emergency_id, payload, now),
                         {"emergency_id": emergency_id})
