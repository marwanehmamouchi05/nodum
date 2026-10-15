"""E1 ownership, audience, guessed-ID and confirmed-action contracts."""
from datetime import timedelta
import pytest
from app.models.auth import NodumUser
from app.models.authorization import Principal, Role, Permission as P, RoleAssignment, ResourceBinding
from app.models.building import Person, PersonRole
from app.models.structure import Affiliation
from app.models.resident import ResidentVisitInput, ResidentMaintenanceInput
from app.models.manager import AnnouncementInput, MaintenanceUpdate
from app.services.authorization import AuthorizationService, ROLE_CEILINGS
from app.services.manager import ManagerService
from app.services.resident import ResidentService
from app.services.errors import DomainError
from app.services.agent_actions import PendingActionStore
from app.services.agent_tools import AgentTools, confirm_action
from app.services.scoped_repository import ScopedRepository
from test_structure import structure
from test_authorization import headers
from test_agent import agent_api, tool_response, text_response
from conftest import NOW

ROOT = 'demo-org:reference:'


@pytest.fixture
def residents(structure):
    repo = structure.repo
    services = []
    for user, unit in [('r101', 'apartment-101'), ('r102', 'apartment-102'), ('roommate', 'apartment-101')]:
        repo.save_configured_person(Person(id=user, name=user, role=PersonRole.RESIDENT))
        repo.save_auth_user(NodumUser(id=user, username=user, person_id=user, password_hash='test-no-login', created_at=NOW))
        repo.save_role_assignment(RoleAssignment(id=user+'-grant', user_id=user, role=Role.RESIDENT,
            scope_id=ROOT+unit, permissions=list(ROLE_CEILINGS[Role.RESIDENT])))
        repo.save_affiliation(Affiliation(id=user+'-home', user_id=user, role=Role.RESIDENT,
            target_id=ROOT+unit, starts_at=NOW-timedelta(days=1), ends_at=NOW+timedelta(days=365)))
        for kind, identifier in [('person', user), ('affiliation', user+'-home')]:
            repo.save_resource_binding(ResourceBinding(resource_type=kind, resource_id=identifier, scope_id=ROOT+unit))
        services.append(ResidentService(AuthorizationService(repo, Principal(user_id=user, person_id=user), NOW)))
    repo.save_role_assignment(RoleAssignment(id='operator', user_id='admin', role=Role.MANAGER,
        scope_id=ROOT+'building', permissions=list(ROLE_CEILINGS[Role.MANAGER])))
    return (*services, ManagerService(structure.auth))


def visit(service, **kwargs):
    return service.create_visit(ResidentVisitInput(name='Own visitor', starts_at=NOW-timedelta(minutes=10),
        ends_at=NOW+timedelta(hours=2), **kwargs))


def issue(service, **kwargs):
    return service.create_maintenance(ResidentMaintenanceInput(title='Kitchen sink leaking', description='Own unit only', **kwargs))


@pytest.mark.parametrize('kind', ['visitor', 'maintenance'])
@pytest.mark.parametrize('other_index', [1, 2])
def test_personal_ownership_even_shared_unit(residents, kind, other_index):
    own, *_, manager = residents
    create = visit if kind == 'visitor' else issue
    a, b = create(own), create(residents[other_index])
    key = 'visitors' if kind == 'visitor' else 'maintenance'
    assert [r['id'] for r in own.snapshot()[key]] == [a['id']]
    assert own.detail(kind, a['id']) == a
    for identifier in (b['id'], 'guessed-missing'):
        with pytest.raises(DomainError) as error:
            own.detail(kind, identifier)
        assert error.value.status_code == 404
    assert not own.auth.allowed(P.VISITORS_READ if kind == 'visitor' else P.MAINTENANCE_READ, kind, b['id'])
    assert len(manager.snapshot()[key]) == 2


@pytest.mark.parametrize('creator', [visit, issue])
def test_destination_not_client_authority(residents, creator):
    with pytest.raises(DomainError):
        creator(residents[0], affiliation_id='r102-home')
    assert not residents[0].repo.list_operational_records('visitor' if creator == visit else 'maintenance')


