# Security readiness — 2026-10-15

PASS means the stated, bounded property was verified. FAIL means a confirmed issue
remains. BLOCKED requires unavailable external evidence. NOT TESTED means no valid
current evidence. None of these statuses constitutes whole-product certification.

| Requirement | Status | Evidence / limit |
|---|---|---|
| Stable meeting demo preserved | PASS | `codex/meeting-demo-20261020` at `c8db547`; no merge/deploy |
| HTTP body size and receive deadline | PASS | SEC-HTTP-001 fixed; hostile ASGI and actual route tests |
| Auth, CSRF, origins, tenant/deployment/privacy regression | PASS | Final backend: 1,038 passed / one SQLite-only skip; final SQLite subset: 41 passed |
| Direct HTTPS request and session defenses | PASS | 413 early body rejection, 408 at 10.01s; cookie/rotation/CSRF/logout wire drill |
| Local broker TLS, authentication, per-topic ACLs | PASS | New MQTT-TLS-001 wire drill; deployment broker remains unverified |
| Three-building Manager isolation and configured Resident confinement | PASS | Corrected HTTP matrix + SQLite subset; broader existing role tests in final backend run |
| Actual deployment proxy and browser | BLOCKED | Selected production deployment unavailable |
| Physical actuator and emergency safety | BLOCKED | No authorized bench or independent actuator review |
| Live Ring contract/account | BLOCKED | No confirmed contract/authorized staging account |
| Anonymous session write budget | PASS | 30/IP/15 min + 1,000 global live-row ceiling; concurrency and rotation tests |
| Scoped dependency/secret queries | PASS | 32 public pinned package versions, no OSV advisories; changed-file pattern scan only |
| Comprehensive dependencies/secrets assessment | NOT TESTED | Transitive/frontend inventory and full history scan remain |
| Persistent activity quotas / retention | FAIL | Known unbounded history; ARCH-005 remains open, no disk-exhaustion experiment |
| Broad injection/SSRF/XSS/fuzz coverage | NOT TESTED | Must map precise cases; do not infer from suite count |

The application is **not approved for a real building pilot**. See
`SECURITY_AUDIT.md` for reproductions, fixes, residuals and test scope.
