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

## MQTT-TLS-001 — local secure broker acceptance (PASS)

`backend/scripts/mqtt_security_drill.py` runs a separate aMQTT 0.11.3 process,
loopback only, at most eight connections, disposable certificate and random runtime
passwords, isolated SQLite and no real devices. This is not a production broker.
No anonymous plugin is loaded; both subscription and nonempty publication ACLs
are explicit. Installed broker source was checked because its legacy configuration
has dangerous defaults: `allow_anonymous=False` still accepts arbitrary usernames,
and absent/empty publish ACLs allow publication. The secure fixture avoids both.

Wire results: untrusted certificate and wrong hostname rejected; anonymous, wrong
password and unknown username rejected; four foreign/wildcard subscriptions denied;
three cross-building/read-only publications not delivered. Both own-topic positive
controls delivered. Nodum recorded one synthetic observation, deduplicated its replay,
then rejected a new event after application grant revocation despite valid broker
credentials. Zero actuator events. Negative publication assertions observe receivers,
not PUBACK alone; observation window is bounded at 0.5 seconds after positive controls.

Reproduce from worktree root with the existing app environment:
`artifacts/install-smoke/Scripts/python.exe backend/scripts/mqtt_security_drill.py --broker-python artifacts/mqtt-broker/Scripts/python.exe`.
The broker test environment is separate; no dependencies were added to the app.
Foreign topic B is a broker namespace fixture; full tenant record isolation is tested
separately. Physical identity, mutual TLS, broker credential revocation/restart,
packet-size limits and the selected deployment broker remain unverified here.

Reference: [official broker configuration](https://amqtt.readthedocs.io/en/latest/references/broker_config/).

## SEC-AUTH-002 — anonymous session write amplification (fixed)

Risk: unauthenticated database growth and increasing cleanup cost; severity MEDIUM
(availability). Root cause: every no-cookie `GET /auth/session` created a persistent
15-minute row, with no issuance budget. Bounded reproduction: discard cookies for
31 requests from one client; baseline returned 200 on request 31. The new regression
failed before the fix with 200 instead of 429. No flood or storage exhaustion occurred.

Defense: at most 30 new anonymous sessions per trusted client IP per 15-minute
window, persisted as a hashed throttle key; a global ceiling of 1,000 live anonymous
sessions also bounds rotating-IP growth. Check/reservation happens inside the same
repository transaction. Caller-provided X-Forwarded-For is not used by this route.
Existing valid sessions and authenticated rotation bypass issuance quotas. Expired
rows/budgets are reclaimed. This is an anonymous-row bound, not a general HTTP,
authenticated-session, disk, or distributed denial-of-service defense. A coordinated
caller can still consume capacity; deployment connection/rate limits and expected
shared-NAT traffic sizing remain necessary.

Verification: 89 authentication/origin/session-budget tests passed in memory mode;
seven session-budget/three-building cases passed in SQLite mode, including concurrent
reservations and rotating IPs. Global-cap tests lower the constant to exercise the
same branch cheaply rather than generating 1,000 sessions. Production defaults are
30 / 15 minutes and 1,000 live anonymous sessions. No schema or dependency change.

## Tenant attack expansion

`tests/test_security_tenants.py` provisions three complete synthetic building
structures with devices and separate manager sessions, maintenance and visitors.
For each manager, only its own records appear in the snapshot/activity. Foreign
maintenance update/create, visitor arrival and device-context reads return 403 and
leave original records/actuator history unchanged. A configured Resident with an
intentionally overbroad stored permission list remains confined to its role ceiling
and cannot open Manager or foreign device views.

An initial Resident case omitted its configured affiliation and expected configured
portal confinement. Existing documented legacy/unaffiliated behavior returned 200
with only permitted scope data; this was a fixture assumption, not demonstrated
cross-tenant access. Adding the intended affiliation made the test valid; corrected
cases passed. No production authorization code was changed to satisfy the fixture.

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

Local MQTT TLS/authentication/ACL wire acceptance passed. Actual deployed proxy/browser,
host process/filesystem isolation, sustained storage pressure, broad fuzzing, and
independent human assessment are not verified in this session. Live actuator safety,
emergency egress and physical acknowledgments require hardware-specific review;
see `ASTRA_HANDOFF.md`. No physical pilot approval follows from software tests.

## Current verification ledger

- HTTP/auth/origin/deployment/privacy batch after body defense: 173 passed.
- Backend after body defense, before session defense: 1,031 passed, one SQLite-only
  test skipped (previous historical baseline 1,013).
- Auth/origins/session defense: 89 passed.
- SQLite security batch: 225 passed and one new fixture-assumption failure described
  above; corrected session/tenant subset: seven passed. Do not describe the first
  command as an entirely passing run.
- Local secure MQTT wire drill: PASS, one recorded / one duplicate / one revoked
  observation rejected, zero storage failures; no actuators.
- OSV queries: 30 pinned core requirements plus paho-mqtt 2.1.0 and aMQTT 0.11.3,
  no returned advisories on 2026-10-15. This excludes a complete installed transitive
  inventory and frontend audit; absence of an advisory is not proof of safety.
- Pattern scan across session changes (committed plus working): 11 files checked at
  that point, no findings. Not a full historical secret scan or Gitleaks replacement.
- Original preservation: all 411 source hashes match the private baseline; private
  configuration bytes and original Git status unchanged. Backup contents are not
  printed. No work in C:/dev/nodum was modified.

Final verified checkpoint results:

- **1,038 passed, one skipped** in the complete default backend suite (149.48s).
- **41 passed** in the final SQLite body/session/three-building/MQTT suites (7.35s),
  including the rollback/restart case skipped by the default repository.
- Existing direct HTTPS authentication drill passed again after both defenses:
  secure cookies, rotation, Manager session, Origin/CSRF rejection, logout,
  untrusted certificate and wrong certificate hostname.
- `http_security_drill.py`: declared oversized HTTPS request rejected 413 before
  upload (Expect/continue), one stalled partial body rejected 408 at 10.01s,
  subsequent health 200. Exactly two hostile requests per successful drill. An
  initial full-upload probe encountered an early connection reset on Windows;
  the guard intentionally closes rejected bodies. The revised probe observes
  early rejection; actual chunk-byte limits are covered by ASGI tests.
- Secure MQTT drill repeated after strengthening the read-only publication attack
  to target that collector's own subscribed topic; same passing results.
- No frontend changes; the prior 32 frontend tests are historical, not rerun here.

Reproduce the HTTPS body fixture from the worktree root:
`artifacts/install-smoke/Scripts/python.exe backend/scripts/http_security_drill.py`.

## SEC-STORAGE-003 — persistent history growth (OPEN, MEDIUM)

Authorized unique contact observations persist without retention or a storage quota;
prior bounded 250-event drill retained 251 observations including reconnect. Manager
snapshot's 100-row display cap does not bound persistent history or list scans.
An authorized/misconfigured publisher can increase disk/cleanup cost over time.
No disk exhaustion was attempted. Track with ARCH-005: measure indexed paging and
scope-safe retention before selecting policy; do not delete records ad hoc. Broker
packet/rate limits and telemetry storage budgets are still required for a real pilot.
