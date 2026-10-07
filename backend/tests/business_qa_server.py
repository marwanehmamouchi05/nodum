"""Synthetic E2 browser fixture. OS temporary SQLite DB; no runtime/AWS access."""
import os
import sys
import json
from tempfile import TemporaryDirectory
from datetime import datetime, timezone, timedelta
from cryptography.fernet import Fernet
import uvicorn
from app.sqlite_repository import SQLiteRepository
from app.models.building import Person, PersonRole
from app.models.authorization import Principal, Role, RoleAssignment, ResourceBinding
from app.models.structure import Affiliation
from app.models.manager import AnnouncementInput, MaintenanceUpdate
from app.models.business_workspace import BusinessVisitInput, BusinessMaintenanceInput
from app.services.auth import AuthService
from app.auth_config import AuthSettings
from app.services.authorization import AuthorizationService, ROLE_CEILINGS
from app.services.structure import StructureService
from app.services.reference_building import load_reference_building
from app.services.manager import ManagerService
from app.services.business_workspace import BusinessService

if __name__=='__main__':
    with TemporaryDirectory(prefix='nodum-business-qa-') as directory:
        os.environ.update(DATABASE_URL='sqlite:///'+directory+'/business.db',NODUM_AUTHORIZATION_MODE='scoped',APP_ENV='development',
            AUTH_PUBLIC_ORIGIN='http://127.0.0.1:8769',AUTH_TRUSTED_ORIGINS='http://127.0.0.1:5177',
            CORS_ALLOWED_ORIGINS='http://127.0.0.1:5177',CORS_ALLOW_CREDENTIALS='true',RING_MODE='simulation',
            RING_SIGNING_KEY='Synthetic-QA-signing-only',RING_ENCRYPTION_KEY=Fernet.generate_key().decode())
        for key in ('AUTH_BOOTSTRAP_USERNAME','AUTH_BOOTSTRAP_PASSWORD','AUTH_BOOTSTRAP_PERSON_ID'):
            os.environ.pop(key,None)
        now=datetime.now(timezone.utc)
        repo=SQLiteRepository(os.environ['DATABASE_URL']);repo.initialize(seed_demo=True)
        def account(identifier,name):
            repo.save_configured_person(Person(id=identifier,name=name,role=PersonRole.EMPLOYEE))
            return AuthService(repo,AuthSettings.from_env()).create_user(identifier,'Synthetic-local-QA-only',identifier,now)
        config=account('qa-config','Synthetic building Admin')
        auth=AuthorizationService(repo,Principal(user_id=config.id,person_id=config.person_id),now)
        structure=StructureService(auth);structure.bootstrap_organization('qa-demo','Synthetic organization',demo=True)
        repo.save_role_assignment(RoleAssignment(id='config-grant',user_id=config.id,role=Role.ADMIN,scope_id='qa-demo',permissions=list(ROLE_CEILINGS[Role.ADMIN])))
        load_reference_building(structure,'qa-demo');prefix='qa-demo:reference:'
        repo.save_role_assignment(RoleAssignment(id='operator-grant',user_id=config.id,role=Role.MANAGER,scope_id=prefix+'building',permissions=list(ROLE_CEILINGS[Role.MANAGER])))
        services=[]
        for identifier,name,role,target in [('qa-business','Atlas Team (Synthetic)',Role.BUSINESS_ADMIN,'business-x'),('qa-staff','Youssef (Synthetic)',Role.BUSINESS_STAFF,'business-x'),('qa-business-y','PRIVATE_Y_ADMIN',Role.BUSINESS_ADMIN,'business-y'),('qa-staff-y','PRIVATE_Y_STAFF',Role.BUSINESS_STAFF,'business-y')]:
            user=account(identifier,name)
            repo.save_role_assignment(RoleAssignment(id=identifier+'-grant',user_id=user.id,role=role,scope_id=prefix+target,permissions=list(ROLE_CEILINGS[role])))
            affiliation=Affiliation(id=identifier+'-aff',user_id=user.id,role=role,target_id=prefix+target,ends_at=now+timedelta(days=365))
            repo.save_affiliation(affiliation)
            for kind,key in [('person',user.person_id),('account',user.id),('affiliation',affiliation.id)]:
                repo.save_resource_binding(ResourceBinding(resource_type=kind,resource_id=key,scope_id=prefix+target))
            services.append(BusinessService(AuthorizationService(repo,Principal(user_id=user.id,person_id=user.person_id),now)))
        manager=ManagerService(auth)
        for target,audience,title in [('building','all','Main entrance maintenance at 18:00'),('floor2','business','Floor 2 power inspection tomorrow'),('building','residential','PRIVATE_RESIDENTIAL_NOTICE'),('business-y','business','PRIVATE_Y_NOTICE')]:
            manager.create('announcement',AnnouncementInput(location_id=prefix+target,title=title,message='Synthetic notice for the relevant audience.',audience=audience))
        for service in services:
            private=service.context()[1].id.endswith('business-y')
            service.create_visit(BusinessVisitInput(name='PRIVATE_Y_VISITOR' if private else 'Sarah (Synthetic)' if service==services[0] else 'Staff visitor (Synthetic)',starts_at=now-timedelta(minutes=10),ends_at=now+timedelta(hours=2)))
            r=service.create_maintenance(BusinessMaintenanceInput(title='PRIVATE_Y_MAINTENANCE' if private else 'Air conditioning not cooling' if service==services[0] else 'Staff door issue',description='Synthetic issue in this business.'))
            manager.update_maintenance(r['id'],MaintenanceUpdate(status='in_progress',note='PRIVATE_OPERATOR_NOTE',public_message='A technician is being arranged for your business.'))
        old=ManagerService(AuthorizationService(repo,auth.principal,now-timedelta(days=2)))
        old.create('announcement',AnnouncementInput(location_id=prefix+'business-x',title='Completed inspection',message='Synthetic archived notice.',audience='business',expires_at=now-timedelta(days=1)))
        manager.create('announcement',AnnouncementInput(location_id=prefix+'business-x',title='FUTURE_NOTICE',message='Not published yet.',publish_at=now+timedelta(days=2),audience='business'))
        device=repo.get_structure_node(prefix+'business-x-camera')
        structure.save(device.model_copy(update={'id':prefix+'business-y-camera','name':'PRIVATE_Y_CAMERA','parent_id':prefix+'business-y','scope_id':prefix+'business-y'}))
        sys.path.insert(0,os.path.dirname(__file__))
        from test_resident import seed_ring
        seed_ring(repo,prefix+'business-x',now)
        from app.main import app
        from app.api.agent import get_gateway,get_agent_settings
        from app.integrations.bedrock import BedrockSettings,BedrockUnavailable
        from test_agent import tool_response,text_response
        class SyntheticGateway:
            def converse(self,*,messages,**kwargs):
                question=json.loads(messages[0]['content'][0]['text'])['request'].lower()
                if 'outage' in question:
                    raise BedrockUnavailable('Synthetic outage')
                if len(messages)==1:
                    return tool_response('business_context',{},'context')
                if len(messages)==3:
                    if 'sarah' in question or 'visitor' in question:
                        return tool_response('business_invite_visitor',{'name':'Sarah (AI synthetic)','starts_at':(now+timedelta(days=1)).replace(hour=10,minute=0,second=0,microsecond=0).isoformat(),'ends_at':(now+timedelta(days=1)).replace(hour=12,minute=0,second=0,microsecond=0).isoformat()},'propose')
                    if 'hvac' in question:
                        return tool_response('business_report_maintenance',{'title':'HVAC issue (AI synthetic)','description':'Air conditioning not cooling in our office.'},'propose')
                return text_response('Synthetic provider: review your authorized business information and confirm any proposed action below.')
        app.dependency_overrides[get_gateway]=lambda:SyntheticGateway()
        app.dependency_overrides[get_agent_settings]=lambda:BedrockSettings()
        uvicorn.run('app.main:app',host='127.0.0.1',port=8769,log_level='warning')
