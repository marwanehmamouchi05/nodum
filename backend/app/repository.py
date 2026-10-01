"""Repository contract and in-memory test implementation.

SQLiteRepository implements this interface for the running application.
Copies at the boundary prevent accidental mutations; the access engine has no
repository dependency.
"""
from contextlib import contextmanager
from threading import RLock
from typing import ContextManager, Iterable, Protocol

from app.models.auth import NodumUser, AuthSession, AuthThrottle
from app.models.access import AccessPermission
from app.models.agent import PendingAction
from app.models.building import Person, PersonRole, WorkOrder, Zone, ZoneType
from app.models.business import Appointment, Business
from app.models.emergency import EmergencyIncident
from app.models.ring import RingAccount, RingEvent
from app.models.integrations import (BuildingIntegration, BuildingDevice, DeviceMapping, DeviceState, CredentialBinding, CredentialEvent, ActuatorEvent, Journey, JourneyTransition)



class Repository(Protocol):
    """Service-facing contract; implementations must serialize transactions."""

    def get_integration(self, identifier: str) -> BuildingIntegration | None: ...
    def list_building_integrations(self) -> list[BuildingIntegration]: ...
    def save_integration(self, record: BuildingIntegration) -> None: ...
    def get_device(self, identifier: str) -> BuildingDevice | None: ...
    def list_building_devices(self) -> list[BuildingDevice]: ...
    def save_device(self, record: BuildingDevice) -> None: ...
    def get_device_mapping(self, identifier: str) -> DeviceMapping | None: ...
    def list_device_zone_mappings(self) -> list[DeviceMapping]: ...
    def save_device_mapping(self, record: DeviceMapping) -> None: ...
    def get_device_state(self, identifier: str) -> DeviceState | None: ...
    def list_device_states(self) -> list[DeviceState]: ...
    def save_device_state(self, record: DeviceState) -> None: ...
    def get_credential(self, identifier: str) -> CredentialBinding | None: ...
    def list_credentials(self) -> list[CredentialBinding]: ...
    def save_credential(self, record: CredentialBinding) -> None: ...
    def get_credential_event(self, identifier: str) -> CredentialEvent | None: ...
    def list_credential_events(self) -> list[CredentialEvent]: ...
    def save_credential_event(self, record: CredentialEvent) -> None: ...
    def get_actuator_event(self, identifier: str) -> ActuatorEvent | None: ...
    def list_actuator_events(self) -> list[ActuatorEvent]: ...
    def save_actuator_event(self, record: ActuatorEvent) -> None: ...
    def get_journey(self, identifier: str) -> Journey | None: ...
    def list_journeys(self) -> list[Journey]: ...
    def save_journey(self, record: Journey) -> None: ...
    def get_journey_transition(self, identifier: str) -> JourneyTransition | None: ...
    def list_journey_transitions(self) -> list[JourneyTransition]: ...
    def save_journey_transition(self, record: JourneyTransition) -> None: ...

    def get_auth_user(self, identifier: str) -> NodumUser | None: ...
    def list_auth_users(self) -> list[NodumUser]: ...
    def save_auth_user(self, record: NodumUser) -> None: ...
    def delete_auth_user(self, identifier: str) -> None: ...
    def get_auth_session(self, identifier: str) -> AuthSession | None: ...
    def list_auth_sessions(self) -> list[AuthSession]: ...
    def save_auth_session(self, record: AuthSession) -> None: ...
    def delete_auth_session(self, identifier: str) -> None: ...
    def get_auth_throttle(self, identifier: str) -> AuthThrottle | None: ...
    def list_auth_throttles(self) -> list[AuthThrottle]: ...
    def save_auth_throttle(self, record: AuthThrottle) -> None: ...
    def delete_auth_throttle(self, identifier: str) -> None: ...

    def ring_receipt_transaction(self) -> ContextManager["Repository"]: ...
    def find_ring_event(self, environment: str, account_id: str, request_id: str, event_id: str) -> RingEvent | None: ...
    def get_ring_account(self, account_key: str) -> RingAccount | None: ...
    def list_ring_accounts(self) -> list[RingAccount]: ...
    def save_ring_account(self, account: RingAccount) -> None: ...
    def get_ring_event(self, event_key: str) -> RingEvent | None: ...
    def list_ring_events(self) -> list[RingEvent]: ...
    def save_ring_event(self, event: RingEvent) -> None: ...

    def transaction(self) -> ContextManager["Repository"]: ...
    def get_person(self, person_id: str) -> Person | None: ...
    def list_people(self) -> list[Person]: ...
    def get_zone(self, zone_id: str) -> Zone | None: ...
    def list_zones(self) -> list[Zone]: ...
    def list_permissions(self) -> list[AccessPermission]: ...
    def list_work_orders(self) -> list[WorkOrder]: ...
    def add_guest_permission(self, guest: Person, permission: AccessPermission) -> None: ...
    def get_business(self, business_id: str) -> Business | None: ...
    def list_businesses(self) -> list[Business]: ...
    def get_appointment(self, appointment_id: str) -> Appointment | None: ...
    def list_appointments(self) -> list[Appointment]: ...
    def add_appointment(self, appointment: Appointment) -> None: ...
    def record_check_in(self, visitor: Person, appointment: Appointment,
                        permission: AccessPermission) -> None: ...
    def get_emergency(self, emergency_id: str) -> EmergencyIncident | None: ...
    def list_emergencies(self) -> list[EmergencyIncident]: ...
    def add_emergency(self, incident: EmergencyIncident) -> None: ...
    def update_emergency(self, incident: EmergencyIncident) -> None: ...
    def get_pending_action(self, action_id: str) -> PendingAction | None: ...
    def list_pending_actions(self) -> list[PendingAction]: ...
    def add_pending_action(self, action: PendingAction) -> None: ...
    def delete_pending_action(self, action_id: str) -> None: ...


