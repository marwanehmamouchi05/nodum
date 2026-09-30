# Guest invitations, business appointments, emergencies, and access policy

The running backend uses a persistent SQLite repository. An in-memory
implementation remains for isolated tests. There is no AI decision logic,
physical hardware actuation, or caller authentication. Policy-guarded software
simulator commands are described in [building integrations](building-integrations.md).

The optional [agent layer](agent-layer.md) uses Bedrock to interpret requests and
explain results. It cannot authorize access: check_access calls this deterministic
policy, and proposed writes require explicit confirmation through existing domain
services. Model explanations are never permission credentials.

## Architecture

- FastAPI routes parse inputs and delegate to services. Dependencies supply the
  repository and a timezone-aware UTC clock.
- The invitation service validates authority, zones, identities, and overlap
  before registering the guest and storing the permission in one locked operation.
- Services depend on the Repository protocol. SQLiteRepository stores people,
  zones, permissions, work orders, businesses, appointments, emergencies/history,
  and pending agent actions; reads reconstruct validated models.
- SQLite transactions serialize service validation and writes across connections
  to the same database file and roll back failed operations. Nested scopes use
  savepoints. InMemoryRepository retains its original lock-based test behavior.
- The access engine receives explicit records and a request timestamp. It does
  not read the clock, repository, network, or AI output.
- The appointment service schedules visits without permissions. Check-in validates
  the appointment and visitor, then records the visitor, permission, and appointment
  transition together under the repository transaction.
- The emergency service validates operators, zones, and responder eligibility.
  Creation, additive assignments, and resolution each persist the incident and
  its chronological audit history together under the same repository transaction.
  Access checks consume an emergency snapshot inside that transaction.

## Journey transit policy

Journey orchestration adds an explicit, narrow transit context: a checked-in
business visitor may enter an unrestricted floor-0 lobby only if the exact
destination passes the normal business policy. Context validation, manager/responder
override, emergency restrictions and contractor work-order precedence run first.
Both lobby and destination emergency state must permit the business visitor.
Ordinary access requests and stored permissions are unchanged. Each journey
command rechecks all authorized journey zones before dispatch; an adapter never
grants permission. No residential or maintenance transit is inferred.

## Invitation policy

The existing resident_id field identifies the inviter and may refer to a resident
or manager. Unknown inviters return 404; other roles return 403.

Only non-restricted residential, lobby, and parking zones are guest-safe. Every
zone must exist (404 otherwise). Residents must also have each zone explicitly
listed in their guest_zone_ids authority. Managers may invite into any guest-safe
zone. Maintenance, business, emergency, and restricted technical zones are never
grantable through guest invitations, including by managers (403).

Guests are registered automatically after all checks pass. An existing guest ID
can be reused only with the same name and guest role; collisions return 409
without changing the person. An invitation cannot convert a contractor or another
role into a guest.

valid_for_hours is an integer from 1 through 24 (default 3). Invalid inputs return
422. All timestamps must be timezone-aware and are normalized to UTC. Permissions
require valid_from < valid_until. Validity includes the start and excludes expiry:

    valid_from <= requested_at < valid_until

Zone IDs are deduplicated and sorted. Any overlapping interval for the same guest
and at least one shared zone returns 409, including pending future permissions.
This applies to repeated requests and invitations from different inviters.
Disjoint zones and renewal exactly at expiry are allowed. Failed invitations do
not partially register people or permissions. Duplicate checks and writes share
the same transaction, including concurrent HTTP requests using the same database.

Created permissions retain a deterministic content-derived ID, inviter ID,
creation timestamp, reason, zone scope, and validity window. Old permissions are
retained for inspection and survive restarts. This is persisted permission history,
not a tamper-proof audit log. IDs are references, not authentication credentials.

## Exact engine precedence

1. Validate context and require request person/zone IDs to match the supplied
   records. Inconsistent IDs or invalid context are denied before any override.
   Validate emergency records and their status/history consistency; malformed
   records or duplicate incident IDs fail closed, including for privileged roles.
2. Preserve the existing manager/emergency-responder building-wide override.
3. Apply all active incidents affecting the requested zone. Guests, business
   visitors, and all other non-privileged roles are denied. Contractors may
   proceed to the work-order check only for a MAINTENANCE zone when every applicable
   incident is a water leak or elevator failure and explicitly assigns them.
   Fire/security incidents block contractors even if an assignment exists.
   Multiple incidents combine restrictively; resolving one does not clear others.
4. Contractors are allowed only by an active work order matching their person ID
   and the requested zone. Temporary permissions are ignored. If several orders
   match, use the lexicographically smallest order ID for the decision reason.
   Work orders currently have an active flag and no scheduled time window.
5. Guests require a guest-safe requested zone and exactly one matching permission
   valid at the request time. Invalid permission data or multiple active matches
   fail closed. Expired or future permissions cannot authorize entry.
