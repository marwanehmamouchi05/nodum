\# Nodum Development Log



\## September 28, 2026



\- Created Devpost submission draft.

\- Created public GitHub repository.

\- Configured local Git repository.

\- Created Ring private developer app.

\- Selected Ring scopes for cameras, contact sensors, and flood/freeze sensors.

\- Ring account linking deferred until public HTTPS endpoints are deployed.

\- Created AWS account.

\- Created $20 monthly AWS budget with 50%, 80%, and 100% alerts.

\- Installed AWS CLI.

\- Amazon Bedrock access pending AWS account verification.

\- Created local environment template and ignored local .env secrets.



## 2026-10-15 — PILOT-001 COMPLETED (isolated branch)
Verified baseline backup and source hashes; original workspace preserved. Added explicit-path online SQLite backup, read-only verify and restore-to-new-file CLI. Atomic no-overwrite publication, timeout and schema/integrity checks. Recovery + persistence: 54 passed; initial Windows fsync issue repaired. No live hardware or original database touched. See backup-recovery.md and development-state.json. Next: read-only pilot preflight.


## 2026-10-15 — PILOT-002 COMPLETED
Added read-only pilot preflight, isolated production-mode template and actionable JSON failures. No network, migration, seeding or secret output. Tests cover unsafe modes, cross-origin sessions, bootstrap removal, missing DB, old schema and empty onboarding. 11 targeted tests passed. PASS explicitly covers local prerequisites only. Next: reject malformed authentication origins before session handling.


## 2026-10-15 — PILOT-004 COMPLETED; regression checkpoint
Authentication origin validation now rejects malformed/out-of-range/empty ports, wildcards, ambiguous characters and whitespace. Fixed error messages redact values. 86 auth/origin tests and all 994 default backend tests passed. Reproducible disposable backup/restore/preflight/startup drill passed: health200, Manager401, docs404, restored records present. No broken requirements. Two high hardware/live-linking handoffs documented, not sent. See PILOT_READINESS.md for partial/blocked gates; no pilot-ready claim.


## 2026-10-15 — Recovery hardening COMPLETED
Post-review bounded malformed/huge schema-version input before constructing a version range; snapshot deadline also covers hashing/publication. All 12 maintenance tests passed. Full 994-test run preceded this narrow hardening; no full-suite rerun claimed. Original source/private configuration and Git-state hashes rechecked unchanged.


## 2026-10-15 — Final isolated session checkpoint
SQLite-specific auth, authorization and product-release tests: 162 passed. No active task or failed approach left open. Code checkpoint febe213; machine state tracks completed iterations and independent queue. Working tree clean after documentation commit. Original branch remains product-platform with all prior changes preserved; no promotion, deployment or physical commands.


## 2026-10-15 — PILOT-005 isolated installation/TLS iteration COMPLETED
Resumed verified clean 40b4769. 87 targeted baseline tests and 55 auth/isolation tests passed. Fresh Windows Python 3.13 venv installed backend pins; pip check, recovery/startup drill and real HTTPS session drill passed. Added shared allowlisted drill environment and temporary TLS fixture. Certificate trust/cookie rotation/CSRF/Origin/logout checks use actual HTTPS. No OS trust-store or existing config changes. Proxy/frontend topology remains unverified. Broker dependencies separated after identifying a test-only Click pin conflict.


## 2026-10-15 — PILOT-003 contact MQTT iteration COMPLETED
Added optional read-only Paho subscriber with strict contact payload, exact device/building topics, per-event revocable authorization, durable SQLite activity binding/idempotency, no actuator/publish method. Added bounded private-config collector and actual separate aMQTT wire drill. 16 final SQLite MQTT tests passed, including concurrent dedup, restart and rollback; earlier Manager/MQTT SQLite batch 46 passed. Actual broker restart/resubscription, retained/malformed rejection, grant revocation and Manager simulation labeling passed. Test broker dependency conflict isolated into a separate environment. No real sensors or deployed broker TLS/ACL claims.


