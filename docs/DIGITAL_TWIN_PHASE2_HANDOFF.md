# Phase 2 implementation handoff

Read `ARCHITECTURE_OVERVIEW.md`, `DIGITAL_TWIN_INTEGRATION_CONTRACT.md`,
`DIGITAL_TWIN_TESTING_ARCHITECTURE.md`, `SCALABILITY_ASSESSMENT.md` and current
`development-state.json`. This is implementation guidance, not permission for live
hardware or merging the engineering branch. Preserve the c8db547 meeting demo.

## Official release starting point

Use official GitHub `main` at tag `nodum-foundation-20261016`. See
[NODUM_RELEASE_BASELINE.md](NODUM_RELEASE_BASELINE.md) for publication and combined
verification. The review checkout below is historical. No lab or deployment starts
as part of this release.

## Verified review checkpoint (historical)

Implementation and acceptance evidence are committed at
`bcf5f9da1964cb462b1f44d307b5defc41776113`, based on
`af7a3e1d75d526d754c016f8bc12f77f5c2327ee`.
Historical review branch: `codex/astra-final-review` in
`C:/Users/marwa/.codex/worktrees/astra-final-review/nodum`; the final documentation
commit is its HEAD. The source checkpoint above remains the tested implementation.
Do not work in the original repository or change the frozen demo.

**Simulator backend: READY WITH LIMITATIONS** for the verified external HTTPS and
contact-v1 MQTT contracts. **Official Ring/hackathon: BLOCKED** pending authorized
runtime evidence. **Physical pilot: BLOCKED** pending hardware safety and deployment
acceptance. See `ASTRA_INDEPENDENT_REVIEW.md`, `ASTRA_RESOLUTION_LOG.md` and
`PHASE2_READINESS_DECISION.md`. Phase 2 has not started: a new user instruction is
required before creating the separate lab. Subsequent release authorization permits GitHub integration, but no live deployment.

## Starting proof and commands

Use the isolated review checkout and follow `DEVELOPER_ONBOARDING.md` for a
fresh Python 3.13 environment, optional Paho and separate test-broker environment.

```powershell
backend/.venv/Scripts/python.exe backend/scripts/external_contract_drill.py --broker-python .broker/Scripts/python.exe
backend/.venv/Scripts/python.exe backend/scripts/benchmark_activity.py --output artifacts/activity-benchmark.json
$reviewTemp = Join-Path $env:TEMP ('nodum-review-' + [guid]::NewGuid())
backend/.venv/Scripts/python.exe -m pytest -q --basetemp $reviewTemp
```

The external run uses seed 1729, creates two buildings via HTTPS, authenticates real
scoped sessions, sends MQTT contact samples, checks normalized correlation and
tenant isolation, exercises broker restart and revokes the collector assignment.
Its JSON report must say PASS with three persisted source events; supplemental
server counts are recorded=3, duplicate=1, rejected=2, failed=0. Treat other results
as failure, not as evidence to rewrite expected assertions. Runtime timestamps,
ports, IDs and credentials are fresh; the scenario decisions remain reproducible.
The review [evidence](verification/review-20261016.json) records PASS in 20.97s,
including complete stop/restore and rejection after restored revocation. Its negative
observation window was 0.75s, not an indefinite-delivery guarantee. Restoring an older
backup requires reconciling later revocations before reopening service. Capture
future stdout to a new artifact/report file. These commands are for future changes;
the completed 1,085 backend and 272 SQLite checks need not be repeated for docs.

## Recommended separate project

```text
building_lab/
  profiles/        # buildings, actors, devices and evidence requirements
  scenarios/       # versioned declarative definitions + seeds and budgets
  transports/     # authenticated HTTPS, exact-topic MQTT; no Nodum imports
  scheduler/      # relative timing, faults, reconnect, cancellation
  evaluator/      # deterministic invariants + mutation tests
  reports/        # redacted observations and versioned verdict schema
  fixtures/       # isolated server bootstrap/orchestration, kept separate
  tests/          # engine, evaluator and end-to-end acceptance
```

First port the small client into reusable external API/session and MQTT transport
classes. Keep its oracle independent. Define a scenario schema before adding AI.
Validate scenario capability/risk class and whitelist loopback endpoints by default.
Remote testing requires a separately authorized target allowlist and secret source.

## Initial models

- Buildings: small residential, commercial and mixed-use logical profiles, plus
  disconnected/partially connected variants. Do not attach unsupported hardware.
- Devices: contact publisher v1 with exact JSON/topic; modeled connectivity, delay,
  retained/replay/conflict inputs and per-device budgets. Historical wayfinding and
  access simulators are separate component fixtures, not physical endpoints.
- Actors: recovery/bootstrap operator, Admin, Manager, Resident, Business Admin/Staff,
  visitor and unauthorized caller. Reuse existing auth/affiliation contracts; role
  labels alone grant no authority. Root fixture authority must not be reused as the
  ordinary Manager or device operator in isolation tests.
- Policies: active/expired/revoked grant and affiliation; expected private ownership;
  no physical grants inferred from visitor creation or a camera signal.

## Acceptance sequence

1. Launch isolated Nodum + TLS broker with no inherited provider credentials.
2. Bootstrap initial recovery organization through the trusted fixture/installer.
   All ordinary building/device/account setup goes through supported APIs.
3. Verify each role's positive control, then wrong-building/guessed ID denial.
4. Emit contact events and compare source ID, timestamp, device association,
   normalized action and durable cardinality through paged HTTPS activity reads.
