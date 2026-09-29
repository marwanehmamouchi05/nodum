"""Process-local repository with serialized invitation validation and writes.

Copies at the boundary prevent accidental mutations. Swap the API dependency
when adding persistence; the access engine has no repository dependency.
"""
from contextlib import contextmanager
from threading import RLock
from typing import ContextManager, Iterable, Protocol

from app.models.access import AccessPermission
from app.models.building import Person, PersonRole, WorkOrder, Zone, ZoneType
from app.models.business import Appointment, Business
from app.models.emergency import EmergencyIncident


class Repository(Protocol):
    """Service-facing contract; implementations must serialize transactions."""

    def transaction(self) -> ContextManager["Repository"]: ...
    def get_person(self, person_id: str) -> Person | None: ...
    def get_zone(self, zone_id: str) -> Zone | None: ...
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

    @contextmanager
    def transaction(self):
        """Mutual exclusion, not rollback: validate before writing."""
        with self._lock:
            yield self

    def get_person(self, person_id: str) -> Person | None:
        with self._lock:
            person = self._people.get(person_id)
            return person.model_copy(deep=True) if person else None

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

    def add_guest_permission(self, guest: Person, permission: AccessPermission) -> None:
        """Called inside a transaction after service validation."""
        with self._lock:
            guest_copy = guest.model_copy(deep=True)
            permission_copy = permission.model_copy(deep=True)
            self._people[guest.id] = guest_copy
            self._permissions.append(permission_copy)


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