## 2026-10-15 — ARCH-002 indexed operation reads COMPLETED
Manager arrival and maintenance mutations now use indexed get_operational_record after authorization instead of loading complete histories. SQLite behavioral regression forbids bulk loads and passed. Existing Manager/MQTT SQLite batch had 48 pass and one test-fixture setup error; fixture import repaired and point-read test passed. Bounded real-broker burst: 250 observations in 3.678 sec, 251 persisted including post-reconnect sample, duplicate/retained/malformed/revoked samples handled. Initial load-drill assertion incorrectly expected all records in the capped UI; corrected to verify full storage separately from 100-item projection. Architecture audit records remaining pagination/retention and durable-delivery gaps.


## 2026-10-15 — Resume-session validation checkpoint
1013 backend tests passed, 1 SQLite-only case skipped (separately passed with 16 SQLite MQTT tests). 32 frontend unit tests passed; app/broker pip checks clean. TLS acceptance repeated with explicit wrong-host certificate rejection; MQTT fixture startup now stops its child if readiness fails, wire drill repeated. Original source/private-config/Git-state hashes verified unchanged. Updated hardware evidence, architecture audit, readiness and exact resume queue. No merge, deploy, real provider/device contact or physical command. Next: broker TLS/ACL fixture or scope-safe activity paging; proxy/browser acceptance still partial.


## 2026-10-15 — Engineering foundation from security checkpoint 6e350af

Created a separate managed worktree/branch, preserving pilot-readiness and frozen
c8db547 demo. Implemented indexed, authorized operational-journal pages (ADR 0001),
source-event correlation and durable non-destructive per-device contact capacity
(ADR 0002). Tested tied timestamps, cursor validation, scope/binding consistency,
revocation, SQLite plans, concurrent reservations and restart. No UI redesign,
physical adapter, dynamic plugin API or destructive migration.

Standalone external participant now creates two buildings/devices/accounts/roles via
HTTPS, sends real MQTT messages and checks durable API observations. Actual broker
restart/reconnect and revocation passed; external deterministic oracle has mutation
and Python optimization regressions. Server fixture only bootstraps trusted recovery
and runs actual resources. No client internal imports/direct DB writes.

Measured activity benchmark at 10,000 rows / 100 scopes: legacy p50 3445.015ms versus
91.131ms indexed page, one authorized scope; not a fleet SLA. Fresh backend install
and pip check, frontend npm ci/32 tests/lint/type-build, Python correctness lint and
scoped formatting passed. Added pinned, read-only CI workflow; hosted execution not
observed. Full final counts and checkpoint IDs follow in resume state.

Documented actual architecture, hardware/protocol evidence, onboarding, external
contract and implementation-ready Phase 2 handoff. Official Ring docs/rules reviewed;
no official playground/account evidence or portal change. Updated Astra handoffs for
linking-mode uncertainty and archive/fleet policy. No merge, deployment or hardware
commands. Phase 2 can start with the supported contact boundary; broad/physical
acceptance is not asserted.


Final engineering verification: **1,059 backend passed / 3 SQLite-only skipped**, **67 SQLite checks passed**, plus populated schema-8 upgrade preservation/index plan. Fresh backend pip check, 32 frontend tests, lint/type-build, external HTTPS/MQTT proof, current broker security and schema-10 recovery passed. Hosted CI/official Ring/physical equipment remain unverified. Protected source/private configuration/Git status and both old checkpoint refs verified unchanged. Exact resume state and Phase 2 handoff are stored in this checkout.

## Phase 1 finalization — 2026-10-16

Source checkpoint 254eee5: real Caddy HTTPS/static frontend/private HTTP API fixture,
actual browser workflow/security checks, refresh restoration fix for multi-role
workspaces and Resident/Manager/Business sections, three-building read/write and
revocation acceptance, full external HTTPS/MQTT environment stop/new-path restore.
Fresh backend pins/pip check and frontend npm ci repeated; real Vite browser login
and custom Ring visitor-arrival yielded three persisted simulated signals.
Final backend 1060 passed/3 SQLite-only skips, targeted SQLite 139 passed, frontend
34 passed with lint/type-build, Python correctness/scoped format passed. MQTT
TLS/auth/ACL/revocation wire proof passed. Hosted CI and official Ring remain
unverified. No architecture/style rewrite, actuator activation or simulator work.
Final report and consolidated Astra handoff close the bounded foundation with
external blockers; pilot not approved. Original hashes/config/status and protected
refs verified unchanged. Final documentation commit contains closure/resume evidence.
