# Guest invitations and access policy

This prototype uses one process-local repository. There is no database, AI
decision logic, hardware actuation, or caller authentication.

## Architecture

- FastAPI routes parse inputs and delegate to services. Dependencies supply the
  repository and a timezone-aware UTC clock.
- The invitation service validates authority, zones, identities, and overlap
  before registering the guest and storing the permission in one locked operation.
- Services depend on the Repository protocol. InMemoryRepository owns people,
  zones, permissions, and work orders and returns defensive copies.
- Transactions serialize reads and writes within this process. They do not
  provide general rollback; the service completes validation before writing.
- The access engine receives explicit records and a request timestamp. It does
  not read the clock, repository, network, or AI output.

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
5. Deny everything else. Residents and other roles do not gain a new direct-entry
   policy from their invitation authority.

## Demo data and verification

Existing contractor-1, guest-1, machine-room, floor-5, and wo-001 remain.
resident-1 may invite into floor-5 and lobby. manager-1 is the demo manager.

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

State and audit history disappear on restart and are not shared between workers.
Use one process for this prototype. Revocation, persistent decision auditing,
tenant isolation, rate limits, work-order scheduling, and emergency verification
remain future work. No database or integration has been introduced here.
