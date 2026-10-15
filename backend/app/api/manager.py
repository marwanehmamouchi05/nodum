from fastapi import APIRouter, Depends, Query
from app.api.structure import service as structure_service
from app.models.manager import AnnouncementInput, MaintenanceInput, MaintenanceUpdate, VisitorInput
from app.services.manager import ManagerService

router = APIRouter(prefix="/manager", tags=["Building operations"])


def service(structure=Depends(structure_service)):
    from app.services.resident_boundary import confined
    from app.services.business_boundary import confined as business_confined
    from app.services.errors import DomainError
    if confined(structure.auth):
        raise DomainError(403, "Use your personal Resident portal")
    if business_confined(structure.auth):
        raise DomainError(403, "Use your Business workspace")
    return ManagerService(structure.auth)


@router.get("/snapshot")
def snapshot(manager=Depends(service)):
    return manager.snapshot()


@router.get("/activity")
def activity(manager=Depends(service), cursor: str | None = Query(default=None, max_length=768),
             limit: int = Query(default=100, ge=1, le=100),
             scope_id: str | None = Query(default=None, min_length=1, max_length=256)):
    from app.services.activity import ActivityService
    return ActivityService(manager.auth).public_page(cursor=cursor, limit=limit, scope_id=scope_id)


@router.post("/announcements")
def announce(payload: AnnouncementInput, manager=Depends(service)):
    return manager.create("announcement", payload)


@router.post("/maintenance")
def report(payload: MaintenanceInput, manager=Depends(service)):
    return manager.create("maintenance", payload)


@router.patch("/maintenance/{identifier}")
def update(identifier: str, payload: MaintenanceUpdate, manager=Depends(service)):
    return manager.update_maintenance(identifier, payload)


@router.post("/visitors")
def invite(payload: VisitorInput, manager=Depends(service)):
    return manager.invite(payload)


@router.post("/visitors/{identifier}/arrive")
def arrive(identifier: str, manager=Depends(service)):
    return manager.arrive(identifier)
