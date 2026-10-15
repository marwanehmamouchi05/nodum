# Security readiness — 2026-10-15

PASS means the stated, bounded property was verified. FAIL means a confirmed issue
remains. BLOCKED requires unavailable external evidence. NOT TESTED means no valid
current evidence. None of these statuses constitutes whole-product certification.

| Requirement | Status | Evidence / limit |
|---|---|---|
| Stable meeting demo preserved | PASS | `codex/meeting-demo-20261020` at `c8db547`; no merge/deploy |
| HTTP body size and receive deadline | PASS | SEC-HTTP-001 fixed; hostile ASGI and actual route tests |
| Auth, CSRF, origins, deployment/privacy regression | PASS | 173 tests including body guard; in-process scope |
| Broker TLS, authentication, per-topic ACLs | NOT TESTED | Pending new local secure wire fixture |
| Cross-building authorization, all roles | NOT TESTED | Existing tests available; current rerun pending |
| Actual deployment proxy and browser | BLOCKED | Selected production deployment unavailable |
| Physical actuator and emergency safety | BLOCKED | No authorized bench or independent actuator review |
| Live Ring contract/account | BLOCKED | No confirmed contract/authorized staging account |
| Full dependency/secret assessment | NOT TESTED | Pending scoped scan; no comprehensive assurance |
| Broad injection/SSRF/XSS/fuzz coverage | NOT TESTED | Must map precise cases; do not infer from suite count |

The application is **not approved for a real building pilot**. See
`SECURITY_AUDIT.md` for reproductions, fixes, residuals and test scope.
