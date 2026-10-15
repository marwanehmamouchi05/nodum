"""E2 same-floor isolation, bounded staff authority, typed AI and multi-role."""
from datetime import timedelta
import pytest
from app.models.auth import NodumUser
from app.models.building import Person, PersonRole
from app.models.authorization import Principal, Role, Permission as P, RoleAssignment, ResourceBinding
from app.models.structure import Affiliation
from app.models.business_workspace import BusinessVisitInput, BusinessMaintenanceInput, StaffCreateInput, StaffUpdateInput
from app.models.manager import AnnouncementInput, MaintenanceUpdate
from app.models.resident import ResidentMaintenanceInput
from app.services.authorization import AuthorizationService, ROLE_CEILINGS
from app.services.business_workspace import BusinessService
from app.services.manager import ManagerService
from app.services.resident import ResidentService
from app.services.agent_tools import AgentTools, confirm_action
from app.services.agent_actions import PendingActionStore
from app.services.scoped_repository import ScopedRepository
from app.services.errors import DomainError
from test_structure import structure
from test_authorization import headers
from test_resident import seed_ring
from test_agent import agent_api, tool_response, text_response
from conftest import NOW

ROOT='demo-org:reference:'


@pytest.fixture
def businesses(structure):
    repo=structure.repo; services=[]
    for identifier,role,target in [('bx',Role.BUSINESS_ADMIN,'business-x'),('by',Role.BUSINESS_ADMIN,'business-y'),('sx',Role.BUSINESS_STAFF,'business-x'),('sy',Role.BUSINESS_STAFF,'business-y')]:
        repo.save_configured_person(Person(id=identifier,name=identifier,role=PersonRole.EMPLOYEE))
        repo.save_auth_user(NodumUser(id=identifier,username=identifier,person_id=identifier,password_hash='fixture-no-login',created_at=NOW))
        repo.save_role_assignment(RoleAssignment(id=identifier+'-grant',user_id=identifier,role=role,scope_id=ROOT+target,permissions=list(ROLE_CEILINGS[role])))
        repo.save_affiliation(Affiliation(id=identifier+'-aff',user_id=identifier,role=role,target_id=ROOT+target,starts_at=NOW-timedelta(days=1),ends_at=NOW+timedelta(days=365)))
        for kind,key in [('person',identifier),('account',identifier),('affiliation',identifier+'-aff')]:
            repo.save_resource_binding(ResourceBinding(resource_type=kind,resource_id=key,scope_id=ROOT+target))
        services.append(BusinessService(AuthorizationService(repo,Principal(user_id=identifier,person_id=identifier),NOW)))
    repo.save_role_assignment(RoleAssignment(id='qa-operator',user_id='admin',role=Role.MANAGER,scope_id=ROOT+'building',permissions=list(ROLE_CEILINGS[Role.MANAGER])))
    return (*services,ManagerService(structure.auth))


def visit(service, **changes):
    return service.create_visit(BusinessVisitInput(name='Sarah',starts_at=NOW-timedelta(minutes=10),ends_at=NOW+timedelta(hours=2),**changes))


def issue(service, **changes):
    return service.create_maintenance(BusinessMaintenanceInput(title='HVAC not cooling',description='Office feels warm',**changes))


@pytest.mark.parametrize('kind', ['visitor','maintenance'])
def test_same_floor_business_list_detail_guessed_id_isolation(businesses,kind):
    x,y,_,_,_=businesses
    create=visit if kind=='visitor' else issue
    a,b=create(x),create(y)
    key='visitors' if kind=='visitor' else 'maintenance'
    assert [r['id'] for r in x.snapshot()[key]]==[a['id']]
    for identifier in [b['id'],'guessed-id']:
        with pytest.raises(DomainError) as error:
            x.detail(kind,identifier)
        assert error.value.status_code==404
    assert x.detail(kind,a['id'])==a


def test_business_snapshot_and_visitors_include_related_building_context(businesses):
    x, y, *_ = businesses
    assert x.snapshot()['building'] == 'Mixed-use reference building'
    created = visit(x)
    assert created['building'] == 'Mixed-use reference building'
    assert x.detail('visitor', created['id'])['building'] == 'Mixed-use reference building'
    assert visit(y)['destination'] == 'Business Y'


