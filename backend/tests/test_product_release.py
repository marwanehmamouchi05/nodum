"""Final integration gates; all repositories and credentials are synthetic."""
from unittest.mock import Mock
import pytest
from cryptography.fernet import Fernet
from conftest import NOW
from demo_product import seed_demo, PREFIX
from app.models.authorization import Principal, Permission as P
from app.services.authorization import AuthorizationService
from app.api.demo import demo_context
from app.services.manager import ManagerService
from app.services.resident import ResidentService
from app.services.business_workspace import BusinessService
from app.models.resident import ResidentVisitInput
from app.services.ring import RingService
from app.services.ring_simulation import RingSimulationService, SCENARIOS
from app.integrations.ring.config import RingSettings
from test_authorization import headers


@pytest.fixture
def product(repo, monkeypatch, request):
    monkeypatch.setenv('NODUM_AUTHORIZATION_MODE','scoped')
    monkeypatch.setenv('APP_ENV','development')
    monkeypatch.setenv('AUTH_PUBLIC_ORIGIN','http://test')
    monkeypatch.setenv('RING_MODE','simulation')
    monkeypatch.setenv('RING_SIGNING_KEY','Synthetic-release-signing-only')
    monkeypatch.setenv('RING_ENCRYPTION_KEY',Fernet.generate_key().decode())
    users=seed_demo(repo,NOW,presentation=getattr(request,"param",False))
    def auth(name):
        user=users[name]
        return AuthorizationService(repo,Principal(user_id=user.id,person_id=user.person_id),NOW)
    return repo,users,auth


def test_demo_controls_require_explicit_synthetic_authority(product,monkeypatch,api):
    repo,users,auth=product
    assert demo_context(auth('demo-manager'))['available']
    for name in ['demo-owner','demo-admin','demo-resident','demo-business','demo-staff']:
        assert demo_context(auth(name))=={'available':False}
    assert api('GET','/demo/context')[0]==401
    assert api('GET','/demo/context',headers=headers(repo,users['demo-manager'].id))[1]['available']
    monkeypatch.setenv('APP_ENV','production')
    assert demo_context(auth('demo-manager'))=={'available':False}
    monkeypatch.setenv('APP_ENV','development')
    node=repo.get_structure_node(PREFIX+'building')
    repo.save_structure_node(node.model_copy(update={'demo':False}))
    assert demo_context(auth('demo-manager'))=={'available':False}


def test_signed_ring_hero_flow_keeps_identity_policy_and_tenant_privacy(product,api):
    repo,users,auth=product
    resident=ResidentService(auth('demo-resident'))
    visitor=resident.create_visit(ResidentVisitInput(name='Cousin (Synthetic)',starts_at=NOW,ends_at=NOW.replace(hour=23)))
    before=repo.list_permissions(),repo.list_device_states(),repo.list_actuator_events()
    response=api('POST','/ring/simulation/scenarios/visitor_arrives',{},headers=headers(repo,users['demo-manager'].id))
    assert response[0]==200
    manager=ManagerService(auth('demo-manager')).snapshot()
    assert len(manager['ring'])==3 and manager['ring'][0]['simulated']
    assert len([item for item in manager['attention'] if item['title']=='Ring arrival signals'])==1
    assert any(a['what']=='Visitor arrival signal' and a['where']=='Main entrance zone' for a in manager['activity'])
    assert all('identity' in r['description'] for r in manager['ring'])
    assert resident.detail('visitor',visitor['id'])['status']=='expected'
    assert not resident.ring() and not BusinessService(auth('demo-business')).ring()
    assert (repo.list_permissions(),repo.list_device_states(),repo.list_actuator_events())==before
    assert not auth('demo-admin').allowed(P.RING_READ,'ring_event',response[1]['events'][0]['id'])
    assert api('POST','/ring/simulation/scenarios/visitor_arrives',{},headers=headers(repo,users['demo-resident'].id))[0]==403


def test_all_scenarios_remain_signal_only_in_scoped_demo(product):
    repo,_,auth=product
    simulator=RingSimulationService(RingService(repo,RingSettings.from_env(),Mock()))
    before=repo.list_permissions(),repo.list_device_states(),repo.list_actuator_events(),repo.list_operational_records('visitor')
    for name in SCENARIOS:
        result=simulator.run_scenario(name,NOW)
        assert result and all(e['is_simulation'] for e in result)
        assert all(repo.get_ring_event(e['id']) for e in result)
    assert (repo.list_permissions(),repo.list_device_states(),repo.list_actuator_events(),repo.list_operational_records('visitor'))==before


def test_membership_expiry_and_revocation_change_private_cache_generation(product):
    from datetime import timedelta
    from app.api.authorization import principal_context
    repo,_,auth=product
    resident=auth('demo-resident')
    a=next(a for a in repo.list_affiliations() if a.id=='demo-resident-resident-affiliation')
    initial=principal_context(resident)['context_version']
    assert initial==principal_context(resident)['context_version']
    repo.save_affiliation(a.model_copy(update={'ends_at':NOW+timedelta(seconds=1)}))
    revised=principal_context(resident)['context_version']
    assert initial!=revised
    resident.now=NOW+timedelta(seconds=2)
    assert principal_context(resident)['context_version']!=revised
    repo.save_affiliation(a.model_copy(update={'active':False}))
    assert principal_context(resident)['context_version']!=initial


def test_clean_v8_install_v7_upgrade_restart_and_integrity(tmp_path):
    import sqlite3
    from contextlib import closing
    from app.database import MIGRATIONS
    from app.sqlite_repository import SQLiteRepository
    assert [version for version,_ in MIGRATIONS]==list(range(1,9))
    for upgrade in (False,True):
        path=tmp_path/('upgrade.db' if upgrade else 'clean.db')
        if upgrade:
            with closing(sqlite3.connect(path)) as connection:
                connection.execute('CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)')
                for version,statements in MIGRATIONS[:7]:
                    for statement in statements:
                        connection.execute(statement)
                    connection.execute('INSERT INTO schema_migrations VALUES (?,?)',(version,NOW.isoformat()))
                connection.commit()
        for _ in range(2):
            repository=SQLiteRepository('sqlite:///'+str(path))
            repository.initialize(seed_demo=False)
            with repository.database.transaction() as connection:
                assert connection.execute('PRAGMA foreign_keys').fetchone()[0]==1
                assert connection.execute('PRAGMA foreign_key_check').fetchall()==[]
                assert connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
                assert [row[0] for row in connection.execute('SELECT version FROM schema_migrations ORDER BY version')]==list(range(1,9))
            assert not repository.list_structure_nodes() and not repository.list_auth_users()


@pytest.mark.parametrize("product", [True], indirect=True)
def test_presentation_visits_are_real_scoped_records_without_physical_access(product):
    repo, users, auth = product
    resident = ResidentService(auth("demo-resident")).snapshot()["visitors"]
    business = BusinessService(auth("demo-business")).snapshot()["visitors"]
    presenter = ResidentService(auth("demo-presenter")).snapshot()["visitors"]
    assert [v["name"] for v in resident] == ["Youssef Amrani"]
    assert {v["name"] for v in business} == {"Lina Haddad", "Omar Idrissi"}
    assert [v["name"] for v in presenter] == ["Sara Benali"]
    assert all(v["status"] == "expected" and v["physical_access"] is False for v in resident + business + presenter)
    assert not BusinessService(auth("demo-business-y")).snapshot()["visitors"]
    assert not repo.list_ring_events()
