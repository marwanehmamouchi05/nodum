"""Business projection over existing affiliations, accounts and operational records."""
from datetime import datetime
from uuid import uuid4
from app.models.authorization import Permission as P, Role, RoleAssignment
from app.models.admin import AccountInput
from app.models.structure import Affiliation
from app.models.manager import VisitorInput, MaintenanceInput
from app.services.business_boundary import contexts, business_permission, dated, BUSINESS_ROLES
from app.services.resident_boundary import physical_path
from app.services.resident import ResidentService
from app.services.manager import ManagerService
from app.services.scoped_repository import bind_created
from app.services.authorization import ROLE_CEILINGS
from app.services.account_provisioning import provision_account
from app.services.errors import DomainError


class BusinessService:
    def __init__(self, authorization, *, ai_context=False):
        self.auth, self.repo, self.ai_context = authorization, authorization.repository, ai_context

    def context(self):
        user = self.repo.get_auth_user(self.auth.principal.user_id)
        choices = [(a,n) for a,n in contexts(self.auth) if self.auth.allowed(P.LOCATIONS_READ,'structure',n.id)] if user and user.active else []
        if len({n.id for _,n in choices}) != 1:
            raise DomainError(403,'An active business assignment is required')
        return next((p for p in choices if p[0].role==Role.BUSINESS_ADMIN),choices[0])

    def allowed(self, permission, kind, identifier):
        _,node = self.context()
        return business_permission(self.auth,permission,node) and self.auth.allowed(permission,kind,identifier) and (
            not self.ai_context or business_permission(self.auth,P.AI_USE,node) and self.auth.allowed(P.AI_USE,kind,identifier))

    def target(self, affiliation_id, permission):
        a,node = self.context()
        if affiliation_id is not None and affiliation_id != a.id:
            raise DomainError(403,'This business assignment is unavailable')
        if not self.allowed(permission,'structure',node.id):
            raise DomainError(403,'This action has not been delegated for your business')
        return a,node

    def location_name(self, identifier):
        return self.context()[1].name

    building_name = ResidentService.building_name

    def homes(self):
        # Reuse safe E1 value projections, not its Resident authority checks.
        return [self.context()]

    def visit_view(self, record):
        result=ResidentService.visit_view(self,record)
        if not record.get('logical_authorization'):
            result['logical_authorization']='Not configured'
        return result
    maintenance_view = ResidentService.maintenance_view

    def records(self, kind, permission):
        a,node = self.context()
        owner = 'host_id' if kind=='visitor' else 'reporter_id'
        return [r for r in self.repo.list_operational_records(kind)
            if node.id in physical_path(self.repo,r.get('location_id'))
            and (a.role==Role.BUSINESS_ADMIN or r.get(owner)==self.auth.principal.person_id)
            and (b:=self.repo.get_resource_binding(kind,r['id'])) and node.scope_id in self.auth.ancestors(b.scope_id)
            and self.allowed(permission,kind,r['id'])]

    def detail(self, kind, identifier):
        with self.repo.transaction():
            found = next((r for r in self.records(kind,P.VISITORS_READ if kind=='visitor' else P.MAINTENANCE_READ) if r['id']==identifier),None)
            if not found:
                raise DomainError(404,'This record is unavailable')
            return self.visit_view(found) if kind=='visitor' else self.maintenance_view(found)

    def create_visit(self, payload):
        with self.repo.transaction():
            _,node = self.target(payload.affiliation_id,P.VISITORS_INVITE)
            r = ManagerService(self.auth).invite(VisitorInput(location_id=node.id,name=payload.name.strip(),starts_at=payload.starts_at,ends_at=payload.ends_at))
            r.update(note=payload.note,logical_authorization={'destination_id':node.id,'valid_from':r['starts_at'],'valid_until':r['ends_at'],'revoked_at':None,'physical_access':False})
            self.repo.save_operational_record('visitor',r)
            return self.visit_view(r)

    def create_maintenance(self, payload):
        with self.repo.transaction():
            _,node = self.target(payload.affiliation_id,P.MAINTENANCE_CREATE)
            r = ManagerService(self.auth).create('maintenance',MaintenanceInput(location_id=node.id,title=payload.title.strip(),description=payload.description.strip(),priority=payload.priority))
            return self.maintenance_view(r)

    def cancel(self, identifier):
        with self.repo.transaction():
            r = next((r for r in self.records('visitor',P.VISITORS_READ) if r['id']==identifier),None)
            if not r:
                raise DomainError(404,'This visit is unavailable')
            if not self.allowed(P.VISITORS_INVITE,'visitor',identifier):
                raise DomainError(403,'You cannot cancel this visit')
            if r.get('checked_in_at') or self.auth.now >= datetime.fromisoformat(r['ends_at']):
                raise DomainError(409,'An arrived or ended visit cannot be cancelled here')
            if not r.get('cancelled_at'):
                r['cancelled_at']=self.auth.now.isoformat()
                if r.get('logical_authorization'):
                    r['logical_authorization']['revoked_at']=r['cancelled_at']
                self.repo.save_operational_record('visitor',r); ManagerService(self.auth).journal('visitor.cancelled',r)
            return self.visit_view(r)

    def arrive(self, identifier):
        with self.repo.transaction():
            self.detail('visitor',identifier)
            if not self.allowed(P.VISITORS_CHECK_IN,'visitor',identifier):
                raise DomainError(403,'Visitor arrival confirmation is unavailable')
            return self.visit_view(ManagerService(self.auth).arrive(identifier))

    def notices(self):
        _,node = self.context()
        if not self.allowed(P.ANNOUNCEMENTS_READ,'structure',node.id):
            return []
        result=[]
        for r in self.repo.list_operational_records('announcement'):
            target=self.repo.get_structure_node(r['location_id']); binding=self.repo.get_resource_binding('announcement',r['id'])
            if not target or not binding or binding.scope_id!=target.scope_id or not self.auth.ancestors(target.scope_id):
                continue
            if target.organization_id!=node.organization_id or target.id not in physical_path(self.repo,node.id) or r['audience'] not in {'all','business'} or datetime.fromisoformat(r['publish_at'])>self.auth.now:
                continue
            result.append({'id':r['id'],'title':r['title'],'message':r['message'],'published_at':r['publish_at'],'expires_at':r.get('expires_at'),
                'expired':bool(r.get('expires_at') and datetime.fromisoformat(r['expires_at'])<=self.auth.now),'demo':r.get('demo',False)})
        return sorted(result,key=lambda r:r['published_at'],reverse=True)

    def notice_detail(self, identifier):
        r=next((r for r in self.notices() if r['id']==identifier),None)
        if not r:
            raise DomainError(404,'This notice is unavailable')
        return r

    access = ResidentService.access

    def ring(self):
        from app.services.ring import identity
        _,node=self.context(); result=[]
        for e in self.repo.list_ring_events():
            if e.signal not in {'doorbell','person'} or not self.allowed(P.RING_READ,'ring_event',e.id):
                continue
            if any(d.external_device_id==e.source and d.external_account_key==identity(e.environment,e.account_id)
                    and self.allowed(P.HARDWARE_READ,'device',d.id) and (b:=self.repo.get_resource_binding('device',d.id))
                    and node.scope_id in self.auth.ancestors(b.scope_id) for d in self.repo.list_building_devices()):
                result.append({'id':e.id,'at':e.occurred_at,'message':f'Someone is at the doorbell assigned to {node.name}. Identity not verified.',
                    'simulated':e.account_id=='simulation.playground' or e.source.startswith(('simulation:', 'playground:'))})
        return sorted(result,key=lambda r:r['at'],reverse=True)[:10]

    def devices(self):
        _,node=self.context()
        return [{'id':n.id,'name':n.name,'status':'Unverified','connection_path':n.connection_path.value,'demo':n.demo}
            for n in self.repo.list_structure_nodes() if n.kind.value=='device' and node.id in physical_path(self.repo,n.id)
            and self.allowed(P.HARDWARE_READ,'structure',n.id)]

    def staff_options(self):
        a,node=self.context()
        return sorted([p.value for p in ROLE_CEILINGS[Role.BUSINESS_STAFF] if business_permission(self.auth,p,node,admin_only=True)]) if a.role==Role.BUSINESS_ADMIN and self.allowed(P.BUSINESS_STAFF_MANAGE,'structure',node.id) else []

    def staff(self):
        a,node=self.context()
        if a.role!=Role.BUSINESS_ADMIN or not (self.allowed(P.PEOPLE_READ,'structure',node.id) or self.allowed(P.BUSINESS_STAFF_MANAGE,'structure',node.id)):
            return []
        result=[]
        for user in self.repo.list_auth_users():
            affiliation=next((f for f in self.repo.list_affiliations() if f.user_id==user.id and f.target_id==node.id and f.role in BUSINESS_ROLES),None)
            binding=self.repo.get_resource_binding('person',user.person_id)
            if not affiliation or not binding or node.scope_id not in self.auth.ancestors(binding.scope_id):
                continue
            grants=[g for g in self.repo.list_role_assignments() if g.user_id==user.id and g.role==affiliation.role and node.scope_id in self.auth.ancestors(g.scope_id)]
            active=user.active and dated(affiliation,self.auth.now) and any(g.active and (g.expires_at is None or self.auth.now<g.expires_at) for g in grants)
            result.append({'id':user.id,'name':self.repo.get_person(user.person_id).name,'username':user.username,
                'role':'Business Admin' if affiliation.role==Role.BUSINESS_ADMIN else 'Business Staff','active':active,
                'permissions':sorted({p.value for g in grants if g.active for p in g.permissions if p in ROLE_CEILINGS[Role.BUSINESS_STAFF]}),
                'can_manage':affiliation.role==Role.BUSINESS_STAFF and user.id!=self.auth.principal.user_id and self.allowed(P.BUSINESS_STAFF_MANAGE,'structure',node.id)})
        return result

    def staff_detail(self, identifier):
        r=next((r for r in self.staff() if r['id']==identifier),None)
        if not r:
            raise DomainError(404,'This staff member is unavailable')
        return r

    def validate_staff_permissions(self, permissions):
        a,node=self.target(None,P.BUSINESS_STAFF_MANAGE)
        if a.role!=Role.BUSINESS_ADMIN or not set(p.value for p in permissions)<=set(self.staff_options()):
            raise DomainError(403,'Staff permissions exceed your delegated business authority')
        return node

    def create_staff(self, payload):
        with self.repo.transaction():
            node=self.validate_staff_permissions(payload.permissions)
            account=provision_account(self.auth,AccountInput(name=payload.name,username=payload.username,password=payload.password,scope_id=node.scope_id))
            affiliation=Affiliation(id=str(uuid4()),user_id=account['id'],role=Role.BUSINESS_STAFF,target_id=node.id,starts_at=self.auth.now)
            self.repo.save_affiliation(affiliation); bind_created(self.repo,'affiliation',affiliation.id,node.scope_id)
            self.repo.save_role_assignment(RoleAssignment(id='business-staff:'+affiliation.id,user_id=account['id'],role=Role.BUSINESS_STAFF,scope_id=node.scope_id,permissions=payload.permissions))
            self.journal_staff('staff.created',account['id'],node)
            return self.staff_detail(account['id'])

    def update_staff(self, identifier, payload):
        with self.repo.transaction():
            node=self.validate_staff_permissions(payload.permissions)
            staff=self.staff_detail(identifier)
            if not staff['can_manage']:
                raise DomainError(403,'This account cannot be managed here')
            user=self.repo.get_auth_user(identifier)
            affs=[a for a in self.repo.list_affiliations() if a.user_id==identifier and a.target_id==node.id and a.role==Role.BUSINESS_STAFF]
            if payload.active and (not user.active or any((a.ends_at and self.auth.now>=a.ends_at) or (a.starts_at and self.auth.now<a.starts_at) for a in affs)):
                raise DomainError(409,'Contact building Admin to restore this expired or suspended account')
            for g in self.repo.list_role_assignments():
                if g.user_id==identifier and g.role==Role.BUSINESS_STAFF and node.scope_id in self.auth.ancestors(g.scope_id):
                    self.repo.save_role_assignment(g.model_copy(update={'active':False}))
            for a in affs:
                self.repo.save_affiliation(a.model_copy(update={'active':payload.active}))
            first=affs[0]
            self.repo.save_role_assignment(RoleAssignment(id='business-staff:'+first.id,user_id=identifier,role=Role.BUSINESS_STAFF,scope_id=node.scope_id,permissions=payload.permissions,active=payload.active))
            self.journal_staff('staff.updated' if payload.active and staff['active'] else 'staff.activated' if payload.active else 'staff.revoked',identifier,node)
            return self.staff_detail(identifier)

    def journal_staff(self, action, identifier, node):
        ManagerService(self.auth).journal(action,{'id':identifier,'scope_id':node.scope_id,'location_id':node.id})

    def activity(self):
        a,node=self.context(); result=[]
        for r in self.repo.list_operational_records('operation_activity'):
            if not self.allowed(P.ACTIVITY_READ,'operation_activity',r['id']) or node.id not in physical_path(self.repo,r.get('location_id')) or (a.role==Role.BUSINESS_STAFF and r['actor_id']!=self.auth.principal.person_id):
                continue
            actor=self.repo.get_person(r['actor_id'])
            result.append({'id':r['id'],'at':r['at'],'action':r['action'],'who':actor.name if actor else 'Business team','where':node.name})
        return sorted(result,key=lambda r:r['at'],reverse=True)[:20]

    def snapshot(self):
        with self.repo.transaction():
            a,node=self.context()
            visits=[self.visit_view(r) for r in self.records('visitor',P.VISITORS_READ)]
            for v in visits:
                v['can_arrive']=v['status']=='expected' and datetime.fromisoformat(v['starts_at'])<=self.auth.now and self.allowed(P.VISITORS_CHECK_IN,'visitor',v['id'])
            maintenance=[self.maintenance_view(r) for r in self.records('maintenance',P.MAINTENANCE_READ)]
            staff,access=self.staff(),self.access()
            permissions=[p.value for p in P if self.allowed(p,'structure',node.id)]
            return {'name':node.name,'floor':next((self.repo.get_structure_node(i).name for i in physical_path(self.repo,node.id) if self.repo.get_structure_node(i).kind.value=='floor'),None),
                'building':self.building_name(node.id),
                'affiliation_id':a.id,'role':a.role.value,'demo':node.demo,'permissions':permissions,
                'visitors':visits,'maintenance':maintenance,'notices':self.notices(),'staff':staff,'staff_options':self.staff_options(),
                'access':access,'access_status':'Review needed' if any(p['status']=='Denied' for p in access) else 'Active' if access and all(p['status']=='Allowed' for p in access) else 'Not evaluated' if access else 'Not configured',
                'devices':self.devices(),'ring':self.ring(),'activity':self.activity(),'at':self.auth.now,
                'expected_today':sum(v['status']=='expected' and datetime.fromisoformat(v['starts_at']).date()==self.auth.now.date() for v in visits),
                'open_maintenance':sum(r['status'] not in {'resolved','closed'} for r in maintenance)}
