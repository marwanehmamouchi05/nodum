"""Inventory and command dispatch. All actuator operations require fresh policy.

Simulators are pure state transformations, committed with command audit in one
repository transaction. No public provider selection can instantiate real hardware.
"""
from datetime import timedelta
from hashlib import sha256
import json

from pydantic import TypeAdapter

from app.integrations.building import CommandContext, ConnectorRegistry
from app.models.access import AccessDecision, AccessRequest, UTCTimestamp
from app.models.integrations import (
    ActionInput, ActionResult, ActuatorEvent, BuildingDevice, BuildingIntegration,
    Command, ConnectorKind, CredentialBinding, CredentialEvent, CredentialInput,
    DeviceInput, DeviceMapping, DeviceState, DeviceType, IntegrationInput, ScanInput,
)
from app.repository import Repository
from app.services.access_engine import evaluate_access
from app.services.emergencies import validate_operator
from app.services.errors import DomainError


KINDS = {
    DeviceType.DOOR: ConnectorKind.ACCESS, DeviceType.LOCK: ConnectorKind.ACCESS,
    DeviceType.TURNSTILE: ConnectorKind.ACCESS, DeviceType.READER: ConnectorKind.READER,
    DeviceType.ELEVATOR: ConnectorKind.ELEVATOR, DeviceType.FLOOR_CONTROLLER: ConnectorKind.ELEVATOR,
    DeviceType.LIGHT: ConnectorKind.WAYFINDING, DeviceType.SIGN: ConnectorKind.WAYFINDING,
    DeviceType.RING_DEVICE: ConnectorKind.SENSING,
}
CAPABILITIES = {
    ConnectorKind.ACCESS: {"lock", "unlock", "temporary_unlock", "status"},
    ConnectorKind.READER: {"read_credential", "status"},
    ConnectorKind.ELEVATOR: {"call_elevator", "authorize_floor", "status"},
    ConnectorKind.WAYFINDING: {"illuminate_route", "show_destination", "clear_route", "status"},
    ConnectorKind.SENSING: {"observe", "status"},
}


def fingerprint(payload):
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def utc(now):
    return TypeAdapter(UTCTimestamp).validate_python(now)


def result(status, decision, message, event_id=None):
    return ActionResult(status=status, executed=status == "executed", decision=decision,
                        message=message, actuator_event_id=event_id)