def test_visitor_logical_authorization_and_safe_revocation(residents):
    own, _, _, manager = residents
    before = own.repo.list_permissions()
    created = visit(own, note='Meet at reception')
    assert created['building'] == 'Mixed-use reference building'
    assert own.snapshot()['units'][0]['building'] == 'Mixed-use reference building'
    stored = own.repo.list_operational_records('visitor')[0]
    assert stored['host_id'] == 'r101' and stored['location_id'] == ROOT+'apartment-101'
    assert stored['logical_authorization']['physical_access'] is False
    assert created['logical_authorization'] == 'Active' and created['physical_access'] is False
    assert own.cancel(created['id'])['status'] == 'cancelled'
    assert own.cancel(created['id'])['logical_authorization'] == 'Revoked'
    with pytest.raises(DomainError):
        manager.arrive(created['id'])
    assert own.repo.list_permissions() == before


def test_arrival_is_operator_confirmation_not_ring(residents):
    own, _, _, manager = residents
    record = visit(own)
    manager.arrive(record['id'])
    assert own.detail('visitor', record['id'])['status'] == 'arrived'
    with pytest.raises(DomainError):
        own.cancel(record['id'])


def test_maintenance_public_reply_private_note(residents):
    own, _, _, manager = residents
    request = issue(own)
    assert request['status'] == 'submitted'
    manager.update_maintenance(request['id'], MaintenanceUpdate(status='in_progress',
        note='PRIVATE_OPERATOR_SECRET', public_message='A plumber will visit tomorrow.'))
    safe = own.detail('maintenance', request['id'])
    assert safe['status'] == 'in_progress'
    assert safe['updates'][0]['message'] == 'A plumber will visit tomorrow.'
    assert 'PRIVATE_OPERATOR_SECRET' not in str(safe) and 'actor_id' not in str(safe)
    assert own.repo.list_operational_records('maintenance')[0]['reporter_id'] == 'r101'


@pytest.mark.parametrize('target,audience,visible', [('building','all',True), ('building','residential',True),
    ('floor1','all',True), ('apartment-101','all',True), ('apartment-102','all',False),
    ('floor2','all',False), ('building','business',False), ('business-x','all',False)])
def test_notice_audience_ancestry_and_detail_parity(residents, target, audience, visible):
    own, _, _, manager = residents
    r = manager.create('announcement', AnnouncementInput(location_id=ROOT+target, title='Notice', message='Scoped', audience=audience))
    assert bool(own.notices()) == visible
    if visible:
        assert own.notice_detail(r['id']) == own.notices()[0]
    else:
        with pytest.raises(DomainError) as error:
            own.notice_detail(r['id'])
        assert error.value.status_code == 404


def test_future_and_expired_notices(residents):
    own, _, _, manager = residents
    manager.create('announcement', AnnouncementInput(location_id=ROOT+'building', title='Future', message='Later', publish_at=NOW+timedelta(days=1)))
    old = ManagerService(AuthorizationService(own.repo, manager.auth.principal, NOW-timedelta(days=2)))
    old.create('announcement', AnnouncementInput(location_id=ROOT+'building', title='Past', message='Archived', expires_at=NOW-timedelta(days=1)))
    assert [(r['title'],r['expired']) for r in own.notices()] == [('Past',True)]


@pytest.mark.parametrize('change', ['expired', 'inactive', 'suspended', 'revoked'])
def test_affiliation_and_permission_reauthorization(residents, change):
    own = residents[0]
    r = visit(own)
    if change in {'expired','inactive'}:
        a = own.repo.list_affiliations()[0]
        a = next(a for a in own.repo.list_affiliations() if a.user_id == 'r101')
        own.repo.save_affiliation(a.model_copy(update={'ends_at':NOW} if change=='expired' else {'active':False}))
    elif change == 'suspended':
        user = own.repo.get_auth_user('r101')
        own.repo.save_auth_user(user.model_copy(update={'active':False}))
    else:
        grant = own.repo.get_role_assignment('r101-grant')
        own.repo.save_role_assignment(grant.model_copy(update={'permissions':[]}))
    assert not own.snapshot()['visitors']
    with pytest.raises(DomainError):
        visit(own)
    with pytest.raises(DomainError):
        own.detail('visitor',r['id'])


def test_broad_role_scope_does_not_leak_other_units(residents):
    own, other, roommate, _ = residents
    visit(other); issue(roommate)
    grant = own.repo.get_role_assignment('r101-grant')
    own.repo.save_role_assignment(grant.model_copy(update={'scope_id':ROOT+'building'}))
    assert not own.snapshot()['visitors'] and not own.snapshot()['maintenance']
    scoped = ScopedRepository(own.repo, own.auth)
    assert [p.id for p in scoped.list_people()] == ['r101']
    assert not own.auth.allowed(P.LOCATIONS_READ, 'structure', ROOT+'apartment-102')
    assert not own.auth.allowed(P.HARDWARE_READ, 'structure', ROOT+'lobby-camera')


