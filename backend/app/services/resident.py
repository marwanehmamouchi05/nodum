"""Personal Resident projection and mutations over Phase D operational storage."""
from datetime import datetime
from app.models.authorization import Permission as P, Role
from app.models.manager import VisitorInput, MaintenanceInput
from app.services.manager import ManagerService
from app.services.resident_boundary import affiliations, physical_path
from app.services.errors import DomainError


class ResidentService:
    def __init__(self, authorization, *, ai_context=False):
        self.auth, self.repo = authorization, authorization.repository
        self.ai_context = ai_context

    def allowed(self, permission, kind, identifier):
        return self.auth.allowed(permission, kind, identifier) and (
            not self.ai_context or self.auth.allowed(P.AI_USE, kind, identifier))

    def homes(self):
        user = self.repo.get_auth_user(self.auth.principal.user_id)
        if not user or not user.active:
            return []
        if not any(a.user_id == user.id and a.role == Role.RESIDENT and a.active and
                   (a.expires_at is None or self.auth.now < a.expires_at) and self.auth.ancestors(a.scope_id)
                   for a in self.repo.list_role_assignments()):
            return []
        result = []
        for affiliation in affiliations(self.auth):
            node = self.repo.get_structure_node(affiliation.target_id)
            if node and node.kind.value == "unit" and self.allowed(P.LOCATIONS_READ, "structure", node.id):
                result.append((affiliation, node))
        return result

    def target(self, affiliation_id, permission):
        homes = self.homes()
        choices = [(a, n) for a, n in homes if affiliation_id is None or a.id == affiliation_id]
        if len(choices) != 1:
            raise DomainError(403, "Choose one of your active unit assignments")
        affiliation, node = choices[0]
        if not self.allowed(permission, "structure", node.id):
            raise DomainError(403, "This action is unavailable for your unit")
        return affiliation, node

    def create_visit(self, payload):
        with self.repo.transaction():
            _, node = self.target(payload.affiliation_id, P.VISITORS_INVITE)
            record = ManagerService(self.auth).invite(VisitorInput(location_id=node.id, name=payload.name.strip(),
                starts_at=payload.starts_at, ends_at=payload.ends_at))
            record.update(note=payload.note, logical_authorization={"destination_id": node.id,
                "valid_from": record["starts_at"], "valid_until": record["ends_at"],
                "revoked_at": None, "physical_access": False})
            self.repo.save_operational_record("visitor", record)
            return self.visit_view(record)

    def create_maintenance(self, payload):
        with self.repo.transaction():
            _, node = self.target(payload.affiliation_id, P.MAINTENANCE_CREATE)
            record = ManagerService(self.auth).create("maintenance", MaintenanceInput(location_id=node.id,
                title=payload.title.strip(), description=payload.description.strip(), priority=payload.priority))
            return self.maintenance_view(record)

    def personal_records(self, kind, permission):
        homes = {n.id: n for _, n in self.homes()}
        field = "host_id" if kind == "visitor" else "reporter_id"
        return [r for r in self.repo.list_operational_records(kind)
                if r.get(field) == self.auth.principal.person_id and r.get("location_id") in homes
                and self.allowed(permission, kind, r["id"])
                and (binding := self.repo.get_resource_binding(kind, r["id"]))
                and homes[r["location_id"]].scope_id in self.auth.ancestors(binding.scope_id)]

    def detail(self, kind, identifier):
        with self.repo.transaction():
            permission = P.VISITORS_READ if kind == "visitor" else P.MAINTENANCE_READ
            record = next((r for r in self.personal_records(kind, permission) if r["id"] == identifier), None)
            if not record:
                raise DomainError(404, "This record is unavailable")
            return self.visit_view(record) if kind == "visitor" else self.maintenance_view(record)

    def cancel(self, identifier):
        with self.repo.transaction():
            record = next((r for r in self.personal_records("visitor", P.VISITORS_READ) if r["id"] == identifier), None)
            if not record:
                raise DomainError(404, "This visit is unavailable")
            if not self.allowed(P.VISITORS_INVITE, "visitor", identifier):
                raise DomainError(403, "You cannot cancel this visit")
            if record.get("checked_in_at") or self.auth.now >= datetime.fromisoformat(record["ends_at"]):
                raise DomainError(409, "An arrived or ended visit cannot be cancelled here")
            if not record.get("cancelled_at"):
                record["cancelled_at"] = self.auth.now.isoformat()
                if record.get("logical_authorization"):
                    record["logical_authorization"]["revoked_at"] = record["cancelled_at"]
                self.repo.save_operational_record("visitor", record)
                ManagerService(self.auth).journal("visitor.cancelled", record)
            return self.visit_view(record)

    def location_name(self, identifier):
        return next((n.name for _, n in self.homes() if n.id == identifier), "Your unit")

    def visit_view(self, record):
        now = self.auth.now
        start, end = datetime.fromisoformat(record["starts_at"]), datetime.fromisoformat(record["ends_at"])
        status = "cancelled" if record.get("cancelled_at") else "completed" if now >= end and record.get("checked_in_at") else "expired" if now >= end else "arrived" if record.get("checked_in_at") else "expected"
        return {"id": record["id"], "name": record["name"], "destination": self.location_name(record["location_id"]),
            "starts_at": record["starts_at"], "ends_at": record["ends_at"], "status": status,
            "note": record.get("note", ""), "physical_access": False,
            "logical_authorization": "Revoked" if status == "cancelled" else "Ended" if status in {"expired", "completed"} else "Scheduled" if now < start else "Active",
            "can_cancel": not record.get("checked_in_at") and not record.get("cancelled_at") and now < end
                and self.allowed(P.VISITORS_INVITE, "visitor", record["id"]), "demo": record.get("demo", False)}

    def maintenance_view(self, record):
        # Phase D notes default to operator-private. Only explicitly public replies
        # may be included; operator names, assignments and internal notes stay private.
        return {"id": record["id"], "title": record["title"], "description": record["description"],
            "location": self.location_name(record["location_id"]), "priority": record["priority"],
            "status": "submitted" if record["status"] == "new" else record["status"],
            "created_at": record["created_at"], "updated_at": record["updated_at"],
            "updates": [{"status": "submitted" if h["status"] == "new" else h["status"], "at": h["at"],
                "message": h.get("public_message", "")} for h in record.get("history", [])], "demo": record.get("demo", False)}

    def notices(self):
        with self.repo.transaction():
            homes = [(a, n) for a, n in self.homes() if self.allowed(P.ANNOUNCEMENTS_READ, "structure", n.id)]
            result = []
            for r in self.repo.list_operational_records("announcement"):
                target = self.repo.get_structure_node(r["location_id"])
                binding = self.repo.get_resource_binding("announcement", r["id"])
                if not target or not binding or binding.scope_id != target.scope_id:
                    continue
                if r["audience"] not in {"all", "residential"} or datetime.fromisoformat(r["publish_at"]) > self.auth.now:
                    continue
                if not any(target.id in physical_path(self.repo, n.id) and
                           target.organization_id == n.organization_id and self.auth.ancestors(target.scope_id) for _, n in homes):
                    continue
                result.append({"id": r["id"], "title": r["title"], "message": r["message"],
                    "published_at": r["publish_at"], "expires_at": r.get("expires_at"),
                    "expired": bool(r.get("expires_at") and datetime.fromisoformat(r["expires_at"]) <= self.auth.now),
                    "audience": "Residents" if r["audience"] == "residential" else "Everyone in this area", "demo": r.get("demo", False)})
            return sorted(result, key=lambda r: r["published_at"], reverse=True)

    def notice_detail(self, identifier):
        record = next((r for r in self.notices() if r["id"] == identifier), None)
        if not record:
            raise DomainError(404, "This notice is unavailable")
        return record

    def access(self):
        from app.models.access import AccessCheckInput
        from app.services.access import check_access
        person = self.auth.principal.person_id
        if not self.homes():
            return []
        result = []
        for permission in self.repo.list_permissions():
            if permission.person_id != person or not self.allowed(P.ACCESS_READ, "access_permission", permission.id):
                continue
            for identifier in permission.allowed_zone_ids:
                zone = self.repo.get_zone(identifier)
                if not zone or not self.allowed(P.LOCATIONS_READ, "location", identifier):
                    continue
                outcome = None
                if self.allowed(P.ACCESS_CHECK, "person", person) and self.allowed(P.ACCESS_CHECK, "location", identifier):
                    outcome = check_access(self.repo, AccessCheckInput(person_id=person, zone_id=identifier,
                        purpose="Resident personal access review"), self.auth.now, legacy_role_access=False)
                result.append({"area": zone.name, "status": "Allowed" if outcome and outcome.allowed else "Denied" if outcome else "Authorization recorded",
                    "reason": outcome.reason if outcome else "Current access has not been evaluated.",
                    "valid_from": permission.valid_from, "valid_until": permission.valid_until})
        return result

    def ring(self):
        from app.services.ring import identity
        homes = {n.scope_id for _, n in self.homes()}
        result = []
        for event in self.repo.list_ring_events():
            if event.signal not in {"doorbell", "person"} or not self.allowed(P.RING_READ, "ring_event", event.id):
                continue
            if any(d.external_device_id == event.source and d.external_account_key == identity(event.environment, event.account_id)
                   and self.allowed(P.HARDWARE_READ, "device", d.id)
                   and (b := self.repo.get_resource_binding("device", d.id)) and any(scope in self.auth.ancestors(b.scope_id) for scope in homes)
                   for d in self.repo.list_building_devices()):
                result.append({"id": event.id, "at": event.occurred_at, "message": "Someone is at your doorbell. Identity not verified.",
                    "simulated": event.account_id == "simulation.playground" or event.source.startswith("simulation:")})
        return sorted(result, key=lambda e: e["at"], reverse=True)[:10]

    def snapshot(self):
        with self.repo.transaction():
            homes = self.homes()
            visits = [self.visit_view(r) for r in self.personal_records("visitor", P.VISITORS_READ)]
            requests = [self.maintenance_view(r) for r in self.personal_records("maintenance", P.MAINTENANCE_READ)]
            notices, access = self.notices(), self.access()
            return {"name": self.repo.get_person(self.auth.principal.person_id).name,
                "units": [{"affiliation_id": a.id, "name": n.name, "demo": n.demo,
                    "floor": next((self.repo.get_structure_node(i).name for i in physical_path(self.repo, n.id)
                        if self.repo.get_structure_node(i).kind.value == "floor"), None),
                    "can_invite": self.allowed(P.VISITORS_INVITE, "structure", n.id),
                    "can_report": self.allowed(P.MAINTENANCE_CREATE, "structure", n.id)} for a, n in homes],
                "visitors": visits, "maintenance": requests, "notices": notices,
                "access": access, "access_status": "Active" if any(a["status"] == "Allowed" for a in access) else "Not evaluated" if access else "Not configured",
                "ring": self.ring(), "at": self.auth.now,
                "expected_today": sum(v["status"] == "expected" and datetime.fromisoformat(v["starts_at"]).date() == self.auth.now.date() for v in visits),
                "open_maintenance": sum(r["status"] not in {"resolved", "closed"} for r in requests)}