def test_staff_records_are_personal_and_admin_records_business_scoped(businesses):
    admin,_,staff,_,_=businesses
    own=visit(staff); visit(admin); issue(admin); mine=issue(staff)
    assert [r['id'] for r in staff.snapshot()['visitors']]==[own['id']]
    assert [r['id'] for r in staff.snapshot()['maintenance']]==[mine['id']]
    assert len(admin.snapshot()['visitors'])==2 and len(admin.snapshot()['maintenance'])==2
    assert staff.snapshot()['staff']==[] and staff.staff_options()==[]


def staff_payload(**changes):
    return StaffCreateInput(name='New team member',username='new-team',password='Synthetic-local-password',permissions=[P.LOCATIONS_READ,P.VISITORS_READ,P.VISITORS_INVITE],**changes)


def test_staff_creation_fixed_role_scope_and_private_account(businesses):
    x=businesses[0]
    staff=x.create_staff(staff_payload())
    grant=next(g for g in x.repo.list_role_assignments() if g.user_id==staff['id'])
    aff=next(a for a in x.repo.list_affiliations() if a.user_id==staff['id'])
    assert grant.role==Role.BUSINESS_STAFF and grant.scope_id==ROOT+'business-x'
    assert aff.role==Role.BUSINESS_STAFF and aff.target_id==ROOT+'business-x'
    assert 'password' not in str(staff) and 'password_hash' not in str(staff)
    with pytest.raises(DomainError):
        businesses[1].staff_detail(staff['id'])


@pytest.mark.parametrize('permission',[P.AUTHORIZATION_MANAGE,P.ACCOUNTS_MANAGE,P.OWNERSHIP_MANAGE,P.BUSINESS_STAFF_MANAGE,P.CAMERA_VIEW,P.HARDWARE_CONFIGURE])
def test_staff_ceiling_no_escalation(businesses,permission):
    x=businesses[0]
    payload=StaffCreateInput(name='Escalation',username='forbidden',password='Synthetic-local-password',permissions=[permission])
    with pytest.raises(DomainError) as error:
        x.create_staff(payload)
    assert error.value.status_code==403
    assert not any(u.username=='forbidden' for u in x.repo.list_auth_users())


def test_staff_delegation_intersects_administrators_current_permissions(businesses):
    x=businesses[0]
    grant=x.repo.get_role_assignment('bx-grant')
    x.repo.save_role_assignment(grant.model_copy(update={'permissions':[P.LOCATIONS_READ,P.PEOPLE_READ,P.BUSINESS_STAFF_MANAGE,P.VISITORS_READ]}))
    assert P.VISITORS_INVITE.value not in x.staff_options()
    with pytest.raises(DomainError):
        x.create_staff(staff_payload())
    result=x.create_staff(StaffCreateInput(name='Reader',username='reader',password='Synthetic-local-password',permissions=[P.LOCATIONS_READ,P.VISITORS_READ]))
    assert result['active']


@pytest.mark.parametrize('actor_index,target',[(0,'sy'),(2,'sx'),(2,'sy'),(0,'by'),(0,'bx')])
def test_staff_mutation_foreign_and_admin_protected(businesses,actor_index,target):
    with pytest.raises(DomainError):
        businesses[actor_index].update_staff(target,StaffUpdateInput(active=False,permissions=[]))


def test_staff_revocation_immediate_and_reactivation_is_membership_only(businesses):
    x,_,staff,_,_=businesses
    # Preserve an unrelated Resident role and affiliation on the same account.
    repo=x.repo
    repo.save_role_assignment(RoleAssignment(id='sx-home-grant',user_id='sx',role=Role.RESIDENT,scope_id=ROOT+'apartment-101',permissions=[P.LOCATIONS_READ]))
    repo.save_affiliation(Affiliation(id='sx-home',user_id='sx',role=Role.RESIDENT,target_id=ROOT+'apartment-101'))
    x.update_staff('sx',StaffUpdateInput(active=False,permissions=[]))
    assert repo.get_auth_user('sx').active and repo.get_role_assignment('sx-home-grant').active
    with pytest.raises(DomainError):
        staff.snapshot()
    x.update_staff('sx',StaffUpdateInput(active=True,permissions=[P.LOCATIONS_READ,P.VISITORS_READ]))
    assert staff.snapshot()['role']=='business_staff'