@pytest.mark.parametrize('tool,payload', [('resident_invite_visitor', {'name':'Youssef','starts_at':NOW.isoformat(),'ends_at':(NOW+timedelta(hours=2)).isoformat()}),
    ('resident_report_maintenance', {'title':'Sink leaking','description':'Please repair'})])
def test_ai_typed_proposal_confirmation_and_once_only(residents, tool, payload):
    own = residents[0]
    store = PendingActionStore(own.repo)
    tools = AgentTools(own.repo, store, 'r101', lambda:NOW, own.auth)
    proposed = tools.run(tool,payload)
    assert proposed.status == 'confirmation_required'
    assert proposed.data['arguments']['affiliation_id'] == 'r101-home'
    assert not own.snapshot()['visitors'] and not own.snapshot()['maintenance']
    with pytest.raises(DomainError):
        confirm_action(own.repo,store,proposed.data['id'],'r102',NOW,residents[1].auth)
    assert confirm_action(own.repo,store,proposed.data['id'],'r101',NOW,own.auth).status == 'success'
    with pytest.raises(DomainError):
        confirm_action(own.repo,store,proposed.data['id'],'r101',NOW,own.auth)


def test_ai_context_and_revoked_confirmation(residents):
    own, other, roommate, _ = residents
    visit(other); issue(roommate)
    store = PendingActionStore(own.repo)
    tools = AgentTools(own.repo,store,'r101',lambda:NOW,own.auth)
    context = tools.run('resident_context',{}).data
    assert context['visitors'] == [] and context['maintenance'] == []
    assert tools.run('manager_operations',{}).status == 'error'
    assert not tools.run('find_people',{'query':'r102'}).data['items']
    proposed = tools.run('resident_report_maintenance',{'title':'Leak','description':'Kitchen'})
    grant = own.repo.get_role_assignment('r101-grant')
    own.repo.save_role_assignment(grant.model_copy(update={'permissions':[p for p in grant.permissions if p != P.AI_USE]}))
    with pytest.raises(DomainError):
        confirm_action(own.repo,store,proposed.data['id'],'r101',NOW,own.auth)
    assert tools.run('resident_context',{}).data['units'] == []


@pytest.mark.parametrize('kind', ['visitors', 'maintenance'])
def test_http_list_detail_and_forged_identity(residents,api,kind):
    own, other, _, _ = residents
    r = visit(other) if kind=='visitors' else issue(other)
    h = headers(own.repo,'r101')
    assert api('GET','/resident/'+kind,headers=h) == (200,[])
    assert api('GET','/resident/'+kind+'/'+r['id'],headers=h)[0] == 404
    assert api('GET','/resident/'+kind+'/missing',headers=h)[0] == 404
    payload = {'name':'Visitor','starts_at':NOW.isoformat(),'ends_at':(NOW+timedelta(hours=1)).isoformat()} if kind=='visitors' else {'title':'Leak','description':'Kitchen'}
    assert api('POST','/resident/'+kind,{**payload,'reporter_id':'r102','location_id':ROOT+'apartment-102'},headers=h)[0] == 422
    assert api('POST','/resident/'+kind,{**payload,'affiliation_id':'r102-home'},headers=h)[0] == 403
    assert api('POST','/resident/'+kind,payload,headers=h)[0] == 201
    assert api('POST','/resident/'+kind,payload,headers=h[:1])[0] == 403
    assert api('GET','/manager/snapshot',headers=h)[0] == 403


def test_personal_access_no_inferred_zone_or_control(residents):
    own, other, _, _ = residents
    from app.models.access import AccessPermission
    assert own.snapshot()['access_status'] == 'Not configured'
    for service in (own,other):
        p = AccessPermission(id=service.auth.principal.user_id+'-access', person_id=service.auth.principal.person_id,
            allowed_zone_ids=['lobby'],valid_from=NOW-timedelta(days=1),valid_until=NOW+timedelta(days=1),reason='Explicit personal authorization')
        service.repo.add_guest_permission(service.repo.get_person(p.person_id),p)
        service.repo.save_resource_binding(ResourceBinding(resource_type='access_permission', resource_id=p.id,scope_id=ROOT+'apartment-101'))
    own.repo.save_resource_binding(ResourceBinding(resource_type='location',resource_id='lobby',scope_id=ROOT+'apartment-101'))
    records = ScopedRepository(own.repo,own.auth).list_permissions()
    assert [p.person_id for p in records] == ['r101']
    data = own.access()
    assert len(data)==1 and data[0]['status']=='Allowed'
    assert 'person_id' not in str(data) and 'r102-access' not in str(data)


