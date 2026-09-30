"""Simulator APIs: thin routes, no direct adapter or SQL access."""
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import Field

from app.api.dependencies import get_repository, utc_now
from app.api.ring import Principal, Service as RingServiceDependency
from app.models.access import NonEmptyString
from app.models.integrations import (
    ActionInput, CredentialInput, DeviceInput, IntegrationInput, JourneyInput,
    Record, ScanInput, TransitionInput,
)
from app.services.building import BuildingService
from app.services.journeys import JourneyService


router = APIRouter(prefix="/building", tags=["building integrations (simulators)"])


def get_building_service(repository=Depends(get_repository)):
    return BuildingService(repository)


def get_journey_service(repository=Depends(get_repository)):
    return JourneyService(repository)


Building = Annotated[BuildingService, Depends(get_building_service)]
Journeys = Annotated[JourneyService, Depends(get_journey_service)]
Now = Annotated[datetime, Depends(utc_now)]


class IntegrationRegistration(IntegrationInput):
    actor_id: NonEmptyString


class DeviceRegistration(DeviceInput):
    actor_id: NonEmptyString


class IntegrationConfiguration(Record):
    actor_id: NonEmptyString
    enabled: bool


class MappingInput(Record):
    actor_id: NonEmptyString
    zone_ids: list[NonEmptyString] = Field(min_length=1)


class ConnectionInput(Record):
    actor_id: NonEmptyString
    status: Literal["online", "offline"]


class CredentialRegistration(CredentialInput):
    actor_id: NonEmptyString


class DemoInput(Record):
    id: NonEmptyString
    actor_id: NonEmptyString
    connect_simulators: bool = True


class RingDeviceImport(Record):
    zone_id: NonEmptyString


@router.get("/integrations")
def list_integrations(service: Building):
    return service.repo.list_building_integrations()


@router.post("/integrations", status_code=201)
def register_integration(payload: IntegrationRegistration, service: Building, now: Now):
    return service.register_integration(IntegrationInput(**payload.model_dump(exclude={"actor_id"})), payload.actor_id, now)


@router.patch("/integrations/{integration_id}")
def configure_integration(integration_id: str, payload: IntegrationConfiguration, service: Building, now: Now):
    return service.configure_integration(integration_id, payload.enabled, payload.actor_id, now)


@router.get("/devices")
def list_devices(service: Building):
    return service.repo.list_building_devices()


@router.post("/devices", status_code=201)
def register_device(payload: DeviceRegistration, service: Building, now: Now):
    return service.register_device(DeviceInput(**payload.model_dump(exclude={"actor_id"})), payload.actor_id, now)


@router.put("/devices/{device_id}/mapping")
def map_device(device_id: str, payload: MappingInput, service: Building, now: Now):
    return service.map_device(device_id, payload.zone_ids, payload.actor_id, now)


@router.get("/devices/{device_id}/status")
def device_status(device_id: str, service: Building, now: Now):
    return service.status(device_id, now)


@router.patch("/devices/{device_id}/connection")
def configure_connection(device_id: str, payload: ConnectionInput, service: Building, now: Now):
    return service.connection(device_id, payload.status, payload.actor_id, now)


@router.post("/devices/{device_id}/actions")
def simulate_action(device_id: str, payload: ActionInput, service: Building, now: Now):
    return service.action(device_id, payload, now)


@router.get("/actuator-events")
def actuator_events(service: Building):
    return service.repo.list_actuator_events()


@router.post("/credentials", status_code=201)
def register_credential(payload: CredentialRegistration, service: Building, now: Now):
    return service.register_credential(CredentialInput(**payload.model_dump(exclude={"actor_id"})), payload.actor_id, now)


@router.post("/credential-scans")
def simulate_scan(payload: ScanInput, service: Building, now: Now):
    return service.scan(payload, now)


@router.get("/credential-events")
def credential_events(service: Building):
    return service.repo.list_credential_events()


@router.post("/journeys", status_code=201)
def create_journey(payload: JourneyInput, service: Journeys, now: Now):
    return service.create(payload, now)


@router.get("/journeys")
def list_journeys(service: Journeys):
    return service.repo.list_journeys()


@router.get("/journeys/{journey_id}")
def get_journey(journey_id: str, service: Journeys):
    return service.get(journey_id)


@router.post("/journeys/{journey_id}/transitions")
def confirm_transition(journey_id: str, payload: TransitionInput, service: Journeys, now: Now):
    return service.confirm_transition(journey_id, payload, now)


@router.get("/journeys/{journey_id}/transitions")
def journey_transitions(journey_id: str, service: Journeys):
    service.get(journey_id)
    return sorted((t for t in service.repo.list_journey_transitions() if t.journey_id == journey_id),
                  key=lambda t: (t.at, t.id))


@router.post("/demo/atlas-dental")
def atlas_demo(payload: DemoInput, service: Journeys, now: Now):
    return service.demo_atlas(payload.id, payload.actor_id, payload.connect_simulators, now)


@router.post("/ring/accounts/{account_id}/devices/{external_device_id}/register")
def register_ring_device(account_id: str, external_device_id: str, payload: RingDeviceImport,
                         principal: Principal, ring: RingServiceDependency, service: Building, now: Now):
    return service.import_ring_device(account_id, external_device_id, payload.zone_id, principal, ring, now)
