# Independent engineering review — 2026-10-16

Verified review base: `af7a3e1d75d526d754c016f8bc12f77f5c2327ee`.
Branch: `codex/astra-final-review`, isolated worktree
`C:/Users/marwa/.codex/worktrees/astra-final-review/nodum`.

The requested ASTRA filenames identify this review mission. Evidence was gathered
in this Codex session by inspecting source, reproducing new failures and running
tests independently of the earlier report. No separate model invocation, external
security certification or human review is claimed.

## Executive assessment

The modular monolith is a reasonable foundation for professional engineers to
inherit. Supported product workflows, scoped sessions, contact-v1 ingestion,
external observation and recovery are executable. A rewrite is not justified.
The foundation report was substantially reproducible, but missed a current Ring
classification contract and accepted insufficiently constrained simulator output.
These are fixed, with regression tests. Retention planning now has an authorized,
bounded non-destructive service; archive/deletion remains unimplemented and disabled.

**SIMULATOR BACKEND READY WITH LIMITATIONS** for authenticated HTTPS provisioning,
MQTT contact-v1 and scoped observation. **HACKATHON RING READY: BLOCKED. PHYSICAL
PILOT READY: BLOCKED.** These decisions are independent. No simulator was built.

## Actual verification, not inherited counts

| Check executed in this review | Result |
|---|---|
| Foundation baseline: Ring, building integration, recovery | 190 passed |
| New defect reproductions before correction | 7 failed as expected, 3 passed; two classification cases, replay conflict, four adapter-output cases |
| Full backend after corrections | 1,085 passed, 4 skipped, 144.48 seconds |
| SQLite targeted acceptance | 272 passed, 52.84 seconds; all four SQLite-only skipped cases exercised |
| New review tests | 18 command/Ring/security/extension cases plus 8 retention cases; included above, not extra unique totals |
| Fresh backend install | Core + optional MQTT + development pins installed into new venv; pip check passed |
| Fresh frontend install | npm ci installed 160 packages; 34 tests, ESLint and TypeScript/Vite build passed |
| Caddy/browser | Actual HTTPS proxy + built frontend + private API: login, visitor/pass, role/page refresh, deep path, cookies, CSRF/Origin, error codes, logout and forged Admin hash passed; zero page errors |
| Independent HTTPS/MQTT client | PASS, 20.97 seconds; two buildings, three persisted source events, duplicate/conflict boundaries, broker restart, revocation and complete stop/restore |
| Broker wire security | Wrong CA/hostname/credentials, four foreign/wildcard subscriptions and three forbidden publications rejected; positive controls and Nodum revocation passed |
| Recovery/startup | Fresh schema-10 snapshot/new-path restore, integrity/FKs, preflight, health 200, anonymous Manager 401 and docs 404 passed |
| Correctness lint / whitespace | Ruff E9/F63/F7/F82 and git diff --check passed |
| Hosted CI | NOT RUN; workflow now includes new SQLite cases, local equivalents passed |

See [evidence](verification/review-20261016.json),
[resolution log](ASTRA_RESOLUTION_LOG.md),
[gate decision](PHASE2_READINESS_DECISION.md). An initial browser-tool wrapper used
an unsupported dynamic import; loading the same committed callback through the
tool corrected the harness. It was not an application failure. Temporary services
were stopped and no OS certificate trust was changed. Browser certificate bypass
was limited to its disposable self-signed fixture context.

## Architecture and professional maintainability

Strengths: explicit domain models, thin HTTP boundaries, parameterized repository
operations, additive migrations, scoped resource bindings, server-owned adapters,
separate optional MQTT dependency, and a genuinely separate-process external client.
`tools/contract_client/client.py` has its own expected outcomes and consumes HTTPS/
MQTT, not application policy or database records. Its mutation/independence tests
remain in the full regression. React/TypeScript/API separation is intact.

| Area / files | Finding and engineering consequence |
|---|---|
| services/authorization.py, authorization_operations.py, api/authorization.py | Fresh user/grant/role-ceiling/typed ancestry and object ownership checks; explicit mutation allowlist. Keep these reviews centralized. A URL/hash never grants authority. |
| services/building.py, integrations/building.py | Simulator adapter output was trusted after only schema/device-ID validation. Fixed by services/simulated_commands.py. Pure simulators remain intentionally distinct from physical I/O. |
| services/ring.py | Current documented motion subtype was ignored; same-ID changed event data could be treated as duplicate. Fixed. Token refresh still performs bounded HTTP while holding a SQLite write transaction; this is live-Ring contention debt, not solved by the command validator. |
| database.py | BEGIN IMMEDIATE for reads and writes gives consistent authority but serializes contenders. Do not claim fleet throughput from component tests. |
| manager_repository.py, services/activity.py | Authorized scopes constrain indexed candidates before LIMIT; current object authority filters output. Sparse pages retain continuation. Typed cursors are navigation, not credentials. |
| services/manager.py, services/ring.py, repository.py | Non-journal snapshots and several legacy histories still scan collections. Prioritize measured hot paths and indexed reads as deployment grows. |
| repository.py / sqlite_repository.py | Memory is a test double with locking, not rollback. SQLite atomic failure tests are required. Large aggregate protocol/modules are coupling hotspots but do not demand a rewrite. |
| models/structure.py versus models/integrations.py | Configured product inventory and historical simulator inventory are separate. Automatic bridging would be unsafe; document this onboarding trap. |
| integrations/building.py fixed commands/types | Extensible within defined categories; not universal hardware compatibility. Arbitrary HVAC points/media streams do not fit the lock-state model. Add reviewed category contracts at the adapter boundary. |

