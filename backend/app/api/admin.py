"""Admin endpoints use the existing session and CSRF dependency."""
from fastapi import APIRouter, Depends
from app.api.structure import service as structure_service
from app.models.admin import OrganizationInput, AccountInput, AccountStateInput, MappingInput, SetupInput, DemoInput, RingSetupInput
from app.models.structure import StructureNode, Affiliation
from app.models.authorization import RoleAssignment, Permission as P, Role
from app.services.admin import AdminService
from app.services.errors import DomainError

router = APIRouter(prefix="/admin", tags=["Administration"])


def service(structure=Depends(structure_service)):
    return AdminService(structure.auth)


@router.get("/organizations")
def organizations(admin=Depends(service)):
    return admin.organizations()


@router.post("/organizations")
def create_organization(payload: OrganizationInput, admin=Depends(service)):
    return admin.create_organization(payload)


@router.put("/nodes/{identifier}")
def node(identifier: str, payload: StructureNode, admin=Depends(service)):
    if identifier != payload.id:
        raise DomainError(422, "Path and node identity must match")
    return admin.save(payload)


@router.put("/affiliations/{identifier}")
def affiliate(identifier: str, payload: Affiliation, admin=Depends(service)):
    if identifier != payload.id:
        raise DomainError(422, "Path and affiliation identity must match")
    with admin.repo.transaction():
        result = admin.save_affiliation(payload)
        target = admin.repo.get_structure_node(result.target_id)
        admin.audit("affiliation.saved", result.id, target.scope_id)
        return result


@router.delete("/assignments/{identifier}")
def revoke(identifier: str, admin=Depends(service)):
    with admin.repo.transaction():
        record = admin.repo.get_role_assignment(identifier)
        admin.auth.revoke(identifier)
        admin.audit("role.revoked", identifier, record.scope_id)
    return {"status": "revoked"}


@router.get("/accounts")
def accounts(admin=Depends(service)):
    return admin.accounts()


@router.post("/accounts")
def create_account(payload: AccountInput, admin=Depends(service)):
    return admin.create_account(payload)


@router.patch("/accounts/{identifier}")
def state(identifier: str, payload: AccountStateInput, admin=Depends(service)):
    return admin.set_account_state(identifier, payload.active)


@router.put("/devices/{identifier}/mapping")
def mapping(identifier: str, payload: MappingInput, admin=Depends(service)):
    return admin.map_device(identifier, payload.location_id)


@router.get("/grant-options/{scope_id}")
def options(scope_id: str, admin=Depends(service)):
    return admin.grant_options(scope_id)


@router.put("/assignments/{identifier}")
def assignment(identifier: str, payload: RoleAssignment, admin=Depends(service)):
    if identifier != payload.id:
        raise DomainError(422, "Path and assignment identity must match")
    with admin.repo.transaction():
        owner_appointment = payload.role == Role.ADMIN and admin.auth.allowed_scope(P.OWNERSHIP_MANAGE, payload.scope_id)
        if not owner_appointment:
            admin.auth.require(P.ACCOUNTS_READ, "account", payload.user_id)
        admin.auth.grant(payload)
        admin.audit("role.assigned", payload.id, payload.scope_id)
    return payload


@router.get("/setup/{building_id}")
def setup(building_id: str, admin=Depends(service)):
    return admin.setup(building_id)


@router.put("/setup/{building_id}")
def save_setup(building_id: str, payload: SetupInput, admin=Depends(service)):
    return admin.setup(building_id, payload)


@router.post("/demo-building")
def demo(payload: DemoInput, admin=Depends(service)):
    return admin.demo(payload.organization_id)


@router.get("/audit")
def audit(admin=Depends(service)):
    return admin.audit_records()


@router.get("/ring")
def ring_configuration(admin=Depends(service)):
    return admin.ring_configuration()


@router.post("/ring/setup")
def prepare_ring(payload: RingSetupInput, admin=Depends(service)):
    return admin.prepare_ring(payload.building_id)
