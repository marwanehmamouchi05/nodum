"""Phase B configuration contracts. No UI and no implicit legacy bridge."""
from fastapi import APIRouter, Depends
from app.api.authorization import require_scoped_context
from app.models.structure import StructureNode, Affiliation
from app.services.structure import StructureService
from app.services.authorization import authorization_mode
from app.services.errors import DomainError


router = APIRouter(prefix="/structure", tags=["Configured building"])


def service(auth=Depends(require_scoped_context)):
    if authorization_mode() != "scoped":
        raise DomainError(404, "Configured structure requires scoped mode")
    return StructureService(auth)


@router.get("/catalog")
def catalog(structure=Depends(service)):
    return structure.catalog()


@router.get("/nodes/{identifier}")
def detail(identifier: str, structure=Depends(service)):
    return structure.get(identifier)


@router.put("/nodes/{identifier}")
def save(identifier: str, record: StructureNode, structure=Depends(service)):
    if identifier != record.id:
        raise DomainError(422, "Path and record identity must match")
    return structure.save(record)


@router.get("/devices/{identifier}/context")
def device_context(identifier: str, structure=Depends(service)):
    return structure.device_context(identifier)


@router.get("/affiliations")
def affiliations(structure=Depends(service)):
    return structure.affiliations()


@router.put("/affiliations/{identifier}")
def affiliate(identifier: str, record: Affiliation, structure=Depends(service)):
    if identifier != record.id:
        raise DomainError(422, "Path and record identity must match")
    return structure.save_affiliation(record)
