# Phase 2 implementation handoff

Read `ARCHITECTURE_OVERVIEW.md`, `DIGITAL_TWIN_INTEGRATION_CONTRACT.md`,
`DIGITAL_TWIN_TESTING_ARCHITECTURE.md`, `SCALABILITY_ASSESSMENT.md` and current
`development-state.json`. This is implementation guidance, not permission for live
hardware or merging the engineering branch. Preserve the c8db547 meeting demo.

Phase 1 is now FOUNDATION COMPLETE WITH EXTERNAL BLOCKERS; PILOT NOT APPROVED.
See PHASE1_FINAL_REPORT.md and ASTRA_FINAL_REVIEW_HANDOFF.md. Independent Astra
acceptance of the supported contact boundary must precede this separate simulator
assignment. This document does not authorize starting it automatically.

## Starting proof and commands

Use the isolated engineering checkout and follow `DEVELOPER_ONBOARDING.md` for a
fresh Python 3.13 environment, optional Paho and separate test-broker environment.

```powershell
backend/.venv/Scripts/python.exe backend/scripts/external_contract_drill.py --broker-python .broker/Scripts/python.exe
backend/.venv/Scripts/python.exe backend/scripts/benchmark_activity.py --output artifacts/activity-benchmark.json
backend/.venv/Scripts/python.exe -m pytest -q
```

The external run uses seed 1729, creates two buildings via HTTPS, authenticates real
scoped sessions, sends MQTT contact samples, checks normalized correlation and
tenant isolation, exercises broker restart and revokes the collector assignment.
Its JSON report must say PASS with three persisted source events; supplemental
server counts are recorded=3, duplicate=1, rejected=2, failed=0. Treat other results
as failure, not as evidence to rewrite expected assertions. Runtime timestamps,
ports, IDs and credentials are fresh; the scenario decisions remain reproducible.
The last recorded [external result](verification/external-contact-20261015.json)
is preserved as redacted JSON. Capture future stdout to a new artifact/report file.

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
