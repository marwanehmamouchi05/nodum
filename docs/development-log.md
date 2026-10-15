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
