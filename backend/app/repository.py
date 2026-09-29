"""Process-local repository with serialized invitation validation and writes.

Copies at the boundary prevent accidental mutations. Swap the API dependency
when adding persistence; the access engine has no repository dependency.
"""
from contextlib import contextmanager
from threading import RLock
from typing import ContextManager, Iterable, Protocol

from app.models.access import AccessPermission
from app.models.building import Person, PersonRole, WorkOrder, Zone, ZoneType


class Repository(Protocol):
    """Service-facing contract; implementations must serialize transactions."""

    def transaction(self) -> ContextManager["Repository"]: ...
    def get_person(self, person_id: str) -> Person | None: ...
    def get_zone(self, zone_id: str) -> Zone | None: ...
    def list_permissions(self) -> list[AccessPermission]: ...
    def list_work_orders(self) -> list[WorkOrder]: ...
    def add_guest_permission(self, guest: Person, permission: AccessPermission) -> None: ...


class InMemoryRepository:
    def __init__(
        self,
        people: Iterable[Person] = (),
        zones: Iterable[Zone] = (),
        permissions: Iterable[AccessPermission] = (),
        work_orders: Iterable[WorkOrder] = (),
    ):
        self._lock = RLock()
        self._people = {p.id: p.model_copy(deep=True) for p in people}
        self._zones = {z.id: z.model_copy(deep=True) for z in zones}
        self._permissions = [p.model_copy(deep=True) for p in permissions]
        self._work_orders = [w.model_copy(deep=True) for w in work_orders]

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
        ],
        zones=[
            Zone(id="machine-room", name="Elevator Machine Room",
                 zone_type=ZoneType.MAINTENANCE, floor=-1, restricted=True),
            Zone(id="floor-5", name="Residential Floor 5",
                 zone_type=ZoneType.RESIDENTIAL, floor=5),
            Zone(id="lobby", name="Lobby", zone_type=ZoneType.LOBBY, floor=0),
        ],
        work_orders=[WorkOrder(id="wo-001", contractor_id="contractor-1",
                              description="Repair Elevator 2",
                              allowed_zone_ids=["machine-room"], active=True)],
    )