6. Business visitors require a non-restricted BUSINESS zone and exactly one
   currently valid permission. The permission must reference exactly one checked-in
   appointment and one active business. Visitor ID/name, business ownership,
   destination, check-in/start timestamp, expiry, and permission provenance must
   agree. The permission must contain only the appointment's exact destination.
   Missing, invalid, or inconsistent records fail closed. No access follows merely
   from a scheduled appointment.
7. Deny everything else. Residents and other roles do not gain a new direct-entry
   policy from their invitation authority.

## Emergency mode

An incident records emergency_id, emergency_type, severity, affected_zone_ids,
description, status, created_at, resolved_at, created_by, resolved_by, assigned
responder IDs, and a chronological history of actions with actor IDs and UTC
timestamps. History records triggering, responder additions, and resolution.

Supported types: water_leak, fire_alarm, elevator_failure, security_incident.
Severities: low, medium, high, critical. Severity is recorded for operational
triage; it does not weaken access restrictions or grant entry. Status is active
or resolved. A resolved incident cannot be reopened or assigned new responders.

Creation requires a unique ID, at least one existing zone, a nonblank description,
and an existing manager or emergency responder as created_by. Affected zone and
assignment IDs are sorted and deduplicated. The ID active is reserved for the
active-list endpoint. Callers cannot provide server-owned timestamps, history,
or status through the creation endpoint.

Only existing managers/emergency responders may create incidents, assign
responders, or resolve incidents. These checks validate stored roles, not caller
authentication. Assigned people must be emergency responders or eligible
contractors. A contractor is eligible only for water_leak/elevator_failure and
must have an active work order covering at least one affected MAINTENANCE zone.
Assignments never create permissions, change roles, or substitute for work orders.
At each access decision the work order must still be active and match the exact
requested maintenance zone. Assigned responders do not get additional authority
beyond their existing emergency-responder role.

Assignments are additive. Each audit event names only newly assigned responders;
an entirely repeated assignment returns 409. Mixed valid/invalid assignments
make no changes. Resolution records resolved_at and resolved_by and appends the
resolution event atomically. Duplicate resolution returns 409. Timestamps are
aware UTC and cannot precede the last audit event. No edits or deletion of prior
audit events are exposed through the API.

All active incidents affecting a zone apply, regardless of permission creation
time. Unaffected zones retain normal policy. Resolved incidents no longer block
access: normal permissions and work orders are evaluated again and still must be
valid. The engine evaluates the supplied current emergency state; it is not a
historical replay API. Resolution does not renew an expired permission.

Guest invitations and business check-ins remain record/permission workflows.
They do not authorize entry into an affected zone: POST /access/check always
applies current emergency restrictions. The engine uses explicit records only,
with no AI calls or clock reads.

### Emergency endpoints

| Method | Path | Result |
| --- | --- | --- |
| POST | /emergencies | 201: trigger incident |
| GET | /emergencies | 200: all incidents, sorted by ID |
| GET | /emergencies/active | 200: active incidents only |
| GET | /emergencies/{emergency_id} | 200: incident including history |
| POST | /emergencies/{emergency_id}/responders | 200: assign eligible responders |
| POST | /emergencies/{emergency_id}/resolve | 200: resolve incident |

Unknown incidents, zones, actors, or responders return 404. Ineligible roles or
contractors return 403. Duplicate IDs/transitions/assignments return 409.
Invalid enums, empty zones, malformed requests, or backdated transitions return 422.

Example water-leak body for POST /emergencies:

    {
      "emergency_id": "leak-001",
      "emergency_type": "water_leak",
      "severity": "high",
      "affected_zone_ids": ["utility-room"],
      "description": "Water leaking from the supply valve",
      "created_by": "manager-1",
      "assigned_responder_ids": ["plumber-1"]
    }

For an elevator failure use a new ID, emergency_type elevator_failure, zone
machine-room, and assigned contractor-1. To add an emergency responder:

    {"assigned_by": "manager-1", "responder_ids": ["responder-1"]}

Resolve with:

    {"resolved_by": "manager-1"}

## Business appointments and check-in

Business records include an ID, name, active flag, and destination zone IDs.
Appointments include visitor ID/name, business ID, a single destination zone ID,
appointment time, before/after windows in minutes, status, creation time, and an
optional check-in time. No employee/host model is needed for this initial flow;
business ownership is checked against the stored Business record.

Appointment creation requires an active business, an existing non-restricted
BUSINESS zone owned by that business, and an aware appointment time at or after
the server clock. It creates neither a person nor an access permission.

Before-window: 0–120 minutes, default 15. After-window: 1–480 minutes, default 60.
All timestamps normalize to UTC. Naive dates, out-of-range dates/windows, and
attempts to supply server-owned status/timestamps return 422.

