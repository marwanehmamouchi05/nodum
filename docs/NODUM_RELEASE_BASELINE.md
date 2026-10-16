# Nodum official release baseline — 2026-10-16

## Repository and authoritative checkpoint

Official repository: https://github.com/marwanehmamouchi05/nodum (private).
Default branch: `main`. Original local repository: `C:/dev/nodum`.
Release checkout: `C:/Users/marwa/.codex/worktrees/release-20261016/nodum`.
Final release commit: immutable tag `nodum-foundation-20261016^{commit}`.
Resolve it with `git rev-parse nodum-foundation-20261016^{commit}` after fetching.
The tag identifies the commit containing this document without a self-referential
hash. Exact remote SHA is also reported at delivery; publication receipt is below.

All requested checkpoints are ancestors of the tested candidate: `40b4769`,
`c8db547`, `6e350af`, `2ffbaab`, `af7a3e1`, `bcf5f9d`, and
`e1110dc602730ba2e69fc5540bb0058ab618c086`. Imported Phase G changes (`ed0a187`,
`86ab9c8`) and the product platform are included. Remote main was `71927dd`;
integration is a normal fast-forward, without cherry-picks or conflicts.
Release changes are documentation only; application source and pins are unchanged.

Recovery refs `codex/recovery-main-20261016` and `codex/recovery-product-20261016`
preserve the previous official/local branch tips. The original working tree remains
intentionally dirty with its pre-existing user work; do not reset it to main.

## Implemented product and contracts

Nodum provides scoped Admin, Manager, Resident and Business building workflows:
configuration/delegation, visitors/passes, maintenance, notices and activity.
Implemented protections include authentication/session limits, CSRF/exact Origin,
request bounds, tenant/resource authorization, MQTT TLS/ACL/revocation, Ring replay
integrity and constrained pure simulator command results. Indexed activity pages,
contact capacity, backup/restore/preflight and safe startup are verified. Retention
preview is bounded and read-only; no deletion/archive application path is enabled.

External lab contracts: authenticated HTTPS provisioning/session/scoped observation
and TLS MQTT contact-v1, with exact per-device topics, strict payloads, duplicate
handling and fresh authority checks. See [exact handoff](DIGITAL_TWIN_PHASE2_HANDOFF.md)
and [contract](DIGITAL_TWIN_INTEGRATION_CONTRACT.md). No external actuator contract,
universal discovery or durable offline capture is claimed. Internal access,
elevator and display simulators do not prove physical execution.

## Actual combined verification

Executed against source `e1110dc602730ba2e69fc5540bb0058ab618c086` in the release
checkout; later changes only document the result.

| Check | Result |
|---|---|
| Full backend suite | 1,085 passed, 4 SQLite-only skipped; 106.37 s |
| SQLite batch | 272 passed; 45.80 s; all four skipped cases covered |
| Fresh npm ci and frontend tests | 160 packages; 34 passed, zero failed |
| Frontend lint and TypeScript/Vite build | PASS |
| Fresh Python core/MQTT/dev and separate broker installs | PASS; both pip checks clean |
| Python correctness lint | PASS |
| External HTTPS/MQTT full-stop recovery | PASS, 18.28 s; two buildings, three durable events |
| MQTT TLS/auth/ACL wire checks | PASS; wrong trust/hostname/credentials, four denied subscriptions, three blocked publications, positive controls and revocation |
| Backup/restore/preflight/startup | PASS; schema 10 integrity/FKs, health200, anonymous401, docs404 |
| Caddy/browser workflows | PASS; login, visitor/pass, refresh/deep links, cookies, CSRF/Origin, validation/logout, forged Admin route denied, zero page errors |

SQLite files: activity_pages, contact_budget, session_budget, security_tenants,
mqtt_sensor, request_limits, maintenance, foundation_concurrency, review_boundaries,
retention_plan, building_integrations, ring. Full regression includes authentication,
authorization, tenant isolation, Ring simulation and migration compatibility.
External counts: recorded3/duplicate1/rejected2/failed0; restored collector
recorded0/rejected1/failed0. Negative observation is bounded to 0.75 seconds.
All temporary fixtures stopped. No clean production OS or fleet SLA is certified.

## Install, start, demo and tests

