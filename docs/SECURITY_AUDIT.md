# Security audit — isolated development, 2026-10-15

Scope: `codex/pilot-readiness`, baseline `c8db547`. Meeting demonstration is frozen at
`codex/meeting-demo-20261020` (`c8db547`); changes here are not merged or deployed.
All hostile inputs use disposable local fixtures. No physical commands or external
provider accounts are authorized. Tests establish specific properties, not security certification.

## Threat model and surfaces

Adversaries: unauthenticated HTTP callers; authenticated residents/business users
guessing foreign identifiers; revoked operators; MQTT publishers with stolen or
wrongly scoped credentials; malformed/replayed provider input. Assets: tenant
records, session credentials, persistent audit integrity, availability, physical
access boundaries. Surfaces: browser/session routes, scoped operational/configuration
APIs, signed Ring input, optional MQTT collector and broker, SQLite storage,
installation/backup scripts and deployed proxy. Hardware and live Ring are unverified.

## SEC-HTTP-001 — unbounded request bodies (fixed)

Risk: unauthenticated availability degradation; severity HIGH for a directly exposed
API without an upstream cap. Root cause: no global body budget before framework
JSON parsing. Bounded reproduction: send 1 MiB whitespace plus `{}` to
`POST /auth/login`; baseline processed input and returned 403 rather than rejecting
the body. `test_oversized_json_is_rejected_before_authentication` failed before the fix.
No exhaustion or flood was attempted.

Defense: global ASGI guard caps every HTTP body at 1,048,576 bytes and complete
body receipt at 10 seconds, before dependencies or mutations. Counts actual chunks
even without Content-Length, rejects ambiguous/mismatched lengths, stops reading at
overflow, returns 413/408/400 with no-store and connection close. Raw payload bytes
are preserved for signature verification. This does not validate proxy HTTP framing
or bound total concurrent connections; production proxy limits remain required.

Verification: `tests/test_request_limits.py` plus authentication, origins, deployment
and privacy suites: **173 passed**. Variations include lying length, chunked/no-length,
multiple lengths, extreme numeric headers, exact boundary, stall and disconnect.
No new dependency or schema change. Existing signed-provider regressions will also
run in the final backend suite.

## Traceability and coverage

- OWASP API4 resource consumption: SEC-HTTP-001, `test_request_limits.py`; other
  rate/storage/concurrency limits remain under investigation.
- OWASP API1/API5 tenant and function authorization: existing `test_authorization.py`,
  `test_structure.py`, Manager/Resident/Business suites; rerun evidence recorded below.
- OWASP API2 session/authentication: `test_auth.py`, `test_auth_origins.py`; included
  in the 173-pass run. Existing wire HTTPS acceptance is historical evidence only.
- OWASP ASVS: verification categories authentication, session management, authorization,
  validation and configuration; this is a scoped matrix, not full ASVS conformance.

References: [API4](https://api-security.owasp.org/editions/2023/en/0xa4-unrestricted-resource-consumption/),
[API1](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/),
[ASVS](https://owasp.org/projects/asvs).

## Residual and untested areas

MQTT TLS/authentication/ACL wire acceptance is next. Actual deployed proxy/browser,
host process/filesystem isolation, sustained storage pressure, broad fuzzing, and
independent human assessment are not verified in this session. Live actuator safety,
emergency egress and physical acknowledgments require hardware-specific review;
see `ASTRA_HANDOFF.md`. No physical pilot approval follows from software tests.