Check-in requires both visitor_id and visitor_name to exactly match the appointment.
The clock must satisfy:

    appointment_time - access_before_minutes <= now
    now < appointment_time + access_after_minutes

It must also be at or after creation. Only scheduled appointments may check in.
The service revalidates business activity, zone ownership/type/restriction, and
person identity at check-in. An existing person must already be a business visitor
with the same name; other roles are never converted. New people are registered as
BUSINESS_VISITOR only when check-in succeeds.

The permission starts at the actual check-in timestamp (never retroactively) and
ends at appointment_time + access_after_minutes. It contains exactly the one
destination zone. Other offices of the same business, unrelated businesses,
residential floors, maintenance/technical spaces, lobbies, and parking are denied.
Common-area traversal is deliberately not granted implicitly; a future explicit
common-zone policy can extend this without broadening today's permissions.

Repeated check-in and overlapping permissions for the same visitor/destination
return 409 without extending access or creating duplicate permissions.
Nonoverlapping later appointments may reuse an existing business visitor.
Permission records include appointment/business IDs, a deterministic permission
ID, issuer provenance, creation time, validity, and reason. Appointment status
transitions from scheduled to checked_in with checked_in_at recorded atomically.
Cancelled is a modeled terminal state and cannot check in; no cancellation
endpoint is included. Expiry is evaluated at decision time, not by a background
status update.

The engine receives appointment/business snapshots through the access service,
and validates these against the permission. Inactive businesses and cancelled
appointments therefore cannot authorize access even if an old permission remains.

### Endpoints

| Method | Path | Result |
| --- | --- | --- |
| POST | /appointments | 201: schedule appointment |
| GET | /appointments | 200: appointments sorted by ID |
| GET | /appointments/{appointment_id} | 200: appointment details |
| POST | /appointments/{appointment_id}/check-in | 200: checked-in appointment and permission |

Unknown appointments/businesses/zones return 404. Unauthorized destinations,
inactive businesses, visitor mismatches, and outside-window arrivals return 403.
Duplicate IDs, identity collisions, overlaps, and repeated check-in return 409.

Create body example (choose an appointment_time in the future):

    {
      "id": "appt-001",
      "visitor_id": "visitor-001",
      "visitor_name": "Sam",
      "business_id": "atlas-dental",
      "destination_zone_id": "office-106",
      "appointment_time": "2026-10-01T10:00:00Z",
      "access_before_minutes": 15,
      "access_after_minutes": 60
    }

Check-in body:

    {"visitor_id": "visitor-001", "visitor_name": "Sam"}

After check-in, use the existing POST /access/check with the visitor's person_id,
zone_id office-106, and purpose. GET /guests/permissions continues to list guest
permissions only; business permission details are returned by check-in.

## Demo data and verification

Existing contractor-1, guest-1, machine-room, floor-5, and wo-001 remain.
resident-1 may invite into floor-5 and lobby. manager-1 is the demo manager.
atlas-dental is Atlas Dental on floor 1, Office 106 (zone office-106). No demo
appointments or business access permissions are pre-created.
utility-room is a restricted maintenance zone with plumber-1 and active work
order wo-plumbing-001. The existing machine-room/contractor-1/wo-001 support the
elevator incident demo. responder-1 is a demo emergency responder. No incident
is created automatically at startup.

From the backend directory in PowerShell:

    .\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider
    .\.venv\Scripts\python.exe -m pip check
    .\.venv\Scripts\python.exe -B -c "from app.main import app; print(list(app.openapi()['paths']))"

Tests exercise services, the pure engine, concurrent invitations, and the actual
FastAPI ASGI interface without external services or additional dependencies.

## Remaining deployment limits

Inviter IDs are validated against trusted stored roles, but HTTP callers are not
authenticated. Anyone able to reach the API can claim an existing resident or
manager ID, query permission history, or request an access decision for another
person. Bind these operations to authenticated principals before public or
physical-access use.

Business scheduling and appointment listing/retrieval also lack caller
authentication and business-staff authorization. Checking a supplied visitor
ID/name against an appointment is record matching, not proof of physical identity.
Appointment details contain personal data. Authentication, scoped business access,
and a trusted check-in identity-verification mechanism remain required before
public or physical-access deployment.

Emergency management has the same caller-authentication limitation: a caller
can claim a stored manager/responder ID. Incident resolution is a recorded operator
assertion, not sensor confirmation that a physical hazard is cleared. The prototype
does not control evacuation, egress, fire alarms, or physical locks and is not a
certified life-safety system. Incident state and append-only application audit
events persist in SQLite, but local database access can tamper with them. Production
operation needs protected backups, authenticated operators, and a reviewed
hardware/egress safety design.

State and incident history survive restart and are shared by connections using
the same SQLite file. See [persistence](persistence.md) for initialization,
transaction semantics, and backup limitations. Revocation, access-decision auditing,
tenant isolation, rate limits, work-order scheduling, and emergency verification
remain future work.
