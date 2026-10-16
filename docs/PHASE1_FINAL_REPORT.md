# Nodum Phase 1 final report

Historical checkpoint report. Current authority: [NODUM_RELEASE_BASELINE.md](NODUM_RELEASE_BASELINE.md).

Finalized 2026-10-16; engineering evidence collected during the Oct 15–16 closure.
Validated source checkpoint: **254eee5**, branch `codex/engineering-foundation`,
isolated `C:/Users/marwa/.codex/worktrees/engineering-foundation/nodum`. The later
finalization commit contains reports/resume state only; use branch HEAD for the
complete milestone. No merge, push, public deployment or real actuator operation.

**FOUNDATION COMPLETE WITH EXTERNAL BLOCKERS. PILOT NOT APPROVED.** This closes the
bounded software engineering deliverable, not official Ring acceptance, production
commissioning, physical safety or an independent security certification. The next
step is the scoped Astra review, not simulator development.

## Demonstrated functionality and completed closure work

Existing Admin/Manager/Resident/Business configuration, visitor, maintenance and
scoped workflows remain covered by regression. Browser testing now demonstrates
actual login/redirect, Resident invitation/pass, persistence after refresh, Manager
and Business section restoration and restricted-role denial through a real reverse
proxy. The discovered refresh defect was corrected without a visual redesign or
changing backend grants. URLs select known screens only, never authority.

The independent HTTPS/MQTT client provisions two buildings, users and devices
through authorized APIs, generates contact observations and checks normalized
source IDs, timestamps, state, simulation labels and tenant isolation. Duplicate,
malformed, broker reconnect and application revocation paths pass. Closure extends
this proof to a complete API/broker/collector stop, SQLite snapshot/new-path restore,
restart and external API re-observation. Revoked ingestion remains rejected after
recovery. The client receives no DB path, Nodum import or repository object.

Contact capacity is durable and configurable per device; activity uses authorized
indexed keyset pages. Existing recovery tooling refuses overwrite, verifies schema,
integrity and foreign keys and publishes snapshots atomically. No history was
deleted and no unapproved retention period was invented. The classified
[closure backlog](PHASE1_CLOSURE_BACKLOG.md) has no intentionally open FIXABLE NOW
item; external, owner and later-phase work remain explicit.

## Actual final verification

| Check executed | Result and scope |
|---|---|
| Full backend regression | **1,060 passed, 3 skipped**, 75.92 s. Skips are SQLite activity query plan, capacity persistence/plan and MQTT rollback/restart; exercised in the SQLite batch. |
| SQLite targeted regression | **139 passed**, 30.97 s: activity, contact/session capacity, tenant matrix, MQTT, HTTP guard, recovery, new concurrency and building integration simulations. |
| New SQLite concurrency + independent oracle subset | **10 passed**, 1.54 s; overlaps final suites, not added to unique totals. |
| Fresh frontend installation and checks | npm ci installed 160 packages; **34 tests passed**, ESLint and TypeScript/build passed. |
| Fresh Python installation | New ignored artifacts/phase1-onboarding venv installed core + optional MQTT + dev pins; pip check passed. This environment successfully ran the final proxy and independent recovery proof. |
| Production-config local Caddy/browser | PASS; Caddy 2.11.7, temporary HTTPS, built frontend, private HTTP API; real UI workflow, refresh/deep URL, secure cookie, CSRF/Origin, validation, 401/403/404 and logout. Wildcard proxy trust rejected before startup. |
| Fresh development onboarding workflow | PASS; new temporary DB, backend and Vite dev server, browser sign-in, Manager custom visitor-arrival scenario; three durable simulated motion/doorbell/person signals read back over API. |
| Independent external final drill | PASS, **14.69 s**, three durable events; before restore recorded=3/duplicate=1/rejected=2/failed=0; restored collector rejected the revoked event, recorded=0/failed=0. Schema 10 integrity/FKs OK. |
| MQTT security wire drill | PASS: wrong CA/hostname/credentials, foreign/wildcard subscriptions and cross-building/read-only publications rejected; positive controls delivered, live Nodum revocation enforced. |
| Python correctness lint / scoped formatting | PASS; E9/F63/F7/F82 and nine selected integration/acceptance files. Not broad Python typing/style certification. |
| CI | Commit-pinned read-only workflow and local commands verified; new concurrency case added to SQLite CI batch. Hosted runner execution NOT TESTED. |

Evidence: [external recovery](verification/external-contact-final-20261015.json),
[proxy/browser](verification/proxy-browser-20261015.json),
[development onboarding](verification/onboarding-20261015.json). Earlier counts in
logs describe their checkpoints and are superseded for this milestone. Initial
test-fixture mistakes (temporary-directory permissions, SQLite byte-hash assumption,
and incorrect browser selectors) were corrected; final runs above have no failures.
Pytest on this host needs a fresh --basetemp because its shared default temp root
was inaccessible. Never reuse a potentially valuable path as pytest basetemp.

## Architecture, hardware and security

The React/TypeScript frontend and FastAPI/Pydantic/SQLite backend remain a modular
monolith. Thin routes, explicit domain services/repository methods, persisted
scope/resource authority and additive schema-9/10 indexes are preserved. Memory
transactions provide locking, not rollback; production acceptance uses SQLite.

