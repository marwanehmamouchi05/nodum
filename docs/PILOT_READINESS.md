# Pilot readiness evidence

Checkpoint: 2026-10-15, isolated `codex/pilot-readiness` worktree. The existing
`C:/dev/nodum` environment has not been promoted or modified by development changes.

| Gate | State | Evidence / remaining work |
|---|---|---|
| A — Functional | PARTIAL | Existing Admin/Manager/Resident/Business and signed simulated Ring workflows covered by regression tests. No newly verified package-delivery workflow or outbound notification delivery. Pilot user acceptance still required. |
| B — Security | PARTIAL | 994 backend tests passed in default repository mode, including tenant/resource boundaries and malformed-origin regression tests. No professional security certification, ingress abuse test or penetration test. |
| C — Integrations | BLOCKED FOR PHYSICAL PILOT | Ring/software simulators tested; no real hardware verified. Exact pilot models, account/license access and adapter acceptance required. See HARDWARE_COMPATIBILITY.md. |
| D — Deployment/recovery | PARTIAL, IMPROVED | New backup/verify/restore and preflight CLI tested. Actual disposable restored production-mode backend returned health 200, anonymous Manager 401 and docs 404. Clean-machine dependency install, TLS/proxy/browser configuration, encrypted backup storage, scheduled recovery and update acceptance remain. |
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
- Actual command-line drill: synthetic scoped DB → snapshot → new restore →
  preflight PASS → production-mode localhost startup → health 200 → unauthenticated
  Manager 401 → disabled public docs 404. Restored records present. Server stopped
  and temporary databases removed. No provider or hardware calls.
- Frontend source is unchanged relative to the imported Phase G baseline; no new
  frontend browser/layout approval claimed by this session.

Run the reproducible drill with `python backend/scripts/pilot_drill.py` from the
isolated source root. It clears inherited provider/auth config for its child
processes, creates synthetic identities in temporary storage, chooses a loopback
port and shuts down its own server. Results contain no credentials. The scripts
require the existing installed backend dependencies; no new package was added.

Original-environment promotion, merging and deployment require owner approval.
