# External building integration contract — version 1

Implemented on the isolated engineering branch. Companion:
[external test architecture](DIGITAL_TWIN_TESTING_ARCHITECTURE.md). No simulator UI
or physical command channel is implied.

## Trust and onboarding

Initial organization/recovery authority is provisioned through the trusted installer
(`backend/provision_admin.py` for an empty installation). There is no anonymous
organization/bootstrap API. The disposable drill provisions this root once on the
server side. Its external participant receives no database path or repository object.

Every external application uses ordinary Nodum sessions: `GET /auth/session` obtains
an anonymous cookie + CSRF; `POST /auth/login` sends username/password plus exact
Origin and `X-CSRF-Token`. Preserve the rotated secure cookie and new CSRF token.
Write routes require both; a successful login does not grant building authority.
Passwords and private broker configuration must never enter a scenario/report.

| HTTPS interface | Existing contract / authority |
|---|---|
| `PUT /admin/nodes/{id}` | `StructureNode`; existing parent, organization/building consistency and role ceilings; hierarchy configured in parent-first order |
| `POST /admin/accounts` | `{name,username,password,scope_id}`; account creation does not automatically assign operational roles |
| `PUT /authorization/assignments/{id}` | `{id,user_id,role,scope_id,permissions}`; caller must have delegation and each permission being delegated |
| `DELETE /authorization/assignments/{id}` | Revocation; subsequent requests/observations recheck persisted authority |
| `PUT /admin/devices/{id}/mapping` | `{location_id}`; both device and location must be authorized and belong to the same building |
| `GET /structure/nodes/{id}` | Authorized device/place identity, not verified capabilities or health |
| `GET /structure/devices/{id}/context` | Scoped configuration context; no implied physical availability |
| `GET /manager/activity?scope_id=...&limit=...&cursor=...` | New bounded operational-journal contract below; tenant-only product roles use their dedicated workspace endpoints |
| `GET /manager/snapshot` | Existing mixed operational projection; not an unlimited event export |
| `GET /health` | Process liveness only; not database/broker/device commissioning |

Account/assignment IDs returned by Nodum must be captured, not guessed or obtained
from SQLite. Scope IDs in request bodies are validated as configuration, never used
as proof of authority. `demo=true` and `connection_path=simulation` truthfully label
virtual equipment. `StructureNode.capabilities` remains empty until a reviewed
adapter capability model is connected to that inventory.

## MQTT contact v1

Exact topic: `nodum/v1/contact/{percent-encoded-building-id}/{percent-encoded-device-id}`.
Encode each complete identifier with no extra safe characters. No wildcard binding.
The registered node must be a `device` with `device_type=sensor`, in the bound
building, beneath an authorized location. The configured integration is metadata;
the optional server-side collector is explicitly started separately.

```json
{"event_id":"contact-0001","observed_at":"2026-10-15T12:00:00+00:00","state":"open"}
```

`event_id`: 1–128 ASCII letters/digits/underscore/hyphen. `observed_at`: explicit
timezone-aware string, accepted from five minutes ago through 30 seconds ahead.
`state`: exactly `open` or `closed`. UTF-8 JSON object, no unknown or duplicate keys,
maximum 1,024 bytes. Retained messages are rejected. Topic is selected by server
binding, not by a payload's claimed tenant. MQTT 3.1.1, QoS 1, verified TLS hostname/CA
and dedicated username/password; broker publication/subscription ACLs are separate.

The collector's Nodum operator needs `hardware.configure` and `activity.read` at the
device's scope, refreshed per event. Revoked user/grant or invalid binding rejects
the event even if broker credentials remain accepted. An identical event ID/content
is a duplicate; conflicting content for the same device/source ID is rejected.

Persistent capacity defaults to 100,000 contact observations per device; private
`mqtt_collect.py` configuration may set `max_observations` from 1 to 1,000,000.
Capacity and insertion are checked in one SQLite transaction. At capacity a new ID
is rejected, duplicates remain duplicates, old audit records are not deleted, and
collector status becomes `capacity_reached` (CLI failure status). Budgets must be
consistent between collectors. This is not a fleet/global disk quota or auto-retention.

## Independent observation

```json
{"schema_version":1,"items":[{"id":"opaque-server-id","at":"2026-10-15T12:00:01+00:00","action":"sensor.contact.open","resource_id":"device-a","location_id":"room-a","source":"MQTT contact observation","source_event_id":"contact-0001","observed_at":"2026-10-15T12:00:00+00:00","simulated":true}],"next_cursor":null}
```

This API returns operational journal rows, not all historical Ring/credential/
actuator/appointment records. Limit 1–100, default 100. Cursor is opaque, validated,
versioned navigation, not authorization. Follow `next_cursor` until null; an empty
ownership-filtered page may still have a cursor. Ordering is existing UTC ISO `at`,
then ID, descending; stable ties, no OFFSET. Refresh from the first page to see new
rows inserted ahead of a cursor. Revocation/ownership changes can change visibility.
Old MQTT rows may lack optional `source_event_id`.

The evaluator must compare source correlation, device, timestamp, normalized state,
row count and simulation flag against what it sent. A 200, PUBACK or “subscribed”
label alone cannot establish ingestion. Error statuses include 401 sign-in, 403
authority, 422 invalid input/cursor, and transport/storage failures. The MQTT wire
has no Nodum application acknowledgment topic; check durable API observations and
server counters separately. Rejection counters deliberately contain no payloads.

## Failure and command limitations

Current clean-session reconnect resubscribes; messages published while offline may
be lost. No exactly-once/offline-delivery SLA. Storage faults stop the collector;
capacity, malformed input and revoked authority are separately testable rejection
conditions. No real device identity, general device health or door state is inferred.

Legacy software actuator APIs are fail-closed for scoped mutation routes and do not
bridge configured product devices. They are not a public physical-command interface
for the future lab. Pure simulator contracts remain testable separately. No durable
physical acknowledgment/reconciliation channel exists; ASTRA-HW-001 blocks one.
Official Ring linking/playground evidence is separate from MQTT and custom scenarios.
