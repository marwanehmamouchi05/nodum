# Guest invitations, business appointments, and access policy

This prototype uses one process-local repository. There is no database, AI
decision logic, hardware actuation, or caller authentication.

## Architecture

- FastAPI routes parse inputs and delegate to services. Dependencies supply the
  repository and a timezone-aware UTC clock.
- The invitation service validates authority, zones, identities, and overlap
  before registering the guest and storing the permission in one locked operation.
- Services depend on the Repository protocol. InMemoryRepository owns people,
  zones, permissions, work orders, businesses, and appointments and returns
  defensive copies.
- Transactions serialize reads and writes within this process. They do not
  provide general rollback; the service completes validation before writing.
- The access engine receives explicit records and a request timestamp. It does
  not read the clock, repository, network, or AI output.
- The appointment service schedules visits without permissions. Check-in validates
  the appointment and visitor, then records the visitor, permission, and appointment
  transition together under the repository transaction.

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
the same lock, including concurrent HTTP requests in one process.

Created permissions retain a deterministic content-derived ID, inviter ID,
creation timestamp, reason, zone scope, and validity window. Old permissions are
retained for inspection. This is inspectable permission history, not a durable
or tamper-proof audit log. IDs are references, not authentication credentials.

## Exact engine precedence

1. Validate context and require request person/zone IDs to match the supplied
   records. Inconsistent IDs or invalid context are denied before any override.
2. Preserve the existing manager/emergency-responder building-wide override.
3. Contractors are allowed only by an active work order matching their person ID
   and the requested zone. Temporary permissions are ignored. If several orders
   match, use the lexicographically smallest order ID for the decision reason.
   Work orders currently have an active flag and no scheduled time window.
4. Guests require a guest-safe requested zone and exactly one matching permission
   valid at the request time. Invalid permission data or multiple active matches
   fail closed. Expired or future permissions cannot authorize entry.
5. Business visitors require a non-restricted BUSINESS zone and exactly one
   currently valid permission. The permission must reference exactly one checked-in
   appointment and one active business. Visitor ID/name, business ownership,
   destination, check-in/start timestamp, expiry, and permission provenance must
   agree. The permission must contain only the appointment's exact destination.
   Missing, invalid, or inconsistent records fail closed. No access follows merely
   from a scheduled appointment.
6. Deny everything else. Residents and other roles do not gain a new direct-entry
   policy from their invitation authority.

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

State and audit history disappear on restart and are not shared between workers.
Use one process for this prototype. Revocation, persistent decision auditing,
tenant isolation, rate limits, work-order scheduling, and emergency verification
remain future work. No database or integration has been introduced here.
