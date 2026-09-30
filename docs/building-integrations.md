# Building connectors and journeys

Nodum is the intelligent operating system for buildings. Ring provides the real
Partner API integration code for sensing and human entry; live account linking
still requires the authenticated adapters described in [Ring integration](ring-integration.md).
Access control, credentials, elevators and wayfinding currently use **software
simulators only**. No Kisi, SALTO, HID, elevator or lighting hardware is integrated.

## Architecture

`app/integrations/building.py` defines `AccessControlAdapter`, `ElevatorAdapter`,
`CredentialReaderAdapter` and `WayfindingAdapter`. A server-owned `ConnectorRegistry`
selects implementations. Public requests cannot load providers, URLs or code.
The simulator adapters perform pure state transformations and contain no permission
logic. `BuildingService` performs fresh deterministic policy checks before dispatch.
`JourneyService` composes existing appointment/check-in services, policy decisions
and connector commands. Neither service requires AI or Ring availability.

All records use the shared Repository protocol and UTC timestamps. SQLite commits
simulated state and command audits in the same transaction. Identical command,
scan and journey IDs return their original result; changed content with the same
ID returns 409. Replayed results describe the original execution, never a new
unlock. Commands that reach an adapter produce a success/failure audit. A policy
denial or unavailable connector produces no actuator command; scans and journey
steps retain their outcomes. Direct denied action responses are not a complete
access-attempt audit trail.

Integration/device metadata is allowlisted, with no secret fields. Simulated
credential bindings store hashes rather than raw card values; these sample
credentials are not a physical identity-verification or secure NFC protocol.
Ring tokens remain in the existing separately encrypted account storage.

## Authorization and truthful status

Every actuator command requires an ALLOW decision for the person and requested
zone, a matching device-zone mapping and supported capability. Access points
protect exactly one mapped zone. Elevator controllers may serve multiple zones,
but each command authorizes one exact zone/floor/person. Floor access does not
grant another business on the same floor. There is no client-supplied floor override.

Guest, contractor and emergency precedence remains authoritative. A business
journey can additionally traverse an unrestricted ground-floor lobby only while
its exact business destination is authorized by a checked-in appointment. This is
an explicit policy-engine rule, not a connector permission. Both lobby and
destination emergency restrictions must pass. Ordinary `/access/check` behavior
and stored business permissions remain unchanged. Every journey command rechecks
all authorized journey zones. Expired appointments, incidents and identity/zone
mismatches deny further actuation. There is no new walk-in access grant.

Unlocks, including `unlock`, are bounded to 1–30 seconds and no later than the
permission expiry. Status projects expired locks back to locked and clears expired
elevator/wayfinding authorization. An elevator call records a requested floor;
it does not report cabin movement. Journey route corridor labels are guidance
waypoints, not new permission-bearing zones. No continuous indoor tracking is inferred.
`current_confirmed_zone_id` starts null and changes only through explicit,
ordered, mapped simulator confirmations. Ring motion cannot serve as one of
these confirmations. A verified Ring motion/button event can be referenced as
arrival context; it never proves identity or creates permission.

All four seeded simulator integrations start **disabled**. Without them, eligible
journeys return `manual_action_required`, with `executed: false`. Ring sensing,
appointments, emergencies and the existing agent tools keep working. Nothing
reports a door unlock without an executed simulated command. All command outcomes
and transition records are explicitly marked simulated.

## API foundation

All paths below have the `/building` prefix. The existing `/ring` APIs are preserved.

| Method and path | Purpose |
| --- | --- |
| GET /integrations | Provider inventory and enabled/mode flags |
| POST /integrations | Register simulator integration; `actor_id`, ID, name, kind |
| PATCH /integrations/{id} | Set `enabled` with operator `actor_id` |
| GET /devices | Device type, capabilities, physical location and simulation flag |
| POST /devices | Register simulated device, optional reader `target_device_id` |
| PUT /devices/{id}/mapping | Set `zone_ids`, with operator `actor_id` |
| GET /devices/{id}/status | Device, mapping, availability and simulated state |
| PATCH /devices/{id}/connection | Simulate online/offline with operator `actor_id` |
| POST /devices/{id}/actions | ID, person, zone, purpose, command, optional journey ID/duration; fresh policy required |
| GET /actuator-events | Historical commands, policy decisions and outcomes |
| POST /credentials | Bind ID, `kind`, `value`, person; operator `actor_id` |
| POST /credential-scans | ID, reader ID, credential kind/value, zone, optional journey ID |
| GET /credential-events | Resolved person and policy/actuator outcome; no raw credential |
| POST /journeys | Person, start/destination, purpose, optional appointment/arrival-event IDs |
| GET /journeys | Journey list |
| GET /journeys/{id} | Decisions, steps, route and current confirmed zone |
| POST /journeys/{id}/transitions | ID, mapped simulator source device ID, next zone ID |
| GET /journeys/{id}/transitions | Confirmed events ordered by timestamp and ID |
| POST /demo/atlas-dental | Explicitly run the backend demo |
| POST /ring/accounts/{account}/devices/{device}/register | Import an actual discovered Ring device; body `zone_id`; existing authenticated Ring principal required |

