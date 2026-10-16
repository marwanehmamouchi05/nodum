# Pilot readiness evidence

Current closure authority: [PHASE1_FINAL_REPORT.md](PHASE1_FINAL_REPORT.md) (2026-10-16). Earlier results below are historical. Consolidated review: [ASTRA_FINAL_REVIEW_HANDOFF.md](ASTRA_FINAL_REVIEW_HANDOFF.md).

Checkpoint: 2026-10-15, isolated `codex/pilot-readiness` worktree. The existing
`C:/dev/nodum` environment has not been promoted or modified by development changes.

| Gate | State | Evidence / remaining work |
|---|---|---|
| A — Functional | PARTIAL | Existing Admin/Manager/Resident/Business and signed simulated Ring workflows covered by regression tests. No newly verified package-delivery workflow or outbound notification delivery. Pilot user acceptance still required. |
| B — Security | PARTIAL | 1,038 backend tests passed (one SQLite-only case separately verified in final 41-test SQLite subset). Bounded hostile HTTP, anonymous session growth, three-building isolation and local MQTT TLS/auth/ACL checks passed. Activity retention and selected deployment testing remain open. No professional security certification. |
| C — Integrations | BLOCKED FOR PHYSICAL PILOT | Ring/software simulators and explicit MQTT contact wire fixture tested; no real hardware verified. Exact pilot models, account/license access and adapter acceptance required. See HARDWARE_COMPATIBILITY.md. |
| D — Deployment/recovery | PARTIAL, IMPROVED | New backup/verify/restore and preflight CLI tested. Actual disposable restored production-mode backend returned health 200, anonymous Manager 401 and docs 404. Fresh-venv install and direct HTTPS session checks now passed (see update below). Clean target OS, deployed TLS/proxy/browser configuration, encrypted backup storage, scheduled recovery and update acceptance remain. |
| E — Operations | PARTIAL | Existing provider/network failure tests; bounded recovery tooling and actionable prerequisite report. Operator ownership, monitoring/alerting, retention and operational runbooks still needed for selected building. |
| F — Physical validation | BLOCKED | No pilot building, physical devices, safety/egress acceptance or owner-approved bench available to this run. |

Verdict: software recovery and configuration readiness improved. **Not declared
software-pilot ready or physical-pilot ready.** A preflight PASS checks local
prerequisites only and cannot satisfy all gates.

## Verification in this session

- Protected baseline: hashes verified for 411 source files; three private configs
  backed up separately with restricted directory access; one SQLite database
  backed up through SQLite backup API and checked for integrity/FK violations.
- Baseline tests: 222 targeted backend and 32 frontend unit tests passed.
- Iteration 1: 54 recovery/persistence tests passed; two initial Windows fsync
  failures fixed. Existing files, corrupt snapshots, future/gapped schema,
  FK violations, missing source, destination race and timeout covered.
- Iteration 2: 11 read-only preflight tests passed; no migration/seed side effects.
- Iteration 3: 86 auth/origin tests passed; full default backend regression **994 passed**.
- SQLite-specific authentication, authorization and product-release regression: **162 passed**.
- Actual command-line drill: synthetic scoped DB → snapshot → new restore →
  preflight PASS → production-mode localhost startup → health 200 → unauthenticated
  Manager 401 → disabled public docs 404. Restored records present. Server stopped
  and temporary databases removed. No provider or hardware calls.
- Final recovery hardening: 12 maintenance tests passed after the full regression run; untrusted schema-version bounds and digest deadline covered.
- Frontend source is unchanged relative to the imported Phase G baseline; no new
  frontend browser/layout approval claimed by this session.

Run the reproducible drill with `python backend/scripts/pilot_drill.py` from the
isolated source root. It clears inherited provider/auth config for its child
processes, creates synthetic identities in temporary storage, chooses a loopback
port and shuts down its own server. Results contain no credentials. The scripts
require the existing installed backend dependencies; no new package was added.

Original-environment promotion, merging and deployment require owner approval.


## Resume session evidence — 2026-10-15
- Exact clean checkpoint 40b4769 verified; 87 fresh targeted baseline tests passed.
- Fresh Python 3.13 backend venv installed existing pins; dependency check, recovery/startup and actual HTTPS session drills passed. TLS proof covers temporary trusted loopback certificate, secure cookie/rotation, authenticated Manager reads, Origin/CSRF rejection, logout and untrusted-certificate failure. It does not verify a deployed reverse proxy, frontend browser topology or clean operating system.
- Optional MQTT contact adapter is PROTOCOL TESTED against actual aMQTT 0.11.3 over loopback MQTT 3.1.1. Final SQLite MQTT tests: 16 passed. No physical sensors or deployed broker TLS/ACL verified. Runtime collector requires verified TLS/credentials, scoped operator grants and existing SQLite; no commands or discovery.
- 250-event wire burst: 3.678 seconds, 251 persisted with reconnect event; Manager intentionally returns latest 100. No retention/capacity claim.
- Single-record Manager mutations now use indexed lookups, preserving authorization. Behavioral SQLite test passed; architecture findings and remaining history/retention issues tracked in ARCHITECTURE_AUDIT.md.
- Current frontend unit tests: 32 passed. Frontend source/layout unchanged.
- Original-environment promotion remains prohibited without owner approval. Gates A/B/D/E remain partial, C/F remain blocked for physical pilot.


Final resume-session regression: **1013 backend tests passed, 1 skipped** (SQLite-only rollback/restart; separately passed in the 16-case SQLite MQTT run). Current frontend unit tests: 32 passed. Application and separate broker pip checks passed. Final TLS drill additionally rejected a trusted certificate with the wrong hostname. Small MQTT wire drill repeated after fixture cleanup hardening. Source, Git-state and private configuration hashes for the original workspace remained unchanged. These results supersede historical session counts for the tested code; no release-candidate or physical pilot declaration.


## Security hardening checkpoint — 2026-10-15

Meeting demo frozen at `codex/meeting-demo-20261020` (`c8db547`). Experimental
branch adds global 1 MiB / 10-second HTTP body guard and persisted anonymous
session issuance budgets. Final backend: 1,038 passed / one skipped; final SQLite
subset: 41 passed. Actual loopback MQTT TLS/auth/topic ACLs and independent Nodum
revocation passed. Direct HTTPS abuse and session checks passed. See
`SECURITY_AUDIT.md` and `SECURITY_READINESS.md` for exact scope and remaining gaps.
These results supersede the older backend counts above. Original project untouched;
no merge, deployment or real pilot approval. Frontend test evidence remains historical.


## Engineering branch gate update — 2026-10-15

New isolated engineering branch provides external simulator connection readiness
for the explicit read-only contact contract, bounded operational activity reads,
persistent contact capacity, fresh onboarding/quality verification and Phase 2
handoff. Schema 9/10 are additive indexes; actual recovery/startup passed at schema 10.
Measured scope-query benchmark and all evidence limitations are documented separately.
Universal hardware support, official Ring runtime demonstration, hosted CI, selected
proxy/browser commissioning, global retention and physical safety gates are not
established. Do not promote the branch or approve a pilot from this software checkpoint.


Final engineering verification: **1,059 backend passed / 3 SQLite-only skipped**, **67 SQLite checks passed**, plus populated schema-8 upgrade preservation/index plan. Fresh backend pip check, 32 frontend tests, lint/type-build, external HTTPS/MQTT proof, current broker security and schema-10 recovery passed. Hosted CI/official Ring/physical equipment remain unverified. Protected source/private configuration/Git status and both old checkpoint refs verified unchanged. Exact resume state and Phase 2 handoff are stored in this checkout.
