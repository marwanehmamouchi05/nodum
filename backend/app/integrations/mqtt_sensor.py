"""Optional read-only MQTT 3.1.1 contact collector. No actuator/publish interface.

Broker identities and topic ACLs must be provisioned separately. Payloads do not
establish a person's identity, physical access or general device health.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from ipaddress import ip_address
import json
import ssl
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from app.models.access import UTCTimestamp
from app.models.authorization import Permission as P
from app.models.structure import NodeKind
from app.services.errors import DomainError
from app.services.scoped_repository import bind_created


class ContactEvent(BaseModel):
    model_config = ConfigDict(extra='forbid')
    event_id: str = Field(min_length=1, max_length=128, pattern=r'^[A-Za-z0-9_-]+$')
    observed_at: UTCTimestamp
    state: Literal['open', 'closed']


@dataclass(frozen=True)
class SensorBinding:
    building_id: str
    device_id: str

    @property
    def topic(self):
        return 'nodum/v1/contact/' + quote(self.building_id, safe='') + '/' + quote(self.device_id, safe='')


def _unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError('Duplicate JSON field')
        obj[key] = value
    return obj


class ContactIngestor:
    """Authorization factory is called for every event; grants remain revocable."""
    def __init__(self, authorization_factory, binding):
        self.authorization_factory = authorization_factory
        self.binding = binding

    def validate_binding(self, auth):
        repo = auth.repository
        device = repo.get_structure_node(self.binding.device_id)
        if (not device or device.kind != NodeKind.DEVICE or device.device_type != 'sensor'
                or device.building_id != self.binding.building_id):
            raise DomainError(403, 'Sensor binding is unavailable')
        auth.require(P.HARDWARE_CONFIGURE, 'structure', device.id)
        auth.require(P.ACTIVITY_READ, 'structure', device.id)
        location = repo.get_structure_node(device.parent_id)
        if not location or location.building_id != device.building_id:
            raise DomainError(403, 'Sensor location is unavailable')
        return device, location

    def receive(self, topic, payload, *, retained=False):
        if retained or topic != self.binding.topic:
            raise DomainError(422, 'Unexpected topic or retained message')
        if not isinstance(payload, bytes) or not 0 < len(payload) <= 1024:
            raise DomainError(422, 'Invalid sensor payload size')
        try:
            data = json.loads(payload.decode('utf-8'), object_pairs_hook=_unique_object)
            if not isinstance(data, dict) or not isinstance(data.get('observed_at'), str):
                raise ValueError('Expected an explicit timestamp string')
            event = ContactEvent.model_validate(data)
        except (ValueError, UnicodeError):
            raise DomainError(422, 'Invalid contact observation') from None
        auth = self.authorization_factory()
        now = auth.now
        if not now - timedelta(minutes=5) <= event.observed_at <= now + timedelta(seconds=30):
            raise DomainError(422, 'Contact observation outside accepted time window')
        repo = auth.repository
        with repo.transaction():
            device, location = self.validate_binding(auth)
            identifier = 'mqtt-contact-' + sha256((device.id+'\0'+event.event_id).encode()).hexdigest()
            digest = sha256(event.model_dump_json().encode()).hexdigest()
            existing = repo.get_operational_record('operation_activity', identifier)
            if existing:
                if existing.get('observation_digest') != digest:
                    raise DomainError(409, 'Event identity already recorded with different content')
                return 'duplicate'
            entry = {'id':identifier, 'scope_id':device.scope_id, 'at':now.isoformat(),
                     'action':'sensor.contact.'+event.state, 'resource_id':device.id,
                     'location_id':location.id, 'actor_id':auth.principal.person_id,
                     'source':'MQTT contact observation', 'source_event_id':event.event_id,
                     'observed_at':event.observed_at.isoformat(),
                     'observation_digest':digest, 'simulated':device.demo or device.connection_path.value == 'simulation'}
            repo.save_operational_record('operation_activity', entry)
            bind_created(repo, 'operation_activity', identifier, device.scope_id)
            return 'recorded'


class ContactSubscriber:
    """Paho transport is optional; subscriptions are exact, reconnects resubscribe.

    Connection status describes this collector's subscription, never a sensor's
    physical health. Counters deliberately exclude payloads and credentials.
    """
    def __init__(self, ingestor, *, host, port=8883, tls_context=None, username=None, password=None,
                 loopback_fixture=False):
        if not 1 <= port <= 65535:
            raise ValueError('Invalid broker port')
        if loopback_fixture:
            if not ip_address(host).is_loopback:
                raise ValueError('Fixture broker must be a loopback IP')
        elif (tls_context is None or tls_context.verify_mode != ssl.CERT_REQUIRED
              or not tls_context.check_hostname or not username or not password):
            raise ValueError('Broker requires verified TLS and dedicated credentials')
        import paho.mqtt.client as mqtt
        self.ingestor, self.host, self.port = ingestor, host, port
        self.status = 'disconnected'
        self.counts = {'recorded':0, 'duplicate':0, 'rejected':0, 'failed':0}
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv311, clean_session=True)
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        if tls_context is not None:
            self.client.tls_set_context(tls_context)
        if username:
            self.client.username_pw_set(username, password)
        self.client.on_connect = self._connect
        self.client.on_subscribe = self._subscribe
        self.client.on_disconnect = self._disconnect
        self.client.on_message = self._message

    def _connect(self, client, userdata, flags, reason, properties):
        if reason.is_failure:
            self.status = 'connection_rejected'
            return
        self.status = 'subscribing'
        result, _ = client.subscribe(self.ingestor.binding.topic, qos=1)
        if result != 0:
            self.status = 'subscription_failed'

    def _subscribe(self, client, userdata, mid, reasons, properties):
        self.status = 'subscription_failed' if not reasons or any(r.is_failure for r in reasons) else 'subscribed'

    def _disconnect(self, client, userdata, flags, reason, properties):
        self.status = 'storage_failed' if self.counts['failed'] else 'disconnected'

    def _message(self, client, userdata, message):
        try:
            outcome = self.ingestor.receive(message.topic, message.payload, retained=message.retain)
            self.counts[outcome] += 1
        except DomainError:
            self.counts['rejected'] += 1
        except Exception:
            # A failing store must not silently drop an acknowledged observation.
            # Clean session means recovery is explicitly lossy; stop and expose failure.
            self.counts['failed'] += 1
            client.disconnect()
            self.status = 'storage_failed'

    def start(self):
        self.status = 'connecting'
        self.client.connect_async(self.host, self.port, keepalive=30)
        self.client.loop_start()

    def stop(self):
        self.client.disconnect()
        self.client.loop_stop()
        self.status = 'disconnected'