@pytest.mark.parametrize('change',['expired','inactive','revoked','suspended'])
def test_business_context_reauthorization(businesses,change):
    x=businesses[0]
    visit(x)
    if change in {'expired','inactive'}:
        aff=next(a for a in x.repo.list_affiliations() if a.id=='bx-aff')
        x.repo.save_affiliation(aff.model_copy(update={'ends_at':NOW} if change=='expired' else {'active':False}))
    elif change=='revoked':
        g=x.repo.get_role_assignment('bx-grant'); x.repo.save_role_assignment(g.model_copy(update={'active':False}))
    else:
        u=x.repo.get_auth_user('bx');x.repo.save_auth_user(u.model_copy(update={'active':False}))
    with pytest.raises(DomainError):
        x.snapshot()
    with pytest.raises(DomainError):
        visit(x)


@pytest.mark.parametrize('target,audience,visible',[('building','all',True),('building','business',True),('floor2','all',True),('business-x','business',True),('business-y','all',False),('building','residential',False),('floor1','all',False),('apartment-101','all',False)])
def test_business_notice_audience_and_detail_parity(businesses,target,audience,visible):
    x,*_,manager=businesses
    r=manager.create('announcement',AnnouncementInput(location_id=ROOT+target,title='Scoped notice',message='Notice',audience=audience))
    assert bool(x.notices())==visible
    if visible:
        assert x.notice_detail(r['id'])==x.notices()[0]
    else:
        with pytest.raises(DomainError):
            x.notice_detail(r['id'])


def test_public_maintenance_history_only_and_manager_api_blocked(businesses,api):
    x,*_,manager=businesses
    request=issue(x)
    manager.update_maintenance(request['id'],MaintenanceUpdate(status='in_progress',note='PRIVATE_OPERATOR_NOTE',public_message='Technician arranged'))
    assert x.detail('maintenance',request['id'])['updates'][0]['message']=='Technician arranged'
    assert 'PRIVATE_OPERATOR_NOTE' not in str(x.snapshot())
    assert api('GET','/manager/snapshot',headers=headers(x.repo,'bx'))[0]==403


def test_devices_and_generic_reads_resist_broad_building_grant(businesses):
    x,y,*_=businesses
    grant=x.repo.get_role_assignment('bx-grant');x.repo.save_role_assignment(grant.model_copy(update={'scope_id':ROOT+'building'}))
    assert [d['name'] for d in x.devices()]==['Demo Business X camera']
    scoped=ScopedRepository(x.repo,x.auth)
    assert {p.id for p in scoped.list_people()}=={'bx','sx'}
    assert not x.auth.allowed(P.HARDWARE_READ,'structure',ROOT+'business-y')
    assert not x.auth.allowed(P.LOCATIONS_READ,'structure',ROOT+'apartment-101')
    assert {s['id'] for s in x.staff()}=={'bx','sx'}


def test_ring_personal_business_mapping_isolated_and_no_access(businesses):
    x,y,*_=businesses
    before=x.repo.list_permissions(),x.repo.list_device_states()
    seed_ring(x.repo,ROOT+'business-x',NOW)
    assert x.ring() and x.ring()[0]['simulated'] and 'Identity not verified.' in x.ring()[0]['message']
    assert not y.ring() and not x.snapshot()['visitors']
    assert (x.repo.list_permissions(),x.repo.list_device_states())==before


def test_visitors_cancellation_manual_arrival_and_no_physical_access(businesses):
    x,y,*_=businesses
    before=x.repo.list_permissions()
    r=visit(x)
    with pytest.raises(DomainError):
        y.cancel(r['id'])
    assert x.cancel(r['id'])['logical_authorization']=='Revoked'
    with pytest.raises(DomainError):
        x.arrive(r['id'])
    another=visit(x); assert x.arrive(another['id'])['status']=='arrived'
    assert x.repo.list_permissions()==before


@pytest.mark.parametrize('kind',['visitors','maintenance','staff'])
def test_http_guessed_ids_lists_and_client_authority(businesses,api,kind):
    x,y,*_=businesses
    r=visit(y) if kind=='visitors' else issue(y) if kind=='maintenance' else {'id':'sy'}
    h=headers(x.repo,'bx');base='/business-workspace/'+kind
    assert api('GET',base+'/'+r['id'],headers=h)[0]==404
    assert api('GET',base+'/missing',headers=h)[0]==404
    assert r['id'] not in str(api('GET',base,headers=h)[1])
    payload={'name':'Guest','starts_at':NOW.isoformat(),'ends_at':(NOW+timedelta(hours=2)).isoformat()} if kind=='visitors' else {'title':'HVAC','description':'Not cooling'} if kind=='maintenance' else {'name':'Team','username':'newmember','password':'Synthetic-local-password','permissions':['locations.read']}
    assert api('POST',base,{**payload,'business_id':ROOT+'business-y','role':'admin'},headers=h)[0]==422
    if kind!='staff':
        assert api('POST',base,{**payload,'affiliation_id':'by-aff'},headers=h)[0]==403
    assert api('POST',base,payload,headers=h)[0]==201
    assert api('POST',base,payload,headers=h[:1])[0]==403