Teams can split frontend, building workflows, auth/security, adapters and persistence
work using the documented ownership map and PR checklist. Shared contracts, migration
ordering and authorization deserve named maintainers and joint review. Dynamic
repository mixins, some untyped service methods, large role projections and incomplete
transitive broker locking are real debt. Broad static typing, full-history secret
scanning and a clean-OS/hosted run are not certified by this review.

## Ring evidence and deadline risk

Nodum uses a standard-library server-side REST client, encrypted tokens and signed
webhooks. It does not use an official SDK or demonstrated official Playground run.
The API guide supports the outgoing token/profile/link/discovery paths and webhook
signature shape; this review corrects human/package motion classification. Unknown
classifications remain motion and raw evidence is retained. Custom legacy event
kinds still work; none proves visitor identity or physical access.

Live inbound token delivery still returns 503. Authorized portal configuration,
approved scopes, exact authenticated code-delivery format and official tool/account
evidence are missing. No speculative decoder or PKCE migration was enabled.
[Official Ring API](https://developer.amazon.com/docs/ring/api-documentation.html),
[configuration](https://developer.amazon.com/docs/ring/configure.html).

The [hackathon rules](https://amazonappdev2026.devpost.com/rules) permit documented
Ring simulators; physical hardware is not mandatory. They require demonstrated
runtime use. A working Nodum custom scenario is insufficient evidence. Follow
[RING_DEMO_PROCEDURE.md](RING_DEMO_PROCEDURE.md) for exact owner setup and demo steps.
The October 23 target remains at risk until that evidence exists; no eligibility
or submission approval is claimed. Context7 returned unrelated Ring libraries,
so official Ring documentation was used directly.

## Command and hardware findings

Read-only contact telemetry has actual local MQTT wire evidence. Access, credentials,
elevator requests and display/wayfinding have component simulation evidence. The
new alternate display adapter exercise requires only registry wiring and its port,
not unrelated frontend/domain changes. It proves that defined extension point,
not a new physical protocol.

Adapter return validation now prevents unrelated-field changes, wrong correlation,
extended leases and altered authority. Failure never creates a successful simulated
receipt; exact failed replays do not retry. SQLite rolls back state if receipt
persistence fails. Concurrent delayed simulator and lock operations serialize.
Fresh unauthorized/expired/revoked requests and scoped cross-building mutations
remain denied. Historical receipt retrieval is not reauthorization or redelivery.

Requested, queued, acknowledged, provider-reported executed and independently
observed state remain different evidence. No durable network delivery subsystem is
installed. [ADR 0002](decisions/0002-simulator-command-boundary.md) defines the future
outbox/reconciliation contract and crash acceptance. Do not put live I/O inside
BuildingService.action. Unknown delivery must not be blindly retried.

MQTT, HTTP/webhooks, streams and configuration writes require distinct semantics.
ONVIF/RTSP, BACnet, Modbus, KNX, DALI, Matter, Zigbee, Z-Wave, OSDP and vendor SDKs
remain researched extension paths, not installed compatibility. Read-only certified
life-safety monitoring and approved elevator interfaces require their own acceptance.
No physical controller, egress or safety system was touched.

## Security assessment

Source inspection and tests support session hashing/rotation, exact Origin/CSRF,
live role ceilings and resource ownership, request bounds, parameterized storage,
verified MQTT TLS/topic ACLs, signed Ring input and revocation after recovery.
New tests attack changed signed event content, out-of-policy adapter results and
legacy command paths from three populated tenant contexts. Findings are bounded
contract/integrity defects, not a demonstrated remote physical takeover.

No newly confirmed unresolved critical exploit was accepted into the supported
contact lab. This is not proof against every attack. Residual risks: total storage
growth, serial database locks, live-provider refresh uncertainty, operational secret/
backup protection, and restoration of older authority. Restore proof used a snapshot
already containing revocation; it does not reconcile later revocations automatically.

## Scalability and lifecycle

The existing benchmark source was inspected and rerun unchanged: 10,000 synthetic
events across 100 scope partitions, one authorized scope, three samples. Legacy p50
3,662.044 ms; indexed p50 86.947 ms, sample p95 104.356 ms. This reproduces the earlier
direction of improvement. Three samples cannot estimate a production p95; traced
Python allocations are not process RSS. Seeding speed is not ingest throughput.
[Measured artifact](benchmarks/review-activity-20261016.json).

Per-device capacity and paged observations support a bounded lab. Total disk,
unbounded other histories, broad-scope enumeration, SQLite locks and clean-session
MQTT message loss remain real limits. No microservices or queues were justified.

The new retention preview counts only authorized scanned contact records and
protects other journal classes. It neither archives nor erases data. Owner must
approve class-specific purpose/horizons, holds, replay retention, fleet ceiling,
archive protection and backup/recovery ownership. See [lifecycle decisions](DATA_LIFECYCLE.md).

## Preservation and next stage

Original source hashes (411), three private config copies, original Git-status
bytes, backup integrity and foundation/security/demo refs verified unchanged.
No merge, push, deployment, real hardware action or simulator implementation.

Next agent must read [DIGITAL_TWIN_PHASE2_HANDOFF.md](DIGITAL_TWIN_PHASE2_HANDOFF.md)
and stay inside contact-v1/HTTPS. Official Ring, physical delivery and destructive
retention remain separately gated. Final local commit and clean-state evidence are
reported at delivery; the foundation branch remains at af7a3e1.
