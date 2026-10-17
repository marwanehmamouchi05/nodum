from datetime import timedelta
import json
import ssl

import pytest

from conftest import NOW
from test_structure import structure  # noqa: F401
from app.integrations.mqtt_sensor import ContactIngestor, ContactSubscriber, SensorBinding
from app.models.authorization import RoleAssignment, Role, Permission as P, Principal
from app.services.authorization import AuthorizationService
from app.services.manager import ManagerService
from app.services.errors import DomainError


@pytest.fixture
def sensor(structure):
    repo = structure.repo
    repo.save_role_assignment(RoleAssignment(id='sensor-operator',user_id='admin',role=Role.MANAGER,
        scope_id='demo-org:reference:building',permissions=[P.HARDWARE_CONFIGURE,P.ACTIVITY_READ,P.HARDWARE_READ,P.LOCATIONS_READ]))
    binding = SensorBinding('demo-org:reference:building','demo-org:reference:machine-room-sensor')
    def auth():
        return AuthorizationService(repo,Principal(user_id='admin',person_id='manager-1'),NOW)
    return ContactIngestor(auth,binding), repo, auth


def payload(**changes):
    return json.dumps({'event_id':'sample-1','observed_at':NOW.isoformat(),'state':'open'} | changes).encode()


def test_record_duplicate_conflict_and_scoped_activity(sensor):
    ingest,repo,auth = sensor
    assert ingest.receive(ingest.binding.topic,payload()) == 'recorded'
    assert ingest.receive(ingest.binding.topic,payload()) == 'duplicate'
    with pytest.raises(DomainError) as error:
        ingest.receive(ingest.binding.topic,payload(state='closed'))
    assert error.value.status_code == 409
    records=[r for r in repo.list_operational_records('operation_activity') if r.get('source')=='MQTT contact observation']
    assert len(records)==1 and records[0]['simulated'] is True
    snapshot=ManagerService(auth()).snapshot()
    event=next(e for e in snapshot['activity'] if e['id']==records[0]['id'])
    assert event['what']=='sensor contact open' and event['simulated'] is True
    assert not repo.list_actuator_events()


@pytest.mark.parametrize('body', [b'bad',b'{}',b'x'*1025,b'\xff',
    b'{"event_id":"a","event_id":"b","state":"open"}',
    payload(state='unlock'),payload(observed_at='2026-01-01T00:00:00Z'),
    payload(observed_at=(NOW+timedelta(minutes=1)).isoformat()),payload(observed_at=NOW.timestamp()),payload(extra='field')])
def test_malformed_stale_and_unsupported_messages_rejected(sensor, body):
    ingest,repo,_=sensor
    with pytest.raises(DomainError):
        ingest.receive(ingest.binding.topic,body)
    assert not repo.list_operational_records('operation_activity')


@pytest.mark.parametrize('stamp', ['0001-01-01T00:00:00+14:00', '9999-12-31T23:59:59-12:00'])
def test_timestamp_normalization_range_is_validation_failure_and_collection_continues(sensor, stamp):
    ingest, repo, _ = sensor
    with pytest.raises(DomainError) as error:
        ingest.receive(ingest.binding.topic, payload(observed_at=stamp))
    assert error.value.status_code == 422
    assert not repo.list_operational_records('operation_activity')
    assert ingest.receive(ingest.binding.topic, payload()) == 'recorded'


def test_wrong_topic_retained_cross_building_and_revocation(sensor):
    ingest,repo,_=sensor
    for topic,retained in [('nodum/other',False),(ingest.binding.topic,True)]:
        with pytest.raises(DomainError):ingest.receive(topic,payload(),retained=retained)
    other=ContactIngestor(ingest.authorization_factory,SensorBinding('other-building',ingest.binding.device_id))
    with pytest.raises(DomainError):other.receive(other.binding.topic,payload())
    grant=repo.get_role_assignment('sensor-operator')
    repo.save_role_assignment(grant.model_copy(update={'active':False}))
    # Admin alone has configuration authority, but no operational ingestion permission.
    with pytest.raises(DomainError):ingest.receive(ingest.binding.topic,payload())


def test_restricted_viewer_cannot_read_sensor_activity(sensor):
    ingest,repo,_=sensor
    ingest.receive(ingest.binding.topic,payload())
    repo.save_role_assignment(RoleAssignment(id='resident-grant',user_id='resident',role=Role.RESIDENT,
        scope_id='demo-org:reference:apartment-101',permissions=[P.ACTIVITY_READ]))
    auth=AuthorizationService(repo,Principal(user_id='resident',person_id='resident-1'),NOW)
    assert not ManagerService(auth).records('operation_activity',P.ACTIVITY_READ)


def test_transport_requires_verified_tls_and_credentials_before_import(sensor):
    ingest,_,_=sensor
    with pytest.raises(ValueError):ContactSubscriber(ingest,host='broker.example')
    with pytest.raises(ValueError):ContactSubscriber(ingest,host='192.0.2.1',loopback_fixture=True)
    unverified=ssl._create_unverified_context()
    with pytest.raises(ValueError):ContactSubscriber(ingest,host='broker.example',tls_context=unverified,username='fixture',password='fixture')


def test_concurrent_deliveries_record_once(sensor):
    from concurrent.futures import ThreadPoolExecutor
    ingest,_,_=sensor
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:ingest.receive(ingest.binding.topic,payload()),range(2)))
    assert sorted(results)==['duplicate','recorded']


def test_sqlite_persistence_and_binding_rollback(sensor, request, monkeypatch):
    if request.config.getoption('--repository-backend')!='sqlite':pytest.skip('SQLite transaction/restart contract')
    from app.sqlite_repository import SQLiteRepository
    ingest,repo,auth=sensor
    original=repo.save_resource_binding
    def failing(record):
        if record.resource_type=='operation_activity':raise RuntimeError('Synthetic store fault')
        original(record)
    monkeypatch.setattr(repo,'save_resource_binding',failing)
    with pytest.raises(RuntimeError):ingest.receive(ingest.binding.topic,payload())
    assert not repo.list_operational_records('operation_activity')
    monkeypatch.setattr(repo,'save_resource_binding',original)
    assert ingest.receive(ingest.binding.topic,payload())=='recorded'
    restarted=SQLiteRepository('sqlite:///'+str(repo.database.path))
    again=ContactIngestor(lambda:AuthorizationService(restarted,auth().principal,NOW),ingest.binding)
    assert again.receive(again.binding.topic,payload())=='duplicate'
