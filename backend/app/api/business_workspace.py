from fastapi import APIRouter, Depends
from app.api.structure import service as structure_service
from app.models.business_workspace import BusinessVisitInput, BusinessMaintenanceInput, StaffCreateInput, StaffUpdateInput
from app.services.business_workspace import BusinessService

router=APIRouter(prefix='/business-workspace',tags=['Business workspace'])


def service(structure=Depends(structure_service)):
    return BusinessService(structure.auth)


@router.get('/snapshot')
def snapshot(business=Depends(service)):
    return business.snapshot()


@router.get('/visitors')
def visitors(business=Depends(service)):
    return business.snapshot()['visitors']


@router.get('/visitors/{identifier}')
def visitor(identifier:str,business=Depends(service)):
    return business.detail('visitor',identifier)


@router.post('/visitors',status_code=201)
def invite(payload:BusinessVisitInput,business=Depends(service)):
    return business.create_visit(payload)


@router.post('/visitors/{identifier}/cancel')
def cancel(identifier:str,business=Depends(service)):
    return business.cancel(identifier)


@router.post('/visitors/{identifier}/arrive')
def arrive(identifier:str,business=Depends(service)):
    return business.arrive(identifier)


@router.get('/maintenance')
def maintenance(business=Depends(service)):
    return business.snapshot()['maintenance']


@router.get('/maintenance/{identifier}')
def request(identifier:str,business=Depends(service)):
    return business.detail('maintenance',identifier)


@router.post('/maintenance',status_code=201)
def report(payload:BusinessMaintenanceInput,business=Depends(service)):
    return business.create_maintenance(payload)


@router.get('/notices')
def notices(business=Depends(service)):
    return business.notices()


@router.get('/notices/{identifier}')
def notice(identifier:str,business=Depends(service)):
    return business.notice_detail(identifier)


@router.get('/staff')
def staff(business=Depends(service)):
    return business.staff()


@router.get('/staff/{identifier}')
def staff_detail(identifier:str,business=Depends(service)):
    return business.staff_detail(identifier)


@router.post('/staff',status_code=201)
def add_staff(payload:StaffCreateInput,business=Depends(service)):
    return business.create_staff(payload)


@router.patch('/staff/{identifier}')
def update_staff(identifier:str,payload:StaffUpdateInput,business=Depends(service)):
    return business.update_staff(identifier,payload)
