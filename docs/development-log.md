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
