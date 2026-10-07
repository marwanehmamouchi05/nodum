"""E1 browser fixture; synthetic records and OS temporary SQLite DB only."""
import os
from tempfile import TemporaryDirectory
from datetime import datetime, timezone, timedelta
from cryptography.fernet import Fernet
import uvicorn
from app.sqlite_repository import SQLiteRepository
from app.models.building import Person, PersonRole
from app.models.authorization import Principal, Role, RoleAssignment, ResourceBinding
from app.models.structure import Affiliation
from app.models.manager import AnnouncementInput, MaintenanceUpdate
from app.models.resident import ResidentVisitInput, ResidentMaintenanceInput
from app.services.auth import AuthService
from app.auth_config import AuthSettings
from app.services.authorization import AuthorizationService, ROLE_CEILINGS
from app.services.structure import StructureService
from app.services.reference_building import load_reference_building
from app.services.manager import ManagerService
from app.services.resident import ResidentService

if __name__ == '__main__':
    with TemporaryDirectory(prefix='nodum-resident-qa-') as directory:
        os.environ.update(DATABASE_URL='sqlite:///'+directory+'/resident.db',NODUM_AUTHORIZATION_MODE='scoped',APP_ENV='development',
            AUTH_PUBLIC_ORIGIN='http://127.0.0.1:8768',AUTH_TRUSTED_ORIGINS='http://127.0.0.1:5176',
            CORS_ALLOWED_ORIGINS='http://127.0.0.1:5176',CORS_ALLOW_CREDENTIALS='true',
            RING_MODE='simulation',RING_SIGNING_KEY='Synthetic-QA-signing-only',RING_ENCRYPTION_KEY=Fernet.generate_key().decode())
        for key in ('AUTH_BOOTSTRAP_USERNAME','AUTH_BOOTSTRAP_PASSWORD','AUTH_BOOTSTRAP_PERSON_ID'):
            os.environ.pop(key,None)
        now = datetime.now(timezone.utc)
        repo = SQLiteRepository(os.environ['DATABASE_URL']); repo.initialize(seed_demo=True)
        def account(identifier,name):
            repo.save_configured_person(Person(id=identifier,name=name,role=PersonRole.RESIDENT))
            return AuthService(repo,AuthSettings.from_env()).create_user(identifier,'Synthetic-local-QA-only',identifier,now)
        admin = account('qa-config','Synthetic Admin')
        auth = AuthorizationService(repo,Principal(user_id=admin.id,person_id=admin.person_id),now)
        structure = StructureService(auth); structure.bootstrap_organization('qa-demo','Synthetic QA organization',demo=True)
        repo.save_role_assignment(RoleAssignment(id='qa-config-grant',user_id=admin.id,role=Role.ADMIN,scope_id='qa-demo',permissions=list(ROLE_CEILINGS[Role.ADMIN])))
        load_reference_building(structure,'qa-demo')
        prefix = 'qa-demo:reference:'
        repo.save_role_assignment(RoleAssignment(id='qa-operator-grant',user_id=admin.id,role=Role.MANAGER,scope_id=prefix+'building',permissions=list(ROLE_CEILINGS[Role.MANAGER])))
        def bind(kind,identifier,scope):
            repo.save_resource_binding(ResourceBinding(resource_type=kind,resource_id=identifier,scope_id=scope))
        people = []
        for identifier,name,unit in [('qa-resident','Ahmed Benali (Synthetic)','apartment-101'),('qa-other','Private Resident 102','apartment-102')]:
            user = account(identifier,name)
            repo.save_role_assignment(RoleAssignment(id=identifier+'-grant',user_id=user.id,role=Role.RESIDENT,scope_id=prefix+unit,permissions=list(ROLE_CEILINGS[Role.RESIDENT])))
            repo.save_affiliation(Affiliation(id=identifier+'-home',user_id=user.id,role=Role.RESIDENT,target_id=prefix+unit,ends_at=now+timedelta(days=365)))
            bind('person',user.person_id,prefix+unit); bind('affiliation',identifier+'-home',prefix+unit)
            people.append(ResidentService(AuthorizationService(repo,Principal(user_id=user.id,person_id=user.person_id),now)))
        service = ManagerService(auth)
        for target,audience,title in [('building','all','Elevator maintenance until 17:00'),('floor1','residential','Water inspection tomorrow'),('building','business','BUSINESS_PRIVATE_NOTICE'),('apartment-102','all','UNIT_102_PRIVATE_NOTICE')]:
            service.create('announcement',AnnouncementInput(location_id=prefix+target,title=title,message='Synthetic notice for the relevant audience.',audience=audience))
        for resident in people:
            resident.create_visit(ResidentVisitInput(name='Youssef (Synthetic)' if resident==people[0] else 'PRIVATE_102_VISITOR',starts_at=now+timedelta(hours=1),ends_at=now+timedelta(hours=3)))
            r = resident.create_maintenance(ResidentMaintenanceInput(title='Kitchen sink leaking' if resident==people[0] else 'PRIVATE_102_MAINTENANCE',description='Water is dripping below the sink.'))
            service.update_maintenance(r['id'],MaintenanceUpdate(status='in_progress',note='OPERATOR_PRIVATE_NOTE',public_message='The building team is arranging a repair.'))
        # Explicit synthetic personal provider mapping; never inferred in production.
        import sys
        sys.path.insert(0,os.path.dirname(__file__))
        from test_resident import seed_ring
        seed_ring(repo,prefix+'apartment-101',now)
        # Exercise real orchestrator/proposal/confirmation routes with a synthetic
        # provider. This fixture makes no AWS request and is never production wiring.
        import json
        from app.main import app
        from app.api.agent import get_gateway, get_agent_settings
        from app.integrations.bedrock import BedrockSettings, BedrockUnavailable
        from test_agent import tool_response, text_response
        class SyntheticGateway:
            def converse(self, *, messages, **kwargs):
                question = json.loads(messages[0]['content'][0]['text'])['request'].lower()
                if 'outage' in question:
                    raise BedrockUnavailable('Synthetic provider outage')
                if len(messages)==1:
                    return tool_response('resident_context',{},'context')
                if len(messages)==3:
                    if 'cousin' in question:
                        return tool_response('resident_invite_visitor',{'name':'Youssef (AI synthetic)',
                            'starts_at':(now+timedelta(days=1)).replace(hour=19,minute=0,second=0,microsecond=0).isoformat(),
                            'ends_at':(now+timedelta(days=1)).replace(hour=22,minute=0,second=0,microsecond=0).isoformat()},'propose')
                    if 'sink' in question:
                        return tool_response('resident_report_maintenance',{'title':'Sink leak (AI synthetic)','description':'Kitchen sink leaking in my unit.','priority':'normal'},'propose')
                return text_response('Synthetic provider: review your own records and confirm any proposed request below.')
        app.dependency_overrides[get_gateway] = lambda: SyntheticGateway()
        app.dependency_overrides[get_agent_settings] = lambda: BedrockSettings()
        uvicorn.run('app.main:app',host='127.0.0.1',port=8768,log_level='warning')