5. Exercise duplicate, conflict, malformed, retained, stale/future inputs. Assert
   unchanged durable outcomes and inspect independent transport evidence.
6. Restart broker, reconnect, deliver a fresh event. Do not require replay of events
   published during downtime: current clean sessions are explicitly lossy.
7. Revoke Nodum operator authority while broker identity remains valid; verify no
   new event appears within a specified bounded observation window. Separately
   revoke broker credentials in a broker-specific scenario when implemented.
8. Exhaust a deliberately small contact budget in the fixture; new IDs must fail,
   duplicates remain idempotent, restart must not reset capacity. No audit deletion.
9. Fail storage between journal and binding; SQLite must roll back. Use a server
   fault fixture, never let the external client write SQL to fake that outcome.
10. Produce a reproducible report, clean resources and fail on evaluator mutation
    tests. Only then add AI scenario proposals, followed later by visualization.

## Remaining boundaries and blockers

There is no anonymous onboarding, universal discovery, generic sensor payload,
production broker deployment, live actuator delivery state machine, physical
readback, complete history export, automatic retention, global fleet disk quota or
durable offline capture. Some non-contact projections still scan whole collections.
Large-scope concurrency/RSS and installed-OS commissioning remain untested. Local
Caddy/browser acceptance and bounded three-building read/write concurrency now pass;
see the final report.

Configured hardware inventory and historical simulator inventory are separate.
Scoped legacy actuator mutations are not exposed; do not bypass that boundary or
enable them to make the lab pass. A second external device/protocol proof needs an
actual supported adapter and reviewed API, not a superficial stub. Existing simulated
display/access contracts are component evidence only.

ASTRA-HW-001 blocks real command delivery/reconciliation; ASTRA-RING-002 and its
current-doc update require confirmation of the configured Ring linking mode and
authorized official simulator/staging evidence. Do not guess inbound credentials
or switch linking methods near submission. No physical pilot approval follows.

## Verified integration contracts for the next agent

The executable reference is `tools/contract_client/client.py`; isolated server and
broker orchestration lives in `backend/scripts/external_contract_drill.py`.
The client uses HTTPS/MQTT only, with no Nodum domain imports or database access.

### HTTPS provisioning and observation

1. GET `/auth/session` to establish the cookie and read `csrf_token`; POST
   `/auth/login` with `username` and `password`. Mutations send the exact `Origin`
   and `X-CSRF-Token`; retain cookies and use the rotated login token.
2. Provision parents first with PUT `/admin/nodes/{id}`. Records contain `id`,
   `name`, `kind`, `organization_id`, `building_id`, `parent_id`, `scope_id`.
   Building belongs to organization; floor to building; location to floor;
   integration to building; device to location. Scope is self for building/floor/
   location and parent for integration/device. Fixture hardware uses `demo: true`,
   `connection_path: "simulation"`; contact device uses `device_type: "sensor"`
   and `integration_id`. Do not invent capabilities or hardware health.
3. POST `/admin/accounts` with `name`, `username`, `password`, `scope_id`; use the
   returned account ID in PUT `/authorization/assignments/{id}` with `id`, `user_id`,
   `role: "manager"`, `scope_id`, `permissions`. Observer grants are `activity.read`,
   `locations.read`, `hardware.read`; a separate collector operator has
   `activity.read`, `hardware.configure`. Root authority is fixture bootstrap only.
4. GET `/manager/activity?scope_id={building}&limit=100`; follow `next_cursor` even
   after an empty page. Response has `schema_version`, `items`, `next_cursor`.
   Contact items expose `id`, `at`, `action` (`sensor.contact.open` or
   `sensor.contact.closed`), `resource_id`, `location_id`, `source`,
   `source_event_id`, `observed_at`, `simulated`. Correlate by source event and
   device, never by guessing the server record ID. Wrong scope is 403,
   unauthenticated access 401 and invalid cursor 422.

### MQTT contact-v1

Use MQTT 3.1.1 over TLS with CA and hostname verification, per-device credentials,
QoS 1 and `retain=false`. Exact topic:
`nodum/v1/contact/{percent-encoded-building-id}/{percent-encoded-device-id}`.
Payload is at most 1,024 bytes, without extra or duplicate keys:

```json
{"event_id":"sample-0001","observed_at":"2026-10-16T12:00:00+00:00","state":"open"}
```

Replace the example timestamp with current UTC time; accepted clock window is
five minutes old to thirty seconds future. State is `open` or `closed`; event ID
is 1–128 ASCII letters/digits/underscore/hyphen. Exact duplicates are idempotent;
changed content under the same identity conflicts. Nodum authority is checked
for every event independently of broker authentication.

The trusted collector runs `backend/scripts/mqtt_collect.py --config <private-json>
--seconds <bounded-duration>` against initialized scoped SQLite. Config supplies
`host`, `port`, `ca_file`, `building_id`, `device_id`, `operator_user_id`,
`max_observations`; credentials use `MQTT_USERNAME` and `MQTT_PASSWORD`. Keep
these private and outside reports. Use the drill as the complete startup reference.

There is **no verified public external actuator command contract**. Internal pure
simulator command tests do not authorize scoped legacy actuator calls or network
actuation. Inventory capabilities do not imply a live controller or physical state.

### Deterministic lab boundary

Future AI may propose declarative scenarios only: validate their schema, supported
capabilities, endpoint allowlist, event/time/resource budgets and cancellation.
Do not execute arbitrary generated code. Expected results must be independently
specified; neither Nodum responses nor AI opinions may define the passing verdict.
Preserve simulation labels and report unsupported cases explicitly.
