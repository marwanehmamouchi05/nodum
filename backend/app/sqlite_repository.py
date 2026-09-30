"""SQLite implementation of Repository. Domain services remain SQL-free.

Entity payloads are validated model JSON (UTC timestamps), with relational keys
for identity and key references. Emergency history is stored separately.
"""
from contextlib import contextmanager
import json
import sqlite3

from app.services.errors import DomainError

from app.database import SQLiteDatabase
from app.models.access import AccessPermission
from app.models.agent import PendingAction
from app.models.building import Person, Zone, WorkOrder
from app.models.business import Appointment, Business
from app.models.emergency import EmergencyIncident
from app.models.ring import RingAccount, RingEvent
from app.models.integrations import (BuildingIntegration, BuildingDevice, DeviceMapping, DeviceState, CredentialBinding, CredentialEvent, ActuatorEvent, Journey, JourneyTransition)

from app.repository import create_demo_repository


class SQLiteRepository:
    def __init__(self, database_url: str | None = None):
        self.database = SQLiteDatabase(database_url)

    def initialize(self, seed_demo: bool = True):
        self.database.initialize()
        if seed_demo:
            self.seed_demo_data()

    @contextmanager
    def transaction(self):
        with self.database.transaction():
            yield self

    def seed_demo_data(self):
        """Insert only missing IDs; never reset existing business state."""
        demo = create_demo_repository()
        with self.database.transaction() as connection:
            for table, records in (
                ("people", demo.list_people()), ("zones", demo.list_zones()),
                ("businesses", demo.list_businesses()),
            ):
                for record in records:
                    connection.execute(
                        f"INSERT INTO {table} (id, data) VALUES (?, ?) ON CONFLICT(id) DO NOTHING",
                        (record.id, record.model_dump_json()),
                    )
            for table, records in (
                ("building_integrations", demo.list_building_integrations()),
                ("building_devices", demo.list_building_devices()),
                ("device_zone_mappings", demo.list_device_zone_mappings()),
                ("device_states", demo.list_device_states()),
                ("credentials", demo.list_credentials()),
                ("credential_events", demo.list_credential_events()),
                ("actuator_events", demo.list_actuator_events()),
                ("journeys", demo.list_journeys()),
                ("journey_transitions", demo.list_journey_transitions()),
            ):
                for record in records:
                    connection.execute(
                        f"INSERT INTO {table} (id, data) VALUES (?, ?) ON CONFLICT(id) DO NOTHING",
                        (record.id, record.model_dump_json()),
                    )
            for order in demo.list_work_orders():
                connection.execute(
                    """INSERT INTO work_orders (id, contractor_id, data) VALUES (?, ?, ?)
                       ON CONFLICT(id) DO NOTHING""",
                    (order.id, order.contractor_id, order.model_dump_json()),
                )

    def _get(self, table, identifier, model):
        # Table names are internal constants, never API/model-provided identifiers.
        with self.database.transaction() as connection:
            row = connection.execute(f"SELECT data FROM {table} WHERE id = ?", (identifier,)).fetchone()
            return model.model_validate_json(row["data"]) if row else None

    def _list(self, table, model, order="id"):
        with self.database.transaction() as connection:
            return [model.model_validate_json(row["data"])
                    for row in connection.execute(f"SELECT data FROM {table} ORDER BY {order}")]

    def get_person(self, person_id: str) -> Person | None:
        return self._get("people", person_id, Person)

    def list_people(self) -> list[Person]:
        return self._list("people", Person)

    def get_zone(self, zone_id: str) -> Zone | None:
        return self._get("zones", zone_id, Zone)

    def list_zones(self) -> list[Zone]:
        return self._list("zones", Zone)

    def list_permissions(self) -> list[AccessPermission]:
        return self._list("permissions", AccessPermission, "sequence")

    def list_work_orders(self) -> list[WorkOrder]:
        return self._list("work_orders", WorkOrder, "rowid")

    def get_business(self, business_id: str) -> Business | None:
        return self._get("businesses", business_id, Business)

    def list_businesses(self) -> list[Business]:
        return self._list("businesses", Business)

    def get_appointment(self, appointment_id: str) -> Appointment | None:
        return self._get("appointments", appointment_id, Appointment)

    def list_appointments(self) -> list[Appointment]:
        return self._list("appointments", Appointment)

    def add_appointment(self, appointment: Appointment) -> None:
        appointment = Appointment.model_validate(appointment.model_dump())
        with self.database.transaction() as connection:
            if self.get_appointment(appointment.id) is not None:
                raise ValueError("Appointment ID already exists")
            connection.execute(
                "INSERT INTO appointments (id, business_id, destination_zone_id, data) VALUES (?, ?, ?, ?)",
                (appointment.id, appointment.business_id, appointment.destination_zone_id,
                 appointment.model_dump_json()),
            )

    def _save_person_permission(self, person: Person, permission: AccessPermission):
        person = Person.model_validate(person.model_dump())
        permission = AccessPermission.model_validate(permission.model_dump())
        connection = self.database.connection
        connection.execute(
            "INSERT INTO people (id, data) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET data=excluded.data",
            (person.id, person.model_dump_json()),
        )
        connection.execute(
            """INSERT INTO permissions (id, person_id, appointment_id, business_id, data)
               VALUES (?, ?, ?, ?, ?)""",
            (permission.id, permission.person_id, permission.appointment_id,
             permission.business_id, permission.model_dump_json()),
        )

    def add_guest_permission(self, guest: Person, permission: AccessPermission) -> None:
        with self.database.transaction():
            self._save_person_permission(guest, permission)

    def record_check_in(self, visitor: Person, appointment: Appointment,
                        permission: AccessPermission) -> None:
        appointment = Appointment.model_validate(appointment.model_dump())
        with self.database.transaction() as connection:
            if self.get_appointment(appointment.id) is None:
                raise ValueError("Appointment not found")
            self._save_person_permission(visitor, permission)
            connection.execute(
                "UPDATE appointments SET business_id=?, destination_zone_id=?, data=? WHERE id=?",
                (appointment.business_id, appointment.destination_zone_id,
                 appointment.model_dump_json(), appointment.id),
            )

    def get_emergency(self, emergency_id: str) -> EmergencyIncident | None:
        with self.database.transaction() as connection:
            row = connection.execute("SELECT data FROM emergencies WHERE id=?", (emergency_id,)).fetchone()
            if row is None:
                return None
            data = json.loads(row["data"])
            data["history"] = [json.loads(event["data"]) for event in connection.execute(
                "SELECT data FROM emergency_events WHERE emergency_id=? ORDER BY sequence", (emergency_id,))]
            return EmergencyIncident.model_validate(data)

    def list_emergencies(self) -> list[EmergencyIncident]:
        with self.database.transaction() as connection:
            ids = [row["id"] for row in connection.execute("SELECT id FROM emergencies ORDER BY id")]
            return [self.get_emergency(identifier) for identifier in ids]

    def add_emergency(self, incident: EmergencyIncident) -> None:
        incident = EmergencyIncident.model_validate(incident.model_dump())
        with self.database.transaction() as connection:
            if self.get_emergency(incident.emergency_id) is not None:
                raise ValueError("Emergency ID already exists")
            connection.execute("INSERT INTO emergencies (id, data) VALUES (?, ?)",
                               (incident.emergency_id, incident.model_dump_json(exclude={"history"})))
            self._append_events(incident, 0)

    def _append_events(self, incident, start):
        self.database.connection.executemany(
            "INSERT INTO emergency_events (emergency_id, sequence, data) VALUES (?, ?, ?)",
            [(incident.emergency_id, index, event.model_dump_json())
             for index, event in enumerate(incident.history) if index >= start],
        )

    def update_emergency(self, incident: EmergencyIncident) -> None:
        incident = EmergencyIncident.model_validate(incident.model_dump())
        with self.database.transaction() as connection:
            previous = self.get_emergency(incident.emergency_id)
            if previous is None:
                raise ValueError("Emergency not found")
            if incident.history[:len(previous.history)] != previous.history:
                raise ValueError("Existing emergency audit events cannot be rewritten")
            connection.execute("UPDATE emergencies SET data=? WHERE id=?",
                               (incident.model_dump_json(exclude={"history"}), incident.emergency_id))
            self._append_events(incident, len(previous.history))

    def get_pending_action(self, action_id: str) -> PendingAction | None:
        return self._get("pending_actions", action_id, PendingAction)

    def list_pending_actions(self) -> list[PendingAction]:
        return self._list("pending_actions", PendingAction)

    def add_pending_action(self, action: PendingAction) -> None:
        with self.database.transaction() as connection:
            connection.execute("INSERT INTO pending_actions (id, data) VALUES (?, ?)",
                               (action.id, action.model_dump_json()))

    def delete_pending_action(self, action_id: str) -> None:
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM pending_actions WHERE id=?", (action_id,))

    def get_ring_account(self, identifier: str) -> RingAccount | None:
        return self._get("ring_accounts", identifier, RingAccount)

    def list_ring_accounts(self) -> list[RingAccount]:
        return self._list("ring_accounts", RingAccount)

    def save_ring_account(self, record: RingAccount) -> None:
        record = RingAccount.model_validate(record.model_dump())
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO ring_accounts (id, data) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                (record.id, record.model_dump_json()),
            )

    def get_ring_event(self, identifier: str) -> RingEvent | None:
        return self._get("ring_events", identifier, RingEvent)

    def list_ring_events(self) -> list[RingEvent]:
        return self._list("ring_events", RingEvent)

    def save_ring_event(self, record: RingEvent) -> None:
        record = RingEvent.model_validate(record.model_dump())
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO ring_events (id, data) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                (record.id, record.model_dump_json()),
            )

    @contextmanager
    def ring_receipt_transaction(self):
        # Ring retries 5xx responses. Avoid waiting the full webhook deadline on
        # a busy database; never acknowledge an event that was not committed.
        try:
            with self.database.transaction(timeout_ms=1000):
                yield self
        except sqlite3.OperationalError:
            raise DomainError(503, "Ring inbox temporarily unavailable") from None

    def find_ring_event(self, environment, account_id, request_id, event_id):
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT data FROM ring_events WHERE json_extract(data, '$.environment') = ? "
                "AND json_extract(data, '$.account_id') = ? AND "
                "(json_extract(data, '$.request_id') = ? OR json_extract(data, '$.event_id') = ?)",
                (environment, account_id, request_id, event_id),
            ).fetchone()
            return RingEvent.model_validate_json(row["data"]) if row else None

    def get_integration(self, identifier: str) -> BuildingIntegration | None:
        return self._get("building_integrations", identifier, BuildingIntegration)

    def list_building_integrations(self) -> list[BuildingIntegration]:
        return self._list("building_integrations", BuildingIntegration)

    def save_integration(self, record: BuildingIntegration) -> None:
        record = BuildingIntegration.model_validate(record.model_dump())
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO building_integrations (id, data) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                (record.id, record.model_dump_json()),
            )

    def get_device(self, identifier: str) -> BuildingDevice | None:
        return self._get("building_devices", identifier, BuildingDevice)

    def list_building_devices(self) -> list[BuildingDevice]:
        return self._list("building_devices", BuildingDevice)

    def save_device(self, record: BuildingDevice) -> None:
        record = BuildingDevice.model_validate(record.model_dump())
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO building_devices (id, data) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                (record.id, record.model_dump_json()),
            )

    def get_device_mapping(self, identifier: str) -> DeviceMapping | None:
        return self._get("device_zone_mappings", identifier, DeviceMapping)

    def list_device_zone_mappings(self) -> list[DeviceMapping]:
        return self._list("device_zone_mappings", DeviceMapping)

    def save_device_mapping(self, record: DeviceMapping) -> None:
        record = DeviceMapping.model_validate(record.model_dump())
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO device_zone_mappings (id, data) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                (record.id, record.model_dump_json()),
            )

    def get_device_state(self, identifier: str) -> DeviceState | None:
        return self._get("device_states", identifier, DeviceState)

    def list_device_states(self) -> list[DeviceState]:
        return self._list("device_states", DeviceState)

    def save_device_state(self, record: DeviceState) -> None:
        record = DeviceState.model_validate(record.model_dump())
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO device_states (id, data) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                (record.id, record.model_dump_json()),
            )

    def get_credential(self, identifier: str) -> CredentialBinding | None:
        return self._get("credentials", identifier, CredentialBinding)

    def list_credentials(self) -> list[CredentialBinding]:
        return self._list("credentials", CredentialBinding)

    def save_credential(self, record: CredentialBinding) -> None:
        record = CredentialBinding.model_validate(record.model_dump())
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO credentials (id, data) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                (record.id, record.model_dump_json()),
            )

    def get_credential_event(self, identifier: str) -> CredentialEvent | None:
        return self._get("credential_events", identifier, CredentialEvent)

    def list_credential_events(self) -> list[CredentialEvent]:
        return self._list("credential_events", CredentialEvent)

    def save_credential_event(self, record: CredentialEvent) -> None:
        record = CredentialEvent.model_validate(record.model_dump())
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO credential_events (id, data) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                (record.id, record.model_dump_json()),
            )

    def get_actuator_event(self, identifier: str) -> ActuatorEvent | None:
        return self._get("actuator_events", identifier, ActuatorEvent)

    def list_actuator_events(self) -> list[ActuatorEvent]:
        return self._list("actuator_events", ActuatorEvent)

    def save_actuator_event(self, record: ActuatorEvent) -> None:
        record = ActuatorEvent.model_validate(record.model_dump())
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO actuator_events (id, data) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                (record.id, record.model_dump_json()),
            )

    def get_journey(self, identifier: str) -> Journey | None:
        return self._get("journeys", identifier, Journey)

    def list_journeys(self) -> list[Journey]:
        return self._list("journeys", Journey)

    def save_journey(self, record: Journey) -> None:
        record = Journey.model_validate(record.model_dump())
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO journeys (id, data) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                (record.id, record.model_dump_json()),
            )

    def get_journey_transition(self, identifier: str) -> JourneyTransition | None:
        return self._get("journey_transitions", identifier, JourneyTransition)

    def list_journey_transitions(self) -> list[JourneyTransition]:
        return self._list("journey_transitions", JourneyTransition)

    def save_journey_transition(self, record: JourneyTransition) -> None:
        record = JourneyTransition.model_validate(record.model_dump())
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO journey_transitions (id, data) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                (record.id, record.model_dump_json()),
            )
