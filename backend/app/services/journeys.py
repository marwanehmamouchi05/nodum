"""Deterministic journey planning and simulator orchestration; no AI dependency."""
from app.models.access import AccessDecision, AccessRequest
from app.models.business import AppointmentCreateInput, AppointmentStatus, VisitorCheckInInput
from app.models.integrations import (
    ActionInput, Command, ConnectorKind, Journey, JourneyInput, JourneyStep, JourneyTransition,
    TransitionInput,
)
from app.services.access_engine import evaluate_access
from app.services.appointments import check_in_visitor, create_appointment
from app.services.building import BuildingService, fingerprint, result, utc
from app.services.emergencies import validate_operator
from app.services.errors import DomainError


class JourneyService:
    def __init__(self, repository, registry=None):
        self.repo = repository
        self.building = BuildingService(repository, registry)

    def get(self, identifier):
        record = self.repo.get_journey(identifier)
        if record is None:
            raise DomainError(404, "Journey not found")
        return record

    def create(self, payload: JourneyInput, now):
        payload = JourneyInput.model_validate(payload.model_dump())
        now = utc(now)
        digest = fingerprint(payload.model_dump(mode="json"))
        with self.repo.transaction():
            previous = self.repo.get_journey(payload.id)
            if previous:
                if previous.request_fingerprint != digest:
                    raise DomainError(409, "Journey ID conflicts with previous request")
                return previous
            start = self.repo.get_zone(payload.starting_zone_id)
            destination = self.repo.get_zone(payload.destination_zone_id)
            if start is None or destination is None:
                raise DomainError(404, "Journey zone not found")
            if payload.arrival_ring_event_id:
                event = self.repo.get_ring_event(payload.arrival_ring_event_id)
                if event is None or event.event_type not in {"motion_detected", "button_press"}:
                    raise DomainError(422, "Arrival context must reference a verified Ring motion/doorbell event")
                # Presence context is never identity proof or an access grant.
            if payload.appointment_id:
                appointment = self.repo.get_appointment(payload.appointment_id)
                if appointment is None:
                    raise DomainError(404, "Journey appointment not found")
                if (appointment.visitor_id != payload.person_id
                        or appointment.destination_zone_id != destination.id):
                    raise DomainError(403, "Journey does not match the appointment")
                if appointment.status == AppointmentStatus.SCHEDULED:
                    check_in_visitor(self.repo, appointment.id, VisitorCheckInInput(
                        visitor_id=appointment.visitor_id, visitor_name=appointment.visitor_name), now)
            person = self.repo.get_person(payload.person_id)
            if person is None:
                raise DomainError(404, "Journey person not found")
            decisions = {}
            for zone in (start, destination):
                decisions[zone.id] = evaluate_access(
                    AccessRequest(person_id=person.id, zone_id=zone.id, purpose=payload.purpose, requested_at=now),
                    person, zone, self.repo.list_permissions(), self.repo.list_work_orders(),
                    appointments=self.repo.list_appointments(), businesses=self.repo.list_businesses(),
                    emergencies=self.repo.list_emergencies(), journey_destination=destination)
            allowed = all(d.allowed for d in decisions.values())
            journey = Journey(**payload.model_dump(), request_fingerprint=digest,
                authorized_zone_ids=[z for z, decision in decisions.items() if decision.allowed],
                status="ready" if allowed else "denied", created_at=now, updated_at=now)
            if not allowed:
                journey.steps = [JourneyStep(kind="access_decision", zone_id=zone,
                    result=result("denied" if not decision.allowed else "manual_action_required", decision,
                                  "Journey denied; no actuator command issued")) for zone, decision in decisions.items()]
                self.repo.save_journey(journey)
                return journey
            route = [start.name]
            if start.floor != destination.floor:
                route.extend(["Elevator", f"Floor {destination.floor} corridor (guidance waypoint)"])
            if destination.id != start.id:
                route.append(destination.name)
            journey.route = route
            self.repo.save_journey(journey)
            actions = [("entrance", ConnectorKind.ACCESS, start.id, Command.TEMPORARY_UNLOCK)]
            if start.floor != destination.floor:
                actions.extend([
                    ("elevator_call", ConnectorKind.ELEVATOR, start.id, Command.CALL),
                    ("elevator_destination", ConnectorKind.ELEVATOR, destination.id, Command.AUTHORIZE_FLOOR)])
            actions.append(("wayfinding", ConnectorKind.WAYFINDING, destination.id, Command.ILLUMINATE))
            for step, kind, zone, command in actions:
                device = self.building.choose_device(kind, zone, command) if payload.use_connectors else None
                if device is None:
                    message = "Visitor verified; manual door action required" if step == "entrance" else f"Authorized {step}; manual action required"
                    outcome = result("manual_action_required", decisions[zone], message)
                else:
                    outcome = self.building.action(device.id, ActionInput(
                        id="journey-" + fingerprint([journey.id, step]), person_id=person.id, zone_id=zone,
                        purpose=payload.purpose, command=command, journey_id=journey.id), now)
                journey.steps.append(JourneyStep(kind=step, zone_id=zone, result=outcome))
                if outcome.status in {"denied", "failed"}:
                    journey.status = "failed"
                    break
            if journey.status != "failed" and any(s.result.status == "manual_action_required" for s in journey.steps):
                journey.status = "manual_action_required"
            self.repo.save_journey(journey)
            return journey

    def confirm_transition(self, identifier, payload: TransitionInput, now):
        payload = TransitionInput.model_validate(payload.model_dump())
        now = utc(now)
        digest = fingerprint({"journey_id": identifier, **payload.model_dump(mode="json")})
        with self.repo.transaction():
            old = self.repo.get_journey_transition(payload.id)
            if old:
                if old.request_fingerprint != digest:
                    raise DomainError(409, "Transition ID conflicts with previous event")
                return old
            journey = self.get(identifier)
            if now < journey.updated_at:
                raise DomainError(422, "Confirmed transition cannot precede journey history")
            decision = self.building.decision(journey.person_id, payload.zone_id, journey.purpose, now, journey)
            if not decision.allowed:
                raise DomainError(403, decision.reason)
            device = self.building.device(payload.source_device_id)
            integration = self.building.integration(device.integration_id)
            mapping = self.repo.get_device_mapping(device.id)
            if (not device.simulated or integration.mode != "simulated"
                    or not integration.enabled or device.connection_status != "online"
                    or not mapping or payload.zone_id not in mapping.zone_ids):
                raise DomainError(403, "Confirmation device does not serve this zone")
            # Explicit simulator confirmations are not motion-derived indoor tracking.
            expected = journey.starting_zone_id if journey.current_confirmed_zone_id is None else journey.destination_zone_id
            if payload.zone_id != expected or payload.zone_id == journey.current_confirmed_zone_id:
                raise DomainError(409, "Transition is not the next journey zone")
            transition = JourneyTransition(**payload.model_dump(), journey_id=journey.id,
                person_id=journey.person_id, at=now, request_fingerprint=digest)
            journey.current_confirmed_zone_id = payload.zone_id
            journey.updated_at = now
            journey.status = "completed" if payload.zone_id == journey.destination_zone_id else "in_progress"
            self.repo.save_journey_transition(transition)
            self.repo.save_journey(journey)
            return transition

    def demo_atlas(self, identifier, actor_id, connect_simulators, now):
        """Repeatable demo, with real services and explicitly simulated arrival."""
        now = utc(now)
        with self.repo.transaction():
            validate_operator(self.repo, actor_id)
            key = fingerprint(["atlas-demo", identifier, connect_simulators])[:24]
            journey_id = "atlas-journey-" + key
            previous = self.repo.get_journey(journey_id)
            if previous:
                return previous
            # Seed records already exist, disabled by default; never overwrite mappings.
            if connect_simulators:
                for kind in ("access_control", "credential_reader", "elevator", "wayfinding"):
                    self.building.configure_integration("demo-" + kind, True, actor_id, now)
            appointment_id = "atlas-appointment-" + key
            visitor_id = "atlas-visitor-" + key
            if self.repo.get_appointment(appointment_id) is None:
                create_appointment(self.repo, AppointmentCreateInput(id=appointment_id,
                    visitor_id=visitor_id, visitor_name="Atlas Dental demo visitor", business_id="atlas-dental",
                    destination_zone_id="office-106", appointment_time=now), now)
            return self.create(JourneyInput(id=journey_id, person_id=visitor_id,
                purpose="I am here for Atlas Dental (simulated arrival context)", starting_zone_id="lobby",
                destination_zone_id="office-106", appointment_id=appointment_id, use_connectors=connect_simulators), now)