Ring imports use the existing documented discovery service and enforce its owner
check. Imported inventory is read-only sensing, with `simulated: false`; it cannot
execute simulator actions. Its connectivity is a **discovery snapshot**, not live
health monitoring. Mapping may be edited by an operator without creating access.
Full request schemas are available in FastAPI OpenAPI.

## Atlas Dental demo

Start the backend locally as described in [deployment](deployment.md), then run:

```powershell
$base = 'http://127.0.0.1:8000'
$journey = Invoke-RestMethod -Method Post -Uri "$base/building/demo/atlas-dental" `
  -ContentType 'application/json' `
  -Body '{"id":"video-take-1","actor_id":"manager-1","connect_simulators":true}'
$journey | ConvertTo-Json -Depth 12
```

This explicitly enables the four demo simulators, creates a current Atlas Dental
appointment through the existing service, checks the visitor in, and evaluates
the journey. Four audited simulated commands unlock the lobby entrance, request
the elevator at the lobby, authorize Floor 1 / Office 106, and illuminate:

`Lobby → Elevator → Floor 1 corridor → Atlas Dental - Office 106`

The destination door is not automatically unlocked; an authorized scan/action
can operate it. Residential, maintenance and unrelated business zones stay denied.
The arrival context is explicitly simulated in this convenience demo; it is not
a fabricated signed Ring webhook. Reuse the request ID to inspect the same result;
use a new ID for another appointment/take.

For Ring-only behavior, use a different ID and `connect_simulators:false`. The
journey will not dispatch connectors even if a previous demo enabled them. It
returns “Visitor verified; manual door action required.”

To demonstrate a QR scan at Office 106, register a `qr_mobile` credential with the
returned `person_id`, then POST a scan using `reader_id: demo-office-reader`,
`zone_id: office-106`, and the same credential kind/value. A lobby scan also needs
the returned journey ID for narrow transit authorization. The seed resident NFC
value `DEMO-RESIDENT-NFC` resolves `resident-1` but follows existing policy, which
does not yet grant residents ordinary access; it correctly denies rather than
inventing a resident entitlement.

Confirm lobby entry using source `demo-reader`, followed by Office 106 using
`demo-office-reader`, with unique transition IDs. These are deliberate simulator
events for the demo, not proof that a human physically moved.

## Persistence and production boundaries

Migration 3 adds `building_integrations`, `building_devices`,
`device_zone_mappings`, `device_states`, `credentials`, `credential_events`,
`actuator_events`, `journeys`, and `journey_transitions`. JSON is model-validated;
service transactions validate references. Credentials have a unique fingerprint
index and transitions a journey index. New tables do not have SQL foreign keys
for JSON references. Seeding inserts missing IDs only: four disabled integrations,
six devices/mappings/states and one demo NFC binding. Restarts do not reset
configuration, actions, appointments or confirmed progress.

The prototype has no caller authentication for generic building APIs. Operator IDs
are role-checked records, not authenticated identities. Keep these routes behind
a private/authenticated gateway. Before connecting physical hardware, add verified
principals, tenant/device authorization, trusted credential enrollment and source
events, rate limiting and egress/life-safety review. Do not make these simulators
an unrestricted public administration surface.

Future physical adapters also require durable outbound command delivery,
manufacturer idempotency/reconciliation, feedback and revocation handling. A
SQLite transaction cannot roll back physical motion. Current simulator expiry is
a status projection, not a background physical relock service. In-memory test
transactions serialize operations but do not roll back writes; SQLite does.
Audit retention/pagination and durable tamper-resistant logs remain future work.

The frontend can now build an Integrations/Mapping screen, simulated device status
cards, credential scan controls, a journey timeline and Atlas Dental demo from
these endpoints. Render `simulated`, `executed`, decision reasons and manual steps
explicitly. No frontend changes are included in this implementation.
