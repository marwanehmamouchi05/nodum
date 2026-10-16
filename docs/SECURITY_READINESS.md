# Security readiness — 2026-10-15

Current closure authority: [PHASE1_FINAL_REPORT.md](PHASE1_FINAL_REPORT.md) (2026-10-16). Earlier results below are historical. Consolidated review: [ASTRA_FINAL_REVIEW_HANDOFF.md](ASTRA_FINAL_REVIEW_HANDOFF.md).

PASS means the stated, bounded property was verified. FAIL means a confirmed issue
remains. BLOCKED requires unavailable external evidence. NOT TESTED means no valid
current evidence. None of these statuses constitutes whole-product certification.

| Requirement | Status | Evidence / limit |
|---|---|---|
| Stable meeting demo preserved | PASS | `codex/meeting-demo-20261020` at `c8db547`; no merge/deploy |
| HTTP body size and receive deadline | PASS | SEC-HTTP-001 fixed; hostile ASGI and actual route tests |
| Auth, CSRF, origins, tenant/deployment/privacy regression | PASS | Engineering backend: 1,059 passed / three SQLite-only skips; 67-case SQLite subset passed |
| Direct HTTPS request and session defenses | PASS | 413 early body rejection, 408 at 10.01s; cookie/rotation/CSRF/logout wire drill |
| Local broker TLS, authentication, per-topic ACLs | PASS | New MQTT-TLS-001 wire drill; deployment broker remains unverified |
| Three-building Manager isolation and configured Resident confinement | PASS | Corrected HTTP matrix + SQLite subset; broader existing role tests in final backend run |
| Actual deployment proxy and browser | BLOCKED | Selected production deployment unavailable |
| Physical actuator and emergency safety | BLOCKED | No authorized bench or independent actuator review |
| Live Ring contract/account | BLOCKED | No confirmed contract/authorized staging account |
| Anonymous session write budget | PASS | 30/IP/15 min + 1,000 global live-row ceiling; concurrency and rotation tests |
| Scoped dependency/secret queries | PASS | 32 public pinned package versions, no OSV advisories; changed-file pattern scan only |
| Comprehensive dependencies/secrets assessment | NOT TESTED | Transitive/frontend inventory and full history scan remain |
| Contact storage budget and operational activity paging | PASS | Durable per-device quota, indexed keyset pages; concurrency/restart/isolation tested |
| Fleet/global storage, other histories and archive retention | FAIL | Still open; ASTRA-STORAGE-003; no destructive cleanup or disk-exhaustion experiment |
| Broad injection/SSRF/XSS/fuzz coverage | NOT TESTED | Must map precise cases; do not infer from suite count |

The application is **not approved for a real building pilot**. See
`SECURITY_AUDIT.md` for reproductions, fixes, residuals and test scope.


Engineering branch supplements the security baseline with independent external
HTTPS/MQTT verification, fresh app installation, schema-10 recovery and Python/
frontend quality checks. Hosted CI and official Ring/device evidence remain
unverified. Final current counts are recorded in development-state.json; earlier
rows describe their original scoped runs. No real-building pilot approval.
