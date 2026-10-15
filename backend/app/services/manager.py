"""Scoped operational projection. No inferred ownership or hardware telemetry."""
from datetime import timedelta
from uuid import uuid4
from app.models.authorization import Permission as P
from app.models.structure import NodeKind as K
from app.services.errors import DomainError
from app.services.scoped_repository import ScopedRepository, bind_created
from app.services.structure import StructureService, read_permission


class ManagerService:
    def __init__(self, authorization, *, ai_context=False):
        self.auth = authorization
        self.repo = authorization.repository
        self.ai_context = ai_context

    def allowed(self, permission, kind, identifier):
        return self.auth.allowed(permission, kind, identifier) and (
            not self.ai_context or self.auth.allowed(P.AI_USE, kind, identifier))

    def records(self, kind, permission):
        return [r for r in self.repo.list_operational_records(kind)
                if self.allowed(permission, kind, r["id"])]

    def target(self, identifier, permission):
        node = self.repo.get_structure_node(identifier)
        if not node or node.kind not in {K.BUILDING, K.FLOOR, K.LOCATION, K.UNIT, K.BUSINESS, K.ROOM}:
            raise DomainError(403, "Operational location is unavailable")
        self.auth.require(permission, "structure", node.id)
        return node

    def journal(self, action, record):
        entry = {"id": str(uuid4()), "scope_id": record["scope_id"], "at": self.auth.now.isoformat(),
                 "action": action, "resource_id": record["id"], "location_id": record["location_id"],
                 "actor_id": self.auth.principal.person_id}
        self.repo.save_operational_record("operation_activity", entry)
        bind_created(self.repo, "operation_activity", entry["id"], entry["scope_id"])

    def create(self, kind, payload):
        permission = P.ANNOUNCEMENTS_PUBLISH if kind == "announcement" else P.MAINTENANCE_CREATE
        with self.repo.transaction():
            node = self.target(payload.location_id, permission)
            now = self.auth.now.isoformat()
            record = {**payload.model_dump(mode="json"), "id": str(uuid4()),
                "building_id": node.building_id, "scope_id": node.scope_id,
                "created_at": now, "updated_at": now, "demo": node.demo}
            if kind == "announcement":
                publish = payload.publish_at or self.auth.now
                if payload.expires_at and payload.expires_at <= publish:
                    raise DomainError(422, "Expiry must follow publication")
                record.update(creator_id=self.auth.principal.person_id, publish_at=publish.isoformat())
            else:
                record.update(reporter_id=self.auth.principal.person_id, status="new", assignee_id=None,
                    resolved_at=None, history=[])
            self.repo.save_operational_record(kind, record)
            bind_created(self.repo, kind, record["id"], node.scope_id)
            self.journal(kind + ".created", record)
            return record

    def invite(self, payload):
        with self.repo.transaction():
            node = self.target(payload.location_id, P.VISITORS_INVITE)
            if payload.ends_at <= self.auth.now:
                raise DomainError(422, "Visit window must not have expired")
            record = {**payload.model_dump(mode="json"), "id": str(uuid4()), "scope_id": node.scope_id,
                "building_id": node.building_id, "host_id": self.auth.principal.person_id,
                "created_at": self.auth.now.isoformat(), "checked_in_at": None, "demo": node.demo}
            self.repo.save_operational_record("visitor", record)
            bind_created(self.repo, "visitor", record["id"], node.scope_id)
            self.journal("visitor.invited", record)
            return record

    def arrive(self, identifier):
        with self.repo.transaction():
            self.auth.require(P.VISITORS_CHECK_IN, "visitor", identifier)
            record = next((r for r in self.repo.list_operational_records("visitor") if r["id"] == identifier), None)
            if not record:
                raise DomainError(403, "Visit is unavailable")
            self.target(record["location_id"], P.VISITORS_CHECK_IN)
            from datetime import datetime
            if not datetime.fromisoformat(record["starts_at"]) <= self.auth.now < datetime.fromisoformat(record["ends_at"]):
                raise DomainError(403, "Visit is outside its time window")
            if record.get("cancelled_at"):
                raise DomainError(409, "This visit was cancelled")
            if record["checked_in_at"]:
                raise DomainError(409, "Visitor has already arrived")
            record["checked_in_at"] = self.auth.now.isoformat()
            self.repo.save_operational_record("visitor", record)
            self.journal("visitor.arrived", record)
            return record

    def update_maintenance(self, identifier, payload):
        with self.repo.transaction():
            self.auth.require(P.MAINTENANCE_MANAGE, "maintenance", identifier)
            record = next((r for r in self.repo.list_operational_records("maintenance") if r["id"] == identifier), None)
            if not record:
                raise DomainError(403, "Maintenance request is unavailable")
            self.target(record["location_id"], P.MAINTENANCE_MANAGE)
            if payload.assignee_id:
                self.auth.require(P.PEOPLE_READ, "person", payload.assignee_id)
                people = self.people()
                if not any(p["id"] == payload.assignee_id and p["active"] and
                           p["role"] in {"maintenance", "contractor"} and
                           p["building_id"] == record["building_id"] for p in people):
                    raise DomainError(422, "Choose an active maintenance person in this building")
            now = self.auth.now.isoformat()
            record = {**record, **payload.model_dump(exclude={"note", "public_message"}), "updated_at": now,
                "resolved_at": now if payload.status in {"resolved", "closed"} else None,
                "history": [*record["history"], {"status": payload.status, "note": payload.note, "public_message": payload.public_message,
                    "at": now, "actor_id": self.auth.principal.person_id}]}
            self.repo.save_operational_record("maintenance", record)
            self.journal("maintenance." + payload.status, record)
            return record

    def people(self):
        result = []
        for affiliation in self.repo.list_affiliations():
            if not self.allowed(P.PEOPLE_READ, "affiliation", affiliation.id):
                continue
            user = self.repo.get_auth_user(affiliation.user_id)
            node = self.repo.get_structure_node(affiliation.target_id)
            if not user or not node or not self.allowed(P.PEOPLE_READ, "person", user.person_id):
                continue
            person = self.repo.get_person(user.person_id)
            if not person:
                continue
            active = user.active and affiliation.active and (
                affiliation.starts_at is None or affiliation.starts_at <= self.auth.now) and (
                affiliation.ends_at is None or self.auth.now < affiliation.ends_at)
            result.append({"id": person.id, "name": person.name, "role": affiliation.role.value,
                "location": node.name if self.allowed(P.LOCATIONS_READ, "structure", node.id) else "Scoped area",
                "building_id": node.building_id, "active": active,
                "starts_at": affiliation.starts_at, "ends_at": affiliation.ends_at})
        return result

    def snapshot(self):
        with self.repo.transaction():
            from app.integrations.ring.config import RingSettings
            auth, now = self.auth, self.auth.now
            try:
                simulation_mode = RingSettings.from_env().mode == "simulation"
            except DomainError:
                simulation_mode = False
            scoped = ScopedRepository(self.repo, auth, ai_context=self.ai_context)
            nodes = [n for n in StructureService(auth).catalog()["nodes"]
                     if self.allowed(read_permission(n), "structure", n.id)]
            names = {n.id: n.name for n in nodes}
            zones = scoped.list_zones()
            names.update({z.id: z.name for z in zones})
            people = self.people()
            person_names = {p.id: p.name for p in scoped.list_people()}
            person_names.update({p["id"]: p["name"] for p in people})
            def place(identifier):
                return names.get(identifier, "Scoped area")
            def who(identifier):
                return person_names.get(identifier, "Scoped person")
            maintenance = self.records("maintenance", P.MAINTENANCE_READ)
            announcements = self.records("announcement", P.ANNOUNCEMENTS_READ)
            # A write grant does not confer private read authority.
            for r in maintenance:
                r["can_manage"] = self.allowed(P.MAINTENANCE_MANAGE, "maintenance", r["id"])
                r["reporter_name"] = who(r["reporter_id"])
                r["location_name"] = place(r["location_id"])
                r["assignee_name"] = who(r["assignee_id"]) if r["assignee_id"] else None
                for h in r["history"]:
                    h["actor_name"] = who(h["actor_id"])
            appointments = scoped.list_appointments()
            visitors = []
            for a in appointments:
                start = a.appointment_time - timedelta(minutes=a.access_before_minutes)
                end = a.appointment_time + timedelta(minutes=a.access_after_minutes)
                state = "completed" if a.status == "cancelled" else "expired" if now >= end else "active" if a.checked_in_at else "expected"
                business = scoped.get_business(a.business_id)
                visitors.append({"can_check_in": self.allowed(P.VISITORS_CHECK_IN, "appointment", a.id) and start <= now < end and not a.checked_in_at, "id": a.id, "name": a.visitor_name, "host": business.name if business else "Scoped host",
                    "destination": place(a.destination_zone_id), "location_id": a.destination_zone_id, "start": start, "end": end,
                    "status": state, "source": "scheduled", "appointment": a})
            from datetime import datetime
            for v in self.records("visitor", P.VISITORS_READ):
                start, end = datetime.fromisoformat(v["starts_at"]), datetime.fromisoformat(v["ends_at"])
                visitors.append({"id": v["id"], "name": v["name"], "host": who(v["host_id"]),
                    "destination": place(v["location_id"]), "location_id": v["location_id"], "start": start, "end": end,
                    "status": "cancelled" if v.get("cancelled_at") else "completed" if now >= end and v["checked_in_at"] else "expired" if now >= end else "arrived" if v["checked_in_at"] else "expected",
                    "source": "demo/simulation" if v["demo"] else "scheduled", "appointment": None,
                    "can_arrive": not v.get("cancelled_at") and not v["checked_in_at"] and start <= now < end and self.allowed(P.VISITORS_CHECK_IN, "visitor", v["id"]),
                    "access_note": "Visit record only; no physical access granted."})
            permissions = scoped.list_permissions()
            for grant in permissions:
                visitors.append({"id": grant.id, "name": who(grant.person_id), "host": "Temporary invitation",
                    "destination": ", ".join(place(z) for z in grant.allowed_zone_ids),
                    "start": grant.valid_from, "end": grant.valid_until,
                    "status": "expired" if now >= grant.valid_until else "expected" if now < grant.valid_from else "active",
                    "source": "scheduled", "appointment": None})
            incidents = scoped.list_emergencies()
            devices = [{"id": d.id, "name": d.name, "status": d.connection_status,
                "location": place(d.zone_id), "simulated": d.simulated} for d in scoped.list_building_devices()]
            existing = {d["id"] for d in devices}
            devices.extend({"id": n.id, "name": n.name, "status": "unverified",
                "location": place(n.parent_id), "simulated": n.demo or n.connection_path.value == "simulation"}
                for n in nodes if n.kind == K.DEVICE and n.id not in existing)
            ring = [{"id": e.id, "at": e.occurred_at, "signal": e.signal, "status": e.status,
                "simulated": (e.source.startswith("simulation:") or e.account_id == "simulation.playground"), "source": "Ring",
                "description": "Arrival signal; visitor identity and destination are not established by this event. No door was unlocked." if e.signal in {"doorbell", "person", "motion"} else "Recorded Ring signal for operator review. This signal does not establish physical readiness or grant access."}
                for e in scoped.list_ring_events()]
            from app.services.ring import identity
            for projection in ring:
                event = self.repo.get_ring_event(projection["id"])
                mapped = next((device for device in self.repo.list_building_devices()
                    if event and device.external_device_id == event.source
                    and device.external_account_key == identity(event.environment, event.account_id)
                    and self.allowed(P.HARDWARE_READ, "device", device.id)), None)
                binding = self.repo.get_resource_binding("device", mapped.id) if mapped else None
                # A resource binding is the only product-scope location link available
                # here. Leave the signal unmapped when no authorized link exists.
                projection["location_id"] = binding.scope_id if binding and any(
                    node.scope_id == binding.scope_id for node in nodes) else None
            ring.sort(key=lambda e: e["at"])
            activity = []
            for e in ring:
                if self.allowed(P.ACTIVITY_READ, "ring_event", e["id"]):
                    from app.services.ring import identity
                    event = self.repo.get_ring_event(e["id"])
                    mapped = next((d for d in self.repo.list_building_devices()
                        if event and d.external_device_id == event.source
                        and d.external_account_key == identity(event.environment, event.account_id)
                        and self.allowed(P.HARDWARE_READ, "device", d.id)), None)
                    binding = self.repo.get_resource_binding("device", mapped.id) if mapped else None
                    labels = {"doorbell": "Visitor arrival signal", "person": "Person detected", "motion": "Motion detected", "package": "Package detected"}
                    activity.append({"id": e["id"], "at": e["at"], "what": labels.get(e["signal"], e["signal"].replace("_", " ")),
                        "who": "Ring", "where": place(binding.scope_id) if binding else "Ring device (location unverified)", "result": e["status"], "simulated": e["simulated"]})
            for e in self.records("operation_activity", P.ACTIVITY_READ):
                activity.append({"id": e["id"], "at": e["at"], "what": e["action"].replace(".", " ").replace("_", " "),
                    "who": who(e["actor_id"]), "where": place(e["location_id"]), "result": "Recorded", "simulated": bool(e.get("simulated", False))})
            for e in scoped.list_actuator_events():
                activity.append({"id": e.id, "at": e.at, "what": "Access granted" if e.decision.allowed else "Access denied",
                    "who": who(e.person_id), "where": place(e.zone_id), "result": "Executed" if e.executed else "Not executed", "simulated": e.simulated})
            for a in appointments:
                if a.checked_in_at and self.allowed(P.ACTIVITY_READ, "appointment", a.id):
                    activity.append({"id": a.id, "at": a.checked_in_at, "what": "Visitor checked in", "who": a.visitor_name,
                        "where": place(a.destination_zone_id), "result": "Arrived", "simulated": False})
            activity.sort(key=lambda e: str(e["at"]), reverse=True)
            open_requests = [r for r in maintenance if r["status"] not in {"resolved", "closed"}]
            active_incidents = [i for i in incidents if i.status != "resolved"]
            offline = [d for d in devices if d["status"] == "offline"]
            unverified = [d for d in devices if d["status"] not in {"online", "connected", "offline"}]
            attention = [{"title": i.description, "detail": "Active incident", "page": "Security"} for i in active_incidents]
            attention += [{"title": d["name"], "detail": "Device offline", "page": "Security"} for d in offline]
            attention += [{"title": r["title"], "detail": place(r["location_id"]) + " — " + r["status"].replace("_", " "), "page": "Maintenance"} for r in open_requests]
            arrivals = [e for e in ring if e["signal"] in {"doorbell", "person"} and now - e["at"] < timedelta(hours=24)]
            if arrivals:
                attention.append({"title": "Ring arrival signals", "detail": f"{len(arrivals)} recent signals. Review arrivals; identity unverified"
                    + (" • Simulation" if all(e["simulated"] for e in arrivals) else ""), "page": "Visitors"})
            if unverified:
                attention.append({"title": f"{len(unverified)} devices unverified", "detail": "Operational status unavailable. Contact Admin for verification.", "page": "Security"})
            status = "Incident active" if active_incidents else "Degraded systems" if offline else "Attention needed" if attention or unverified else "Normal"
            buildings = [n for n in nodes if n.kind == K.BUILDING]
            coverage = {label: bool(buildings) and all(self.allowed(p, "structure", b.id) for b in buildings)
                for label, p in {"visitors": P.VISITORS_READ, "maintenance": P.MAINTENANCE_READ,
                    "incidents": P.INCIDENTS_READ, "devices": P.HARDWARE_READ}.items()}
            complete = all(coverage.values())
            return {"at": now, "buildings": buildings, "nodes": nodes, "people": people,
                "can_simulate": simulation_mode and self.allowed(P.SIMULATION_RUN, "simulation", "ring") and self.allowed(P.RING_READ, "simulation", "ring"),
                "operator_name": self.repo.get_person(auth.principal.person_id).name,
                "status": status if complete or attention else "Status unavailable", "coverage": coverage,
                "status_note": "Based on authorized records; physical systems remain unverified." if complete else "Partial scope or missing read permissions. This is not a building-wide status.",
                "attention": attention, "counts": {"visitors": sum(v["start"].date() <= now.date() <= v["end"].date() for v in visitors),
                    "maintenance": len(open_requests), "incidents": len(active_incidents), "offline": len(offline)},
                "unverified_devices": len(unverified), "maintenance": maintenance, "announcements": announcements,
                "visitors": visitors, "incidents": [{"id": i.emergency_id, "description": i.description,
                    "status": i.status, "severity": i.severity, "locations": [place(z) for z in i.affected_zone_ids]} for i in incidents],
                "devices": devices, "ring": ring, "activity": activity[:100],
                "access_people": [{"id": p.id, "name": p.name} for p in scoped.list_people() if self.allowed(P.ACCESS_CHECK, "person", p.id)],
                "access_zones": [{"id": z.id, "name": z.name} for z in zones if self.allowed(P.ACCESS_CHECK, "location", z.id)],
                "permissions": [{"id": p.id, "person": who(p.person_id), "zones": [place(z) for z in p.allowed_zone_ids],
                    "start": p.valid_from, "end": p.valid_until, "reason": p.reason} for p in permissions],
                "actions": {action: [n.id for n in nodes if n.kind in {K.BUILDING, K.FLOOR, K.LOCATION, K.UNIT, K.BUSINESS, K.ROOM}
                    and self.allowed(p, "structure", n.id)] for action, p in {"announce": P.ANNOUNCEMENTS_PUBLISH,
                        "maintenance": P.MAINTENANCE_CREATE, "invite": P.VISITORS_INVITE}.items()}}
