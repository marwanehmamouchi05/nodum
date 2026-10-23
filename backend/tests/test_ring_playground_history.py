"""Official sandbox reads preserve provenance, scope, timestamps and atomicity."""
from copy import deepcopy
import json
from unittest.mock import Mock

import pytest

from app.integrations.ring.client import RingRemoteError
from app.integrations.ring.config import RingSettings
from app.models.authorization import Scope, ScopeKind
from app.services.errors import DomainError
from app.services.ring_playground import PlaygroundService, ACCOUNT, SOURCE
from conftest import NOW


@pytest.fixture
def playground(repo):
    repo.save_scope(Scope(id='sandbox-org', organization_id='sandbox-org', kind=ScopeKind.ORGANIZATION))
    client = Mock()
    devices = {'data': [{'type': 'devices', 'id': 'sandbox-device', 'attributes': {'name': 'Official sandbox camera'}}]}
    history = {'data': [{'type': 'history-events', 'id': 'official-event',
        'attributes': {'event_type': 'on_demand', 'start': int(NOW.timestamp()*1000), 'end': int(NOW.timestamp()*1000)+1000},
        'relationships': {'source': {'data': {'type': 'devices', 'id': 'sandbox-device'}}}}]}
    client.api.side_effect = lambda method, path, token: deepcopy(devices if path == '/v1/devices' else history)
    return PlaygroundService(repo, RingSettings(), client), devices, history


def test_official_history_reaches_scoped_inbox_without_fabricated_motion_or_customer_link(playground):
    service, _, _ = playground
    result = service.sync('private-token', 'sandbox-org', NOW)
    event, = service.repo.list_ring_events()
    assert event.account_id == ACCOUNT and event.source == 'playground:sandbox-device'
    assert event.event_type == 'history:on_demand' and event.signal == 'live_view'
    assert event.occurred_at == NOW
    assert service.repo.get_resource_binding('ring_event', event.id).scope_id == 'sandbox-org'
    assert json.loads(event.raw_payload)['source'] == SOURCE
    assert service.repo.list_ring_accounts() == []
    assert service.repo.list_emergencies() == []
    assert 'private-token' not in json.dumps(result) + event.raw_payload
    assert result['new_events'] == 1
    assert service.evidence('sandbox-org')['events'][0]['signal'] == 'live_view'
    assert service.evidence('another-scope')['checked_at'] is None


def test_history_resync_is_idempotent_and_cache_survives_missing_token(playground):
    service, _, _ = playground
    service.sync('token', 'sandbox-org', NOW)
    assert service.sync('token', 'sandbox-org', NOW)['new_events'] == 0
    assert len(service.repo.list_ring_events()) == 1
    with pytest.raises(DomainError) as exc:
        service.sync('', 'sandbox-org', NOW)
    assert exc.value.status_code == 503
    assert service.evidence('sandbox-org')['checked_at'] == NOW.isoformat()


@pytest.mark.parametrize('change', ['device-mismatch', 'wrong-type', 'boolean-timestamp', 'empty-id', 'non-list'])
def test_malformed_official_history_cannot_partially_write(playground, change):
    service, _, history = playground
    bad = deepcopy(history['data'][0])
    if change == 'device-mismatch': bad['relationships']['source']['data']['id'] = 'other-device'
    elif change == 'wrong-type': bad['type'] = 'webhook'
    elif change == 'boolean-timestamp': bad['attributes']['start'] = True
    elif change == 'empty-id': bad['id'] = ''
    history['data'].append(bad)
    if change == 'non-list': history['data'] = {}
    with pytest.raises(RingRemoteError): service.sync('token', 'sandbox-org', NOW)
    assert service.repo.list_ring_events() == []
    assert service.evidence('sandbox-org')['checked_at'] is None


def test_sandbox_read_cannot_overwrite_another_scope(playground):
    service, _, _ = playground
    service.sync('token', 'sandbox-org', NOW)
    with pytest.raises(DomainError) as exc:
        service.sync('token', 'another-scope', NOW)
    assert exc.value.status_code == 403
    event, = service.repo.list_ring_events()
    assert service.repo.get_resource_binding('ring_event', event.id).scope_id == 'sandbox-org'


def test_revoked_permission_at_commit_leaves_no_provider_records(playground):
    service, _, _ = playground
    def revoked(): raise DomainError(403, 'Revoked')
    with pytest.raises(DomainError): service.sync('token', 'sandbox-org', NOW, authorize=revoked)
    assert service.repo.list_ring_events() == []


def test_only_fixed_api_paths_are_called_and_remote_pagination_is_not_followed(playground):
    service, devices, history = playground
    devices['data'][0]['id'] = 'device/../escape?token=bad'
    history['data'][0]['relationships']['source']['data']['id'] = devices['data'][0]['id']
    history['links'] = {'next': 'https://attacker.example/'}
    service.sync('token', 'sandbox-org', NOW)
    paths = [call.args[1] for call in service.client.api.call_args_list]
    assert paths == ['/v1/devices', '/v1/history/devices/device%2F..%2Fescape%3Ftoken%3Dbad/events']


def test_bounded_history_does_not_import_unlimited_records(playground):
    service, _, history = playground
    template = history['data'][0]
    history['data'] = [{**deepcopy(template), 'id': str(i)} for i in range(25)]
    result = service.sync('token', 'sandbox-org', NOW)
    assert result['truncated'] is True and len(result['events']) == 20


def test_outbound_ring_requests_include_required_client_headers():
    from unittest.mock import MagicMock
    from uuid import UUID
    from app.integrations.ring.client import RingClient
    client = RingClient(RingSettings())
    response = MagicMock()
    response.__enter__.return_value.read.return_value = b'{"data":[]}'
    client.transport.open = Mock(return_value=response)
    client.api('GET', '/v1/devices', 'private-token')
    request = client.transport.open.call_args.args[0]
    headers = {key.lower(): value for key, value in request.header_items()}
    assert headers['user-agent'] == 'Nodum/1.0'
    assert headers['content-type'] == 'application/json'
    assert str(UUID(headers['hardware_id'])) == headers['hardware_id']
    assert 'private-token' not in headers['hardware_id']