def seed_ring(repo, scope, now):
    from unittest.mock import Mock
    from app.services.ring import RingService, identity
    from app.services.ring_simulation import RingSimulationService
    from app.models.integrations import BuildingIntegration, BuildingDevice
    from test_ring_simulation import _make_settings
    settings = _make_settings()
    sim = RingSimulationService(RingService(repo,settings,Mock()))
    sim.run_scenario('visitor_arrives',now)
    event = next(e for e in repo.list_ring_events() if e.signal == 'doorbell')
    repo.save_integration(BuildingIntegration(id='unit-ring',name='Synthetic personal connector',kind='sensing',provider='simulator',created_at=now,updated_at=now))
    repo.save_device(BuildingDevice(id='unit-doorbell',name='Synthetic unit doorbell',integration_id='unit-ring',
        device_type='ring_device',zone_id='lobby',capabilities=['button_press'],provider='simulator',simulated=True,
        external_device_id=event.source, external_account_key=identity(event.environment,event.account_id),created_at=now))
    for kind, identifier in [('device','unit-doorbell'),('ring_event',event.id)]:
        repo.save_resource_binding(ResourceBinding(resource_type=kind,resource_id=identifier,scope_id=scope))
    return event


def test_ring_explicit_personal_mapping_no_identity_or_unlock(residents):
    own, other, _, _ = residents
    before = own.repo.list_permissions(), own.repo.list_device_states()
    seed_ring(own.repo,ROOT+'apartment-101',NOW)
    signal = own.snapshot()['ring']
    assert len(signal)==1 and signal[0]['simulated']
    assert signal[0]['message']=='Someone is at your doorbell. Identity not verified.'
    assert not other.snapshot()['ring'] and own.snapshot()['visitors']==[]
    assert (own.repo.list_permissions(),own.repo.list_device_states())==before


def test_unbound_operations_default_deny(residents):
    own = residents[0]
    r = visit(own)
    own.repo.save_resource_binding(ResourceBinding(resource_type='visitor',resource_id=r['id'],scope_id=ROOT+'apartment-102'))
    assert own.snapshot()['visitors']==[]
    with pytest.raises(DomainError):
        own.cancel(r['id'])


@pytest.mark.parametrize('tool,payload', [('resident_invite_visitor',{'name':'Confirmed guest','starts_at':NOW.isoformat(),'ends_at':(NOW+timedelta(hours=2)).isoformat()}),
    ('resident_report_maintenance',{'title':'Leak','description':'Kitchen sink'})])
def test_http_ai_uses_session_and_confirmed_personal_action(residents,agent_api,tool,payload):
    api,gateway,_ = agent_api
    own = residents[0]
    from app.main import app
    from app.api.agent import get_actions
    store = PendingActionStore(own.repo)
    app.dependency_overrides[get_actions] = lambda: store
    gateway.responses.extend([tool_response('resident_context',{},'context'),tool_response(tool,payload,'propose'),text_response('Confirm in application')])
    assert api('POST','/agent/chat',{'message':'Help with my unit','actor_id':'r102'},headers=headers(own.repo,'r101'))[0]==403
    status,response = api('POST','/agent/chat',{'message':'Help with my unit'},headers=headers(own.repo,'r101'))
    assert status==200
    proposal = response['tool_results'][-1]
    assert proposal['status']=='confirmation_required' and proposal['data']['actor_id']=='r101'
    assert api('POST','/agent/actions/'+proposal['data']['id']+'/confirm',{'actor_id':'r102'},headers=headers(own.repo,'r101'))[0]==403
    status,result = api('POST','/agent/actions/'+proposal['data']['id']+'/confirm',{'actor_id':'r101'},headers=headers(own.repo,'r101'))
    assert status==200 and result['status']=='success'


def test_bedrock_outage_does_not_break_personal_records(residents,agent_api):
    from app.integrations.bedrock import BedrockUnavailable
    api,gateway,_ = agent_api
    own = residents[0]
    issue(own)
    gateway.responses.append(BedrockUnavailable('PRIVATE_PROVIDER_DETAIL'))
    status,response = api('POST','/agent/chat',{'message':'Help me'},headers=headers(own.repo,'r101'))
    assert status==503 and response['status']=='unavailable' and 'PRIVATE_PROVIDER_DETAIL' not in str(response)
    assert len(api('GET','/resident/snapshot',headers=headers(own.repo,'r101'))[1]['maintenance'])==1
