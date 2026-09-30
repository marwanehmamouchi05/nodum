"""Repository contract and in-memory test implementation.

SQLiteRepository implements this interface for the running application.
Copies at the boundary prevent accidental mutations; the access engine has no
repository dependency.
"""
from contextlib import contextmanager
from threading import RLock
from typing import ContextManager, Iterable, Protocol

from app.models.access import AccessPermission
from app.models.agent import PendingAction
from app.models.building import Person, PersonRole, WorkOrder, Zone, ZoneType
from app.models.business import Appointment, Business
from app.models.emergency import EmergencyIncident
from app.models.ring import RingAccount, RingEvent


class Repository(Protocol):
    """Service-facing contract; implementations must serialize transactions."""

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


def create_demo_repository() -> InMemoryRepository:
    return InMemoryRepository(
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