class InMemoryRepository:
    def get_auth_user(self, identifier):
        with self._lock:
            record = self._auth_users.get(identifier)
            return record.model_copy(deep=True) if record else None

    def list_auth_users(self):
        with self._lock:
            return [record.model_copy(deep=True) for record in self._auth_users.values()]

    def save_auth_user(self, record):
        with self._lock:
            self._auth_users[record.id] = NodumUser.model_validate(record.model_dump())

    def delete_auth_user(self, identifier):
        with self._lock:
            self._auth_users.pop(identifier, None)

    def get_auth_session(self, identifier):
        with self._lock:
            record = self._auth_sessions.get(identifier)
            return record.model_copy(deep=True) if record else None

    def list_auth_sessions(self):
        with self._lock:
            return [record.model_copy(deep=True) for record in self._auth_sessions.values()]

    def save_auth_session(self, record):
        with self._lock:
            self._auth_sessions[record.id] = AuthSession.model_validate(record.model_dump())

    def delete_auth_session(self, identifier):
        with self._lock:
            self._auth_sessions.pop(identifier, None)

    def get_auth_throttle(self, identifier):
        with self._lock:
            record = self._auth_throttles.get(identifier)
            return record.model_copy(deep=True) if record else None

    def list_auth_throttles(self):
        with self._lock:
            return [record.model_copy(deep=True) for record in self._auth_throttles.values()]

    def save_auth_throttle(self, record):
        with self._lock:
            self._auth_throttles[record.id] = AuthThrottle.model_validate(record.model_dump())

    def delete_auth_throttle(self, identifier):
        with self._lock:
            self._auth_throttles.pop(identifier, None)

    def __init__(
        self,
        people: Iterable[Person] = (),
        zones: Iterable[Zone] = (),
        permissions: Iterable[AccessPermission] = (),
        work_orders: Iterable[WorkOrder] = (),
        businesses: Iterable[Business] = (),
        appointments: Iterable[Appointment] = (),
        emergencies: Iterable[EmergencyIncident] = (),
    ):
        self._auth_users = {}
        self._auth_sessions = {}
        self._auth_throttles = {}
        self._lock = RLock()
        self._people = {p.id: p.model_copy(deep=True) for p in people}
        self._zones = {z.id: z.model_copy(deep=True) for z in zones}
        self._permissions = [p.model_copy(deep=True) for p in permissions]
        self._work_orders = [w.model_copy(deep=True) for w in work_orders]
        self._businesses = {b.id: b.model_copy(deep=True) for b in businesses}
        self._appointments = {a.id: a.model_copy(deep=True) for a in appointments}
        self._emergencies = {e.emergency_id: e.model_copy(deep=True) for e in emergencies}
        self._pending_actions: dict[str, PendingAction] = {}
        self._ring_accounts: dict[str, RingAccount] = {}
        self._ring_events: dict[str, RingEvent] = {}
        self._building_integrations: dict[str, BuildingIntegration] = {}
        self._building_devices: dict[str, BuildingDevice] = {}
        self._device_zone_mappings: dict[str, DeviceMapping] = {}
        self._device_states: dict[str, DeviceState] = {}
        self._credentials: dict[str, CredentialBinding] = {}
        self._credential_events: dict[str, CredentialEvent] = {}
        self._actuator_events: dict[str, ActuatorEvent] = {}
        self._journeys: dict[str, Journey] = {}
        self._journey_transitions: dict[str, JourneyTransition] = {}


    @contextmanager
    def transaction(self):
        """Mutual exclusion, not rollback: validate before writing."""
        with self._lock:
            yield self

    def get_person(self, person_id: str) -> Person | None:
        with self._lock:
            person = self._people.get(person_id)
            return person.model_copy(deep=True) if person else None

    def list_people(self) -> list[Person]:
        with self._lock:
            return [self._people[key].model_copy(deep=True) for key in sorted(self._people)]

    def list_zones(self) -> list[Zone]:
        with self._lock:
            return [self._zones[key].model_copy(deep=True) for key in sorted(self._zones)]

    def get_zone(self, zone_id: str) -> Zone | None:
        with self._lock:
            zone = self._zones.get(zone_id)
            return zone.model_copy(deep=True) if zone else None

    def list_permissions(self) -> list[AccessPermission]:
        with self._lock:
            return [p.model_copy(deep=True) for p in self._permissions]

    def list_work_orders(self) -> list[WorkOrder]:
        with self._lock:
            return [w.model_copy(deep=True) for w in self._work_orders]

    def get_business(self, business_id: str) -> Business | None:
        with self._lock:
            business = self._businesses.get(business_id)
            return business.model_copy(deep=True) if business else None

    def list_businesses(self) -> list[Business]:
        with self._lock:
            return [self._businesses[key].model_copy(deep=True)
                    for key in sorted(self._businesses)]

    def get_appointment(self, appointment_id: str) -> Appointment | None:
        with self._lock:
            appointment = self._appointments.get(appointment_id)
            return appointment.model_copy(deep=True) if appointment else None

    def list_appointments(self) -> list[Appointment]:
        with self._lock:
            return [self._appointments[key].model_copy(deep=True)
                    for key in sorted(self._appointments)]

    def add_appointment(self, appointment: Appointment) -> None:
        with self._lock:
            if appointment.id in self._appointments:
                raise ValueError("Appointment ID already exists")
            self._appointments[appointment.id] = appointment.model_copy(deep=True)

    def record_check_in(self, visitor: Person, appointment: Appointment,
                        permission: AccessPermission) -> None:
        """Service validates under transaction; all copies precede writes."""
        with self._lock:
            visitor_copy = visitor.model_copy(deep=True)
            appointment_copy = appointment.model_copy(deep=True)
            permission_copy = permission.model_copy(deep=True)
            self._people[visitor.id] = visitor_copy
            self._appointments[appointment.id] = appointment_copy
            self._permissions.append(permission_copy)

    def get_emergency(self, emergency_id: str) -> EmergencyIncident | None:
        with self._lock:
            incident = self._emergencies.get(emergency_id)
            return incident.model_copy(deep=True) if incident else None

    def list_emergencies(self) -> list[EmergencyIncident]:
        with self._lock:
            return [self._emergencies[key].model_copy(deep=True)
                    for key in sorted(self._emergencies)]

    def add_emergency(self, incident: EmergencyIncident) -> None:
        with self._lock:
            if incident.emergency_id in self._emergencies:
                raise ValueError("Emergency ID already exists")
            self._emergencies[incident.emergency_id] = incident.model_copy(deep=True)

    def update_emergency(self, incident: EmergencyIncident) -> None:
        """Services validate a transition under transaction before replacing."""
        with self._lock:
            if incident.emergency_id not in self._emergencies:
                raise ValueError("Emergency not found")
            self._emergencies[incident.emergency_id] = incident.model_copy(deep=True)

    def get_pending_action(self, action_id: str) -> PendingAction | None:
        with self._lock:
            action = self._pending_actions.get(action_id)
            return action.model_copy(deep=True) if action else None

    def list_pending_actions(self) -> list[PendingAction]:
        with self._lock:
            return [self._pending_actions[key].model_copy(deep=True)
                    for key in sorted(self._pending_actions)]

    def add_pending_action(self, action: PendingAction) -> None:
        with self._lock:
            if action.id in self._pending_actions:
                raise ValueError("Pending action ID already exists")
            self._pending_actions[action.id] = action.model_copy(deep=True)

    def delete_pending_action(self, action_id: str) -> None:
        with self._lock:
            self._pending_actions.pop(action_id, None)

    def add_guest_permission(self, guest: Person, permission: AccessPermission) -> None:
        """Called inside a transaction after service validation."""
        with self._lock:
            guest_copy = guest.model_copy(deep=True)
            permission_copy = permission.model_copy(deep=True)
            self._people[guest.id] = guest_copy
            self._permissions.append(permission_copy)


    def ring_receipt_transaction(self):
        return self.transaction()

    def find_ring_event(self, environment, account_id, request_id, event_id):
        with self._lock:
            return next((e.model_copy(deep=True) for e in self._ring_events.values()
                         if e.environment == environment and e.account_id == account_id
                         and (e.request_id == request_id or e.event_id == event_id)), None)

    def get_ring_account(self, identifier: str) -> RingAccount | None:
        with self._lock:
            record = self._ring_accounts.get(identifier)
            return record.model_copy(deep=True) if record else None

    def list_ring_accounts(self) -> list[RingAccount]:
        with self._lock:
            return [self._ring_accounts[key].model_copy(deep=True)
                    for key in sorted(self._ring_accounts)]

    def save_ring_account(self, record: RingAccount) -> None:
        with self._lock:
            self._ring_accounts[record.id] = RingAccount.model_validate(record.model_dump())

    def get_ring_event(self, identifier: str) -> RingEvent | None:
        with self._lock:
            record = self._ring_events.get(identifier)
            return record.model_copy(deep=True) if record else None

    def list_ring_events(self) -> list[RingEvent]:
        with self._lock:
            return [self._ring_events[key].model_copy(deep=True)
                    for key in sorted(self._ring_events)]

    def save_ring_event(self, record: RingEvent) -> None:
        with self._lock:
            self._ring_events[record.id] = RingEvent.model_validate(record.model_dump())


    def get_integration(self, identifier: str) -> BuildingIntegration | None:
        with self._lock:
            record = self._building_integrations.get(identifier)
            return record.model_copy(deep=True) if record else None

    def list_building_integrations(self) -> list[BuildingIntegration]:
        with self._lock:
            return [self._building_integrations[key].model_copy(deep=True) for key in sorted(self._building_integrations)]

    def save_integration(self, record: BuildingIntegration) -> None:
        with self._lock:
            self._building_integrations[record.id] = BuildingIntegration.model_validate(record.model_dump())

    def get_device(self, identifier: str) -> BuildingDevice | None:
        with self._lock:
            record = self._building_devices.get(identifier)
            return record.model_copy(deep=True) if record else None

    def list_building_devices(self) -> list[BuildingDevice]:
        with self._lock:
            return [self._building_devices[key].model_copy(deep=True) for key in sorted(self._building_devices)]

    def save_device(self, record: BuildingDevice) -> None:
        with self._lock:
            self._building_devices[record.id] = BuildingDevice.model_validate(record.model_dump())

    def get_device_mapping(self, identifier: str) -> DeviceMapping | None:
        with self._lock:
            record = self._device_zone_mappings.get(identifier)
            return record.model_copy(deep=True) if record else None

    def list_device_zone_mappings(self) -> list[DeviceMapping]:
        with self._lock:
            return [self._device_zone_mappings[key].model_copy(deep=True) for key in sorted(self._device_zone_mappings)]

    def save_device_mapping(self, record: DeviceMapping) -> None:
        with self._lock:
            self._device_zone_mappings[record.id] = DeviceMapping.model_validate(record.model_dump())

    def get_device_state(self, identifier: str) -> DeviceState | None:
        with self._lock:
            record = self._device_states.get(identifier)
            return record.model_copy(deep=True) if record else None

    def list_device_states(self) -> list[DeviceState]:
        with self._lock:
            return [self._device_states[key].model_copy(deep=True) for key in sorted(self._device_states)]

    def save_device_state(self, record: DeviceState) -> None:
        with self._lock:
            self._device_states[record.id] = DeviceState.model_validate(record.model_dump())

    def get_credential(self, identifier: str) -> CredentialBinding | None:
        with self._lock:
            record = self._credentials.get(identifier)
            return record.model_copy(deep=True) if record else None

    def list_credentials(self) -> list[CredentialBinding]:
        with self._lock:
            return [self._credentials[key].model_copy(deep=True) for key in sorted(self._credentials)]

    def save_credential(self, record: CredentialBinding) -> None:
        with self._lock:
            self._credentials[record.id] = CredentialBinding.model_validate(record.model_dump())

    def get_credential_event(self, identifier: str) -> CredentialEvent | None:
        with self._lock:
            record = self._credential_events.get(identifier)
            return record.model_copy(deep=True) if record else None

    def list_credential_events(self) -> list[CredentialEvent]:
        with self._lock:
            return [self._credential_events[key].model_copy(deep=True) for key in sorted(self._credential_events)]

    def save_credential_event(self, record: CredentialEvent) -> None:
        with self._lock:
            self._credential_events[record.id] = CredentialEvent.model_validate(record.model_dump())

    def get_actuator_event(self, identifier: str) -> ActuatorEvent | None:
        with self._lock:
            record = self._actuator_events.get(identifier)
            return record.model_copy(deep=True) if record else None

    def list_actuator_events(self) -> list[ActuatorEvent]:
        with self._lock:
            return [self._actuator_events[key].model_copy(deep=True) for key in sorted(self._actuator_events)]

    def save_actuator_event(self, record: ActuatorEvent) -> None:
        with self._lock:
            self._actuator_events[record.id] = ActuatorEvent.model_validate(record.model_dump())

    def get_journey(self, identifier: str) -> Journey | None:
        with self._lock:
            record = self._journeys.get(identifier)
            return record.model_copy(deep=True) if record else None

    def list_journeys(self) -> list[Journey]:
        with self._lock:
            return [self._journeys[key].model_copy(deep=True) for key in sorted(self._journeys)]

    def save_journey(self, record: Journey) -> None:
        with self._lock:
            self._journeys[record.id] = Journey.model_validate(record.model_dump())

    def get_journey_transition(self, identifier: str) -> JourneyTransition | None:
        with self._lock:
            record = self._journey_transitions.get(identifier)
            return record.model_copy(deep=True) if record else None

    def list_journey_transitions(self) -> list[JourneyTransition]:
        with self._lock:
            return [self._journey_transitions[key].model_copy(deep=True) for key in sorted(self._journey_transitions)]

    def save_journey_transition(self, record: JourneyTransition) -> None:
        with self._lock:
            self._journey_transitions[record.id] = JourneyTransition.model_validate(record.model_dump())


