from fastapi import APIRouter, Depends
from app.api.structure import service as structure_service
from app.models.resident import ResidentVisitInput, ResidentMaintenanceInput
from app.services.resident import ResidentService

router = APIRouter(prefix="/resident", tags=["Resident portal"])


def service(structure=Depends(structure_service)):
    return ResidentService(structure.auth)


@router.get("/snapshot")
def snapshot(resident=Depends(service)):
    return resident.snapshot()


@router.get("/visitors")
def visitors(resident=Depends(service)):
    return resident.snapshot()["visitors"]


@router.get("/visitors/{identifier}")
def visitor(identifier: str, resident=Depends(service)):
    return resident.detail("visitor", identifier)


@router.post("/visitors", status_code=201)
def invite(payload: ResidentVisitInput, resident=Depends(service)):
    return resident.create_visit(payload)


@router.post("/visitors/{identifier}/cancel")
def cancel(identifier: str, resident=Depends(service)):
    return resident.cancel(identifier)


@router.get("/maintenance")
def maintenance(resident=Depends(service)):
    return resident.snapshot()["maintenance"]


@router.get("/maintenance/{identifier}")
def request(identifier: str, resident=Depends(service)):
    return resident.detail("maintenance", identifier)


@router.post("/maintenance", status_code=201)
def report(payload: ResidentMaintenanceInput, resident=Depends(service)):
    return resident.create_maintenance(payload)


@router.get("/notices")
def notices(resident=Depends(service)):
    return resident.notices()


@router.get("/notices/{identifier}")
def notice(identifier: str, resident=Depends(service)):
    return resident.notice_detail(identifier)