class BuildingService:
    def __init__(self, repository: Repository, registry=None):
        self.repo = repository
        self.registry = registry or ConnectorRegistry()

    def integration(self, identifier):
        record = self.repo.get_integration(identifier)
        if record is None:
            raise DomainError(404, "Integration not found")
        return record

    def device(self, identifier):
        record = self.repo.get_device(identifier)
        if record is None:
            raise DomainError(404, "Device not found")
        return record

    def register_integration(self, payload: IntegrationInput, actor_id, now):
        payload = IntegrationInput.model_validate(payload.model_dump())
        now = utc(now)
        with self.repo.transaction():
            validate_operator(self.repo, actor_id)
            if payload.provider != "simulator" or payload.kind == ConnectorKind.SENSING:
                raise DomainError(422, "Only simulator providers can be registered; no manufacturer adapter is installed")
            if self.repo.get_integration(payload.id):
                raise DomainError(409, "Integration ID already exists")
            record = BuildingIntegration(**payload.model_dump(), created_at=now, updated_at=now)
            self.repo.save_integration(record)
            return record

    def configure_integration(self, identifier, enabled, actor_id, now):
        now = utc(now)
        with self.repo.transaction():
            validate_operator(self.repo, actor_id)
            record = self.integration(identifier)
            if record.mode != "simulated":
                raise DomainError(422, "Ring connections are managed through the Ring integration")
            record.enabled = enabled
            record.updated_at = now
            self.repo.save_integration(record)
            return record

    def register_device(self, payload: DeviceInput, actor_id, now):
        payload = DeviceInput.model_validate(payload.model_dump())
        now = utc(now)
        with self.repo.transaction():
            validate_operator(self.repo, actor_id)
            integration = self.integration(payload.integration_id)
            if integration.mode != "simulated":
                raise DomainError(422, "Ring inventory must come from documented device discovery")
            if self.repo.get_device(payload.id):
                raise DomainError(409, "Device ID already exists")
            if self.repo.get_zone(payload.zone_id) is None:
                raise DomainError(404, "Physical device zone not found")
            if integration.kind != KINDS[payload.device_type] or not set(payload.capabilities) <= CAPABILITIES[integration.kind]:
                raise DomainError(422, "Device type/capabilities do not match the integration")
            if payload.target_device_id:
                target = self.device(payload.target_device_id)
                if integration.kind != ConnectorKind.READER or KINDS[target.device_type] != ConnectorKind.ACCESS:
                    raise DomainError(422, "Only readers can target access-control devices")
            record = BuildingDevice(**payload.model_dump(), provider=integration.provider, created_at=now)
            self.repo.save_device(record)
            self.repo.save_device_state(DeviceState(id=record.id, updated_at=now,
                current_floor=self.repo.get_zone(record.zone_id).floor if integration.kind == ConnectorKind.ELEVATOR else None))
            return record

    def map_device(self, identifier, zone_ids, actor_id, now):
        now = utc(now)
        with self.repo.transaction():
            validate_operator(self.repo, actor_id)
            device = self.device(identifier)
            scopes = sorted(set(zone_ids))
            if not scopes:
                raise DomainError(422, "At least one mapped zone is required")
            if KINDS[device.device_type] == ConnectorKind.ACCESS and len(scopes) != 1:
                raise DomainError(422, "An access point must protect exactly one zone")
            for zone_id in scopes:
                if self.repo.get_zone(zone_id) is None:
                    raise DomainError(404, "Mapped zone not found")
            record = DeviceMapping(id=identifier, zone_ids=scopes, updated_at=now, updated_by=actor_id)
            self.repo.save_device_mapping(record)
            return record

    def connection(self, identifier, status, actor_id, now):
        with self.repo.transaction():
            validate_operator(self.repo, actor_id)
            record = self.device(identifier)
            if not record.simulated:
                raise DomainError(422, "Only simulator connection status can be changed manually")
            record = BuildingDevice.model_validate(record.model_dump() | {"connection_status": status})
            self.repo.save_device(record)
            return self.status(identifier, now)

    def status(self, identifier, now):
        now = utc(now)
        with self.repo.transaction():
            device = self.device(identifier)
            integration = self.integration(device.integration_id)
            if not device.simulated:
                return {"device": device, "mapping": self.repo.get_device_mapping(identifier),
                        "available": integration.enabled and device.connection_status == "online",
                        "mode": "ring", "state": None}
            state = self.repo.get_device_state(identifier) or DeviceState(id=identifier, updated_at=now)
            if state.unlocked_until is not None and now >= state.unlocked_until:
                state.locked, state.unlocked_until = True, None
            if state.authorization_expires_at is not None and now >= state.authorization_expires_at:
                state.authorized_floor = state.authorized_zone_id = state.authorized_person_id = None
                state.authorization_expires_at = None
                state.route, state.destination_label = [], None
            return {"device": device, "mapping": self.repo.get_device_mapping(identifier),
                    "available": integration.enabled and device.connection_status == "online",
                    "mode": "simulated", "state": state}

    def register_credential(self, payload: CredentialInput, actor_id, now):
        payload = CredentialInput.model_validate(payload.model_dump())
        now = utc(now)
        with self.repo.transaction():
            validate_operator(self.repo, actor_id)
            if self.repo.get_person(payload.person_id) is None:
                raise DomainError(404, "Credential person not found")
            digest = self.registry.readers["simulator"].fingerprint(payload.kind.value, payload.value)
            if self.repo.get_credential(payload.id) or any(c.fingerprint == digest for c in self.repo.list_credentials()):
                raise DomainError(409, "Credential ID or simulated credential already registered")
            credential = CredentialBinding(id=payload.id, kind=payload.kind, person_id=payload.person_id,
                                           fingerprint=digest, created_at=now)
            self.repo.save_credential(credential)
            return {"id": credential.id, "kind": credential.kind, "person_id": credential.person_id, "active": True}

    def decision(self, person_id, zone_id, purpose, now, journey=None):
        person, zone = self.repo.get_person(person_id), self.repo.get_zone(zone_id)
        if person is None or zone is None:
            return AccessDecision(allowed=False, reason="Unknown person or zone")
        destination = None
        if journey:
            if (journey.person_id != person_id or zone_id not in journey.authorized_zone_ids
                    or journey.status in {"denied", "failed", "completed"}):
                return AccessDecision(allowed=False, reason="Request does not match an active authorized journey")
            destination = self.repo.get_zone(journey.destination_zone_id)
            if destination is None:
                return AccessDecision(allowed=False, reason="Journey destination no longer exists")
        return evaluate_access(AccessRequest(person_id=person_id, zone_id=zone_id, purpose=purpose, requested_at=now),
            person, zone, self.repo.list_permissions(), self.repo.list_work_orders(),
            appointments=self.repo.list_appointments(), businesses=self.repo.list_businesses(),
            emergencies=self.repo.list_emergencies(), journey_destination=destination)

    def choose_device(self, kind, zone_id, command):
        for device in self.repo.list_building_devices():
            integration = self.repo.get_integration(device.integration_id)
            mapping = self.repo.get_device_mapping(device.id)
            if (integration and integration.kind == kind and integration.enabled
                    and device.connection_status == "online" and command.value in device.capabilities
                    and mapping and zone_id in mapping.zone_ids):
                return device
        return None

    def action(self, device_id, payload: ActionInput, now):
        payload = ActionInput.model_validate(payload.model_dump())
        now = utc(now)
        digest = fingerprint({"device_id": device_id, **payload.model_dump(mode="json")})
        with self.repo.transaction():
            old = self.repo.get_actuator_event(payload.id)
            if old:
                if old.request_fingerprint != digest:
                    raise DomainError(409, "Actuator command ID conflicts with previous request")
                return result(old.status, old.decision, old.message, old.id)
            device = self.device(device_id)
            integration = self.integration(device.integration_id)
            if (not device.simulated or integration.mode != "simulated"
                    or device.provider != integration.provider or KINDS[device.device_type] != integration.kind):
                raise DomainError(403, "Only consistent simulator actuator inventory can execute commands")
            mapping = self.repo.get_device_mapping(device_id)
            journey = self.repo.get_journey(payload.journey_id) if payload.journey_id else None
            if payload.journey_id and journey is None:
                raise DomainError(404, "Journey not found")
            decision = self.decision(payload.person_id, payload.zone_id, payload.purpose, now, journey)
            if not decision.allowed:
                return result("denied", decision, "Policy denied access; no actuator command issued")
            if not mapping or payload.zone_id not in mapping.zone_ids:
                raise DomainError(403, "Device does not serve the requested zone")
            if payload.command.value not in device.capabilities or payload.command.value not in CAPABILITIES[integration.kind]:
                raise DomainError(422, "Device does not support this command")
            if integration.kind == ConnectorKind.WAYFINDING and journey is None:
                raise DomainError(403, "Wayfinding requires an authorized journey")
            # Destination must still be valid even when operating a lobby device.
            if journey:
                for zone_id in journey.authorized_zone_ids:
                    target = self.decision(payload.person_id, zone_id, payload.purpose, now, journey)
                    if not target.allowed:
                        return result("denied", target, "Journey route no longer authorized; no command issued")
            adapter = self.registry.actuator(integration.provider, integration.kind)
            if not integration.enabled or device.connection_status != "online" or adapter is None:
                return result("manual_action_required", decision, "Access verified; manual action required (connector unavailable)")
            zone = self.repo.get_zone(payload.zone_id)
            if integration.kind == ConnectorKind.ELEVATOR and zone.floor is None:
                raise DomainError(422, "Destination zone has no floor")
            expires = now + timedelta(seconds=payload.duration_seconds)
            if decision.permission:
                expires = min(expires, decision.permission.valid_until)
            context = CommandContext(command_id=payload.id, person_id=payload.person_id, zone_id=payload.zone_id,
                at=now, expires_at=expires, floor=zone.floor, route=tuple(journey.route) if journey else (),
                destination_label=self.repo.get_zone(journey.destination_zone_id).name if journey else zone.name)
            state = self.status(device_id, now)["state"]
            try:
                new_state = adapter.execute(payload.command, state, context)
                new_state = DeviceState.model_validate(new_state.model_dump())
                if new_state.id != device_id:
                    raise ValueError("Adapter returned another device")
            except Exception:
                audit = ActuatorEvent(id=payload.id, request_fingerprint=digest, device_id=device_id,
                    integration_id=integration.id, provider=integration.provider, command=payload.command,
                    person_id=payload.person_id, zone_id=payload.zone_id, journey_id=payload.journey_id,
                    at=now, executed=False, status="failed", message="Simulator command failed; no action confirmed", decision=decision)
                self.repo.save_actuator_event(audit)
                return result("failed", decision, audit.message, audit.id)
            audit = ActuatorEvent(id=payload.id, request_fingerprint=digest, device_id=device_id,
                integration_id=integration.id, provider=integration.provider, command=payload.command,
                person_id=payload.person_id, zone_id=payload.zone_id, journey_id=payload.journey_id, at=now,
                executed=True, status="executed", message=f"Simulated {payload.command.value} executed",
                decision=decision, state=new_state)
            self.repo.save_device_state(new_state)
            self.repo.save_actuator_event(audit)
            return result("executed", decision, audit.message, audit.id)

    def scan(self, payload: ScanInput, now):
        payload = ScanInput.model_validate(payload.model_dump())
        now = utc(now)
        digest = fingerprint(payload.model_dump(mode="json"))
        with self.repo.transaction():
            old = self.repo.get_credential_event(payload.id)
            if old:
                if old.request_fingerprint != digest:
                    raise DomainError(409, "Credential event ID conflicts with previous request")
                return old
            reader = self.device(payload.reader_id)
            integration = self.integration(reader.integration_id)
            mapping = self.repo.get_device_mapping(reader.id)
            if (integration.kind != ConnectorKind.READER or "read_credential" not in reader.capabilities
                    or not mapping or payload.zone_id not in mapping.zone_ids):
                raise DomainError(403, "Reader does not serve this zone")
            if not integration.enabled or reader.connection_status != "online":
                raise DomainError(409, "Simulated reader is unavailable")
            adapter = self.registry.readers.get(integration.provider)
            if adapter is None:
                raise DomainError(409, "Reader connector is unavailable")
            credential_hash = adapter.fingerprint(payload.kind.value, payload.value)
            matches = [c for c in self.repo.list_credentials() if c.active and c.fingerprint == credential_hash]
            credential = matches[0] if len(matches) == 1 else None
            denied = AccessDecision(allowed=False, reason="Credential not recognized")
            outcome = result("denied", denied, "Credential denied; no actuator command issued")
            if credential:
                action = ActionInput(id="scan-" + payload.id, person_id=credential.person_id,
                    zone_id=payload.zone_id, purpose=payload.purpose, command=Command.TEMPORARY_UNLOCK,
                    journey_id=payload.journey_id)
                if reader.target_device_id:
                    outcome = self.action(reader.target_device_id, action, now)
                else:
                    journey = self.repo.get_journey(payload.journey_id) if payload.journey_id else None
                    if payload.journey_id and not journey:
                        raise DomainError(404, "Journey not found")
                    decision = self.decision(credential.person_id, payload.zone_id, payload.purpose, now, journey)
                    outcome = result("manual_action_required" if decision.allowed else "denied", decision,
                                     "Access verified; manual door action required" if decision.allowed else "Policy denied access")
            record = CredentialEvent(id=payload.id, request_fingerprint=digest, reader_id=reader.id,
                kind=payload.kind, person_id=credential.person_id if credential else None,
                credential_id=credential.id if credential else None, zone_id=payload.zone_id, at=now, result=outcome)
            self.repo.save_credential_event(record)
            return record

    def import_ring_device(self, account_id, external_id, zone_id, principal, ring_service, now):
        """Read-only inventory from real discovery; no made-up Ring device payloads."""
        now = utc(now)
        validate_operator(self.repo, principal.person_id)
        if self.repo.get_zone(zone_id) is None:
            raise DomainError(404, "Physical device zone not found")
        devices = ring_service.discover(account_id, principal, now)
        discovered = next((d for d in devices if d.id == external_id), None)
        if discovered is None:
            raise DomainError(404, "Device was not returned by Ring discovery")
        account_key = ring_service.account_key(account_id)
        identifier = "ring-" + fingerprint([account_key, external_id])
        with self.repo.transaction():
            existing = self.repo.get_device(identifier)
            if existing:
                return existing
            integration_id = "ring-" + account_key
            if not self.repo.get_integration(integration_id):
                self.repo.save_integration(BuildingIntegration(id=integration_id, provider="ring", kind="sensing",
                    mode="ring", name="Ring sensing (linked account)", enabled=True, created_at=now, updated_at=now))
            device = BuildingDevice(id=identifier, integration_id=integration_id, provider="ring",
                device_type="ring_device", name=discovered.name or external_id, zone_id=zone_id,
                capabilities=["observe", "status"], simulated=False, external_device_id=external_id,
                external_account_key=account_key, created_at=now,
                connection_status="online" if discovered.related.get("status", {}).get("online") is True else "offline")
            self.repo.save_device(device)
            self.repo.save_device_mapping(DeviceMapping(id=identifier, zone_ids=[zone_id],
                updated_by=principal.person_id, updated_at=now))
            return device