def create_demo_repository() -> InMemoryRepository:
    repository = InMemoryRepository(
        people=[
            Person(id="contractor-1", name="Ahmed", role=PersonRole.CONTRACTOR),
            Person(id="guest-1", name="Sara", role=PersonRole.GUEST),
            Person(id="resident-1", name="Demo resident", role=PersonRole.RESIDENT,
                   guest_zone_ids=["floor-5", "lobby"]),
            Person(id="manager-1", name="Demo manager", role=PersonRole.MANAGER),
            Person(id="responder-1", name="Demo emergency responder",
                   role=PersonRole.EMERGENCY_RESPONDER),
            Person(id="plumber-1", name="Demo plumbing contractor", role=PersonRole.CONTRACTOR),
        ],
        zones=[
            Zone(id="machine-room", name="Elevator Machine Room",
                 zone_type=ZoneType.MAINTENANCE, floor=-1, restricted=True),
            Zone(id="floor-5", name="Residential Floor 5",
                 zone_type=ZoneType.RESIDENTIAL, floor=5),
            Zone(id="lobby", name="Lobby", zone_type=ZoneType.LOBBY, floor=0),
            Zone(id="office-106", name="Atlas Dental - Office 106",
                 zone_type=ZoneType.BUSINESS, floor=1),
            Zone(id="utility-room", name="Water Utility Room",
                 zone_type=ZoneType.MAINTENANCE, floor=-1, restricted=True),
        ],
        work_orders=[WorkOrder(id="wo-001", contractor_id="contractor-1",
                              description="Repair Elevator 2",
                              allowed_zone_ids=["machine-room"], active=True),
                     WorkOrder(id="wo-plumbing-001", contractor_id="plumber-1",
                               description="Inspect and repair water utility piping",
                               allowed_zone_ids=["utility-room"], active=True)],
        businesses=[Business(id="atlas-dental", name="Atlas Dental",
                             destination_zone_ids=["office-106"])],
    )
    from app.building_demo import demo_records
    for method, records in demo_records():
        for record in records:
            getattr(repository, method)(record)
    return repository