Two distinct hardware categories are evidenced: contact monitoring over actual
MQTT TLS connections, and wayfinding/display behavior through clearly labeled
pure simulators. Access/reader and elevator-request simulators are also tested.
There is no physical compatibility claim, universal discovery or verified command
runner. Configured device inventory and historical simulator inventory remain
separate. Broker connection is not device health or physical acknowledgment.

Security evidence covers authenticated sessions, secure-cookie rotation, exact
Origin/CSRF, role/object/tenant denial, request size/deadline, anonymous session
budgets, event identity/replay, broker TLS/auth/ACL, live grant revocation and safe
recovery. No unresolved confirmed critical/high defect was accepted into this
bounded usable scope. Physical delivery remains disabled pending review. Full
history secret scanning, broad fuzzing, clean target-OS commissioning and a complete
transitive dependency/security assessment are not claimed.

Ring remains **official runtime BLOCKED**. Existing REST/linking/webhook code has
mock/signed-custom-simulation evidence. The live inbound code adapter remains 503
pending exact authenticated contract and portal-mode confirmation. Current official
documentation distinguishes Ring-driven and invitation-only PKCE linking; the app's
actual method/entitlement and approved scope configuration need owner-authorized
portal access. See [Ring procedure](RING_DEMO_PROCEDURE.md) and its primary-source
links. No eligibility guarantee or official simulator demonstration is implied.

## Scalability, deployment and maintainability

Retained 10,000-event synthetic query baseline: old p50 **3,445 ms**, indexed p50
**91 ms** (p95 102 ms); one authorized scope, three samples, traced Python memory,
developer host. It was not repeated without a source/performance change. New
bounded concurrency uses three buildings/users/devices and six threads: 24 ingestions,
36 page reads, no foreign contact observations, then revocation denial. It is not
a sustained HTTP/fleet throughput, process-RSS or full-snapshot capacity result.
SQLite serialization, other whole-history projections, total disk growth and lossy
clean-session MQTT downtime remain documented limits.

[Deployment verification](DEPLOYMENT_VERIFICATION.md) provides the reproducible real
Caddy topology and browser callback. Fresh setup now reaches an actual workflow,
not merely a build. [Onboarding](DEVELOPER_ONBOARDING.md), architecture map, adapter
extension guide, pinned dependency files, root pytest and CI make the checkpoint
usable without previous conversations. Broker transitive versions are not fully
locked; hosted cross-OS execution remains unobserved. All disposable services were
stopped; no server is being delivered as an installed operating service.

The [data lifecycle boundary](DATA_LIFECYCLE.md) separates contact observations,
other histories, security/audit, identity and backups. Retention/archive/pruning is
not implemented because its policy is unapproved. Per-device reject-at-capacity and
safe recovery are verified; fleet quotas, encrypted archive and operational
monitoring must be selected before sustained deployment. Restoring an older backup
can restore old authority: the synthetic final drill preserves a revocation already
in its snapshot, not an automatic solution to all recovery reconciliation.

## Closure gates

| Gate | Result | Consequence |
|---|---|---|
| A Functional foundation | PASS, bounded software | Regression and real browser workflows pass; not final user/visual approval. |
| B External integration | PASS contact contract; BLOCKED official Ring | Independent HTTPS/MQTT/recovery usable; vendor runtime remains unapproved. |
| C Hardware extensibility | PASS documented/tested interfaces | Contact + distinct simulator categories; physical delivery separately blocked. |
| D Security | PASS tested usable scope | No known unresolved critical accepted; no whole-product certification. |
| E Reliability | PASS bounded local evidence | Fresh install, DB recovery, restart, concurrent operations; no fleet SLA. |
| F Developer readiness | PASS local; hosted CI unverified | Reproducible source/setup/workflow/quality; run authorized hosted pipeline later. |
| G Operational configuration | PASS local staging/guardrails; BLOCKED operational policy/target | No production or sustained physical pilot approval until commissioning and lifecycle decisions. |
| H Astra handoff | PASS | Three precise issues plus independent checklist and dependency ownership. |
| I State protection | PASS | 411 original source hashes, three private configs and original Git-status bytes match protected baseline; backup integrity/FKs OK; security/demo refs unchanged. |
| J Clean milestone | PASS at final documentation commit | Validated source 254eee5 plus accurate committed reports/state, clean isolated worktree; original intentionally retains its pre-existing changes. |

## Remaining actions and next stage

Owner supplies authorized Ring portal/test access and registered configuration,
chooses the lifecycle/backup policy and deployment operator/target, and selects
equipment/bench only when physical validation is scheduled. No immediate hardware
purchase is justified solely by this foundation report. Authorized repository
publication/CI execution and production commissioning are separate actions.

[ASTRA_FINAL_REVIEW_HANDOFF.md](ASTRA_FINAL_REVIEW_HANDOFF.md) consolidates Ring's
confirmed contract, durable physical command delivery and policy-dependent storage
work, each with files/functions, evidence, alternatives, exact task and acceptance
tests. Astra must first accept the supported software/contact boundary and repair
any concrete findings. A later independent simulator can then build against that
contract, while official Ring, offline durability and actuation stay separately
gated. **Astra has not been invoked; the simulator has not been started.**
