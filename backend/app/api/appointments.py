from datetime import datetime

from fastapi import APIRouter, Depends

from app.api.dependencies import get_repository, utc_now
from app.models.business import (
    Appointment, AppointmentCreateInput, VisitorCheckInInput, VisitorCheckInResult,
)
from app.repository import Repository
from app.services import appointments


router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("", response_model=Appointment, status_code=201)
def create_appointment(payload: AppointmentCreateInput,
                       repository: Repository = Depends(get_repository),
                       now: datetime = Depends(utc_now)):
    return appointments.create_appointment(repository, payload, now)


@router.get("", response_model=list[Appointment])
def list_appointments(repository: Repository = Depends(get_repository)):
    return appointments.list_appointments(repository)


@router.get("/{appointment_id}", response_model=Appointment)
def get_appointment(appointment_id: str, repository: Repository = Depends(get_repository)):
    return appointments.get_appointment(repository, appointment_id)


@router.post("/{appointment_id}/check-in", response_model=VisitorCheckInResult)
def check_in_visitor(appointment_id: str, payload: VisitorCheckInInput,
                     repository: Repository = Depends(get_repository),
                     now: datetime = Depends(utc_now)):
    return appointments.check_in_visitor(repository, appointment_id, payload, now)