def test_business_staff_cannot_create_accounts_or_escalate_generic_admin(businesses,api):
    x,_,staff,*_=businesses
    h=headers(x.repo,'sx')
    assert api('POST','/business-workspace/staff',staff_payload().model_dump(mode='json'),headers=h)[0]==403
    assert api('POST','/admin/accounts',{'name':'Escalation','username':'escalation','password':'Synthetic-local-password','scope_id':ROOT+'business-x'},headers=h)[0]==403
    assert api('PUT','/authorization/assignments/escalation',{'id':'escalation','user_id':'sx','role':'business_admin','scope_id':ROOT+'business-x','permissions':['business.staff.manage']},headers=h)[0]==403


@pytest.mark.parametrize('tool,payload',[('business_invite_visitor',{'name':'Sarah','starts_at':NOW.isoformat(),'ends_at':(NOW+timedelta(hours=2)).isoformat()}),('business_report_maintenance',{'title':'HVAC','description':'Not cooling'})])
def test_ai_scoped_confirmed_actions_reauthorize(businesses,tool,payload):
    x,y,*_=businesses
    visit(y); issue(y)
    store=PendingActionStore(x.repo); tools=AgentTools(x.repo,store,'bx',lambda:NOW,x.auth)
    context=tools.run('business_context',{}).data
    assert context['visitors']==[] and context['maintenance']==[] and all(s['id'] not in {'by','sy'} for s in context['staff'])
    assert tools.run('manager_operations',{}).status=='error'
    assert tools.run(tool,{**payload,'affiliation_id':'by-aff'}).status=='error'
    proposal=tools.run(tool,payload)
    assert proposal.status=='confirmation_required' and proposal.data['arguments']['affiliation_id']=='bx-aff'
    with pytest.raises(DomainError):
        confirm_action(x.repo,store,proposal.data['id'],'by',NOW,y.auth)
    assert confirm_action(x.repo,store,proposal.data['id'],'bx',NOW,x.auth).status=='success'
    second=tools.run(tool,payload)
    g=x.repo.get_role_assignment('bx-grant');x.repo.save_role_assignment(g.model_copy(update={'permissions':[p for p in g.permissions if p!=P.AI_USE]}))
    with pytest.raises(DomainError):
        confirm_action(x.repo,store,second.data['id'],'bx',NOW,x.auth)


def test_ai_http_session_and_provider_outage(businesses,agent_api):
    from app.main import app
    from app.api.agent import get_actions
    from app.integrations.bedrock import BedrockUnavailable
    api,gateway,_=agent_api;x=businesses[0]
    store=PendingActionStore(x.repo);app.dependency_overrides[get_actions]=lambda:store
    gateway.responses.extend([tool_response('business_context',{},'context'),tool_response('business_report_maintenance',{'title':'HVAC','description':'Not cooling'},'propose'),text_response('Review before confirming')])
    h=headers(x.repo,'bx')
    assert api('POST','/agent/chat',{'message':'HVAC issue','actor_id':'by'},headers=h)[0]==403
    status,result=api('POST','/agent/chat',{'message':'HVAC issue'},headers=h)
    assert status==200
    action=result['tool_results'][-1]['data']['id']
    assert api('POST','/agent/actions/'+action+'/confirm',{'actor_id':'bx'},headers=h)[0]==200
    gateway.responses.append(BedrockUnavailable('PRIVATE_PROVIDER_ERROR'))
    status,result=api('POST','/agent/chat',{'message':'Help'},headers=h)
    assert status==503 and 'PRIVATE_PROVIDER_ERROR' not in str(result)
    assert api('GET','/business-workspace/snapshot',headers=h)[0]==200