Follow [developer onboarding](DEVELOPER_ONBOARDING.md) for Python 3.13, Node 24,
pinned requirements, optional MQTT/separate broker, npm ci, tests and lint.
Use a new checkout/environment without production credentials. Run
`backend/.venv/Scripts/python.exe backend/demo_product.py --start` for the disposable
synthetic demo, then the documented frontend command targeting loopback port 8770.
The launcher prints synthetic accounts and uses temporary storage; never deploy it.
For persistent empty setup follow [provisioning](product-release.md#local-startup-and-first-install)
with an explicit new SQLite path and exact origin. See [recovery](backup-recovery.md),
[proxy acceptance](DEPLOYMENT_VERIFICATION.md) and [architecture](ARCHITECTURE_OVERVIEW.md).

## Official Ring Playground investigation

Source/history, development logs, Ring documentation, saved review/runtime artifacts
and known local configuration variable names were inspected without exposing values.
No successful authenticated official Playground request/response or Nodum processing
capture was located. Known smoke settings contain simulation signing/encryption
configuration; no usable official Playground token was located. A token previously
entered is not proof of a successful request. Current tests demonstrate mocked REST
and signed custom events, not official Playground runtime.

**Hackathon integration remains BLOCKED.** Physical Ring hardware is not required
for a Playground demonstration. Missing: authorized official Playground session/token,
supported endpoint execution, redacted URL/status/correlation evidence and observed
Nodum processing. Confirm portal linking mode and authenticated inbound delivery
contract; current live code-delivery adapter remains fail-closed (503). Do not import
Playground credentials into the custom simulator or invent an inbound decoder.
See [Ring procedure](RING_DEMO_PROCEDURE.md). No external test was attempted without
usable credentials; no hackathon eligibility guarantee is claimed.

## Security and preservation

537 outgoing history blobs checked for private-key, AWS access-key and GitHub-token
patterns: zero matches. No tracked dotenv/database/private-key files found. Ignore
rules cover private config, generated artifacts, databases and keys. This is a
bounded pattern scan, not universal secret detection. Fixture credentials are
synthetic; no real provider credentials or resident data were added.

411 original source hashes, three private configurations, original Git-status bytes
and backup integrity/FKs match the preserved baseline. Security, foundation, review
and meeting-demo refs remain intact. Repository CI only verifies; no repository
webhooks or Pages deployment exist. GitHub reports main unprotected with no required
checks; detailed protection/ruleset APIs are unavailable under the current plan.
No protection is disabled or bypassed. No infrastructure deployment is authorized.

**Physical pilot NOT APPROVED:** supported hardware, safe command delivery/readback,
authorized safety/egress bench, commissioned host/network/broker, secrets, monitoring,
backup/revocation reconciliation and approved lifecycle/archive/fleet policy remain.

## Next phase

Use official main at `nodum-foundation-20261016` for separately authorized Virtual
Building Lab work. The HTTPS/contact boundary is ready with limitations. This
assignment did not start that lab, deploy infrastructure or operate physical devices.
Historical reports remain dated evidence; this document supersedes current-status
claims in those earlier reports.

## Publication receipt

Release branch `codex/release-20261016` was pushed and its candidate
`017c4f83415028961817cbab89f3270c3372dfe0` passed both hosted Ubuntu jobs:
[GitHub Actions run 38975412602](https://github.com/marwanehmamouchi05/nodum/actions/runs/38975412602).
Backend regression, SQLite checks, installation, lint/format, external HTTPS/MQTT
recovery and startup all passed; frontend installation/tests/lint/build passed.
This final receipt changes documentation only. The release tag identifies the final
commit promoted to main; final remote reachability and tree equality are checked
at delivery. No source fix or merge conflict was required.

**SOFTWARE FOUNDATION FINALIZED** on successful remote promotion of that tag.
**SIMULATOR INTEGRATION READY WITH LIMITATIONS.** **HACKATHON RING BLOCKED.**
**PHYSICAL PILOT NOT APPROVED.** The original user checkout is intentionally preserved.

Final diff review found one pre-existing extra EOF blank line in
`backend/app/services/authorization_operations.py`; it has no runtime effect and
was preserved with the tested source. Changed release documents pass diff checks.