def test_resident_business_multi_role_union_is_not_building_authority(businesses):
    x=businesses[0];repo=x.repo
    repo.save_affiliation(Affiliation(id='bx-home',user_id='bx',role=Role.RESIDENT,target_id=ROOT+'apartment-101'))
    repo.save_role_assignment(RoleAssignment(id='bx-home-grant',user_id='bx',role=Role.RESIDENT,scope_id=ROOT+'apartment-101',permissions=list(ROLE_CEILINGS[Role.RESIDENT])))
    resident=ResidentService(x.auth)
    home=resident.create_maintenance(ResidentMaintenanceInput(title='Unit leak',description='My unit'))
    office=issue(x)
    assert [r['id'] for r in resident.snapshot()['maintenance']]==[home['id']]
    assert [r['id'] for r in x.snapshot()['maintenance']]==[office['id']]
    assert not x.auth.allowed(P.LOCATIONS_READ,'structure',ROOT+'business-y')


def test_personal_access_and_activity_privacy(businesses):
    from app.models.access import AccessPermission
    x,y,staff,*_=businesses
    for service in (x,y,staff):
        node=service.context()[1]
        p=AccessPermission(id=service.auth.principal.user_id+'-access',person_id=service.auth.principal.person_id,
            allowed_zone_ids=['lobby'],valid_from=NOW-timedelta(days=1),valid_until=NOW+timedelta(days=1),reason='Explicit personal access')
        service.repo.add_guest_permission(service.repo.get_person(p.person_id),p)
        service.repo.save_resource_binding(ResourceBinding(resource_type='access_permission',resource_id=p.id,scope_id=node.scope_id))
        visit(service);issue(service)
    x.repo.save_resource_binding(ResourceBinding(resource_type='location',resource_id='lobby',scope_id=ROOT+'business-x'))
    assert len(x.access())==1 and x.access()[0]['status']=='Allowed'
    assert [p.person_id for p in ScopedRepository(x.repo,x.auth).list_permissions()]==['bx']
    assert all(r['who'] in {'bx','sx'} for r in x.activity()) and all(r['who']=='sx' for r in staff.activity())
    assert all(r['where']=='Business X' for r in x.activity())


def test_staff_reactivation_cannot_override_building_suspension(businesses):
    x=businesses[0]
    user=x.repo.get_auth_user('sx');x.repo.save_auth_user(user.model_copy(update={'active':False}))
    with pytest.raises(DomainError) as error:
        x.update_staff('sx',StaffUpdateInput(active=True,permissions=[P.LOCATIONS_READ]))
    assert error.value.status_code==409 and not x.repo.get_auth_user('sx').active


def test_future_expired_and_unbound_notices(businesses):
    x,*_,manager=businesses
    manager.create('announcement',AnnouncementInput(location_id=ROOT+'building',title='Future',message='Later',publish_at=NOW+timedelta(days=1)))
    old=ManagerService(AuthorizationService(x.repo,manager.auth.principal,NOW-timedelta(days=2)))
    r=old.create('announcement',AnnouncementInput(location_id=ROOT+'building',title='Expired',message='Archive',expires_at=NOW-timedelta(days=1)))
    assert [(n['title'],n['expired']) for n in x.notices()]==[('Expired',True)]
    x.repo.save_resource_binding(ResourceBinding(resource_type='announcement',resource_id=r['id'],scope_id=ROOT+'business-y'))
    assert x.notices()==[]


def test_multi_role_cannot_borrow_business_permissions_for_residential_scope(businesses):
    x=businesses[0]
    g=x.repo.get_role_assignment('bx-grant');x.repo.save_role_assignment(g.model_copy(update={'scope_id':ROOT+'building'}))
    x.repo.save_affiliation(Affiliation(id='residence',user_id='bx',role=Role.RESIDENT,target_id=ROOT+'apartment-102'))
    x.repo.save_role_assignment(RoleAssignment(id='residence-grant',user_id='bx',role=Role.RESIDENT,scope_id=ROOT+'apartment-101',permissions=[P.LOCATIONS_READ,P.MAINTENANCE_CREATE]))
    assert ResidentService(x.auth).snapshot()['units']==[]
    assert not x.auth.allowed(P.LOCATIONS_READ,'structure',ROOT+'apartment-102')


def test_manager_created_visit_does_not_invent_logical_authorization(businesses):
    from app.models.manager import VisitorInput
    x,*_,manager=businesses
    r=manager.invite(VisitorInput(location_id=ROOT+'business-x',name='Manager scheduled',starts_at=NOW,ends_at=NOW+timedelta(hours=1)))
    assert x.detail('visitor',r['id'])['logical_authorization']=='Not configured'
