# Astra final review handoff

2026-10-15. Review source checkpoint **254eee5** plus the final documentation commit
on `codex/engineering-foundation`. Do not use the original `C:/dev/nodum` working
files or the frozen meeting demonstration for experiments. This is a local handoff;
no Astra run/message has been dispatched. PHASE1_FINAL_REPORT.md is the readiness
authority; PHASE1_CLOSURE_BACKLOG.md is the single classified backlog.

The bounded software foundation is complete with external blockers. Physical pilot
and production commissioning are not approved. Do not start the independent
simulator until the scoped review below is complete and any findings affecting its
supported contact contract have been resolved. External Ring/hardware/policy access
cannot be manufactured through code review.

## 1. ASTRA-RING-002 — official linking and runtime evidence

- **Severity/impact:** HIGH integration/submission blocker. Current live inbound
  adapter is disabled; no confirmed exploit in the usable simulation scope.
- **Exact code:** `backend/app/api/ring.py::receive_verified_ring_code`,
  `token_exchange`, `claim_account_redirect`; `backend/app/services/ring.py::
  receive_code`, `claim`, `access_token`, `receive_event`; `backend/app/integrations/
  ring/client.py::RingClient.exchange/profile/discover/confirm/complete` and
  `ring/config.py::RingSettings`. Routes/functions remain authoritative if names
  evolve; inspect them before implementing. Procedure: RING_DEMO_PROCEDURE.md.
- **Current/expected:** REST token/discovery/confirmation, HMAC nonce ownership,
  encrypted tokens, signed normalized webhooks and custom scenarios are tested.
  Live code receipt returns 503. Expected is a provider-confirmed authenticated
  code/callback transport and official consent/link/device/event proof.
- **Evidence/reproduction:** full backend Ring/product regression and fresh Vite
  browser custom visitor-arrival produced three persisted simulated signals
  (`verification/onboarding-20261015.json`). Follow the official acceptance steps
  in RING_DEMO_PROCEDURE.md with an authorized portal; none was available here.
- **Attempted:** current official API/Configure comparison on Oct 15, code-boundary
  inspection, mock/signed scenario tests and actual custom browser scenario. No
  live token request, portal edit or speculative inbound decoder.
- **Why not proceed:** configured app linking method, exact Ring-driven inbound
  authentication/body encoding and permitted official test account are unknown.
  PKCE is invitation-only; public documentation does not establish app entitlement.
- **Options:** retain Ring-driven mode and implement only the confirmed transport;
  or separately review a permitted partner-initiated migration with PKCE/state,
  exact redirect allowlist, session binding and callback replay protection. Do not
  mix methods or infer ownership from an unverified code.
- **Exact Astra task:** obtain/redact the portal configuration and provider delivery
  sample with the owner; reconcile code against it, specify acceptance fixtures,
  implement the smallest verified boundary, and independently validate token/event
  isolation. If access remains absent, return a precise external-blocked result.
- **Acceptance:** successful official staging/tool linking and device event capture;
  reject wrong issuer/client/user, expired/replayed nonce/code/state and revoked
  tokens; refresh rotation/rollback and cross-account/building denial; preserve
  custom simulation and logical visitor workflows. No private tokens in output.
- **Dependencies/risks:** owner-authorized app/portal credentials, approved scopes,
  exact registered HTTPS URLs and consented official tool/device access; outside
  this code checkout. Mode changes can break submission/demo timing and privacy.

## 2. ASTRA-HW-001 — durable real command delivery boundary

- **Severity/impact:** HIGH for real actuation; does not block read-only contact
  monitoring or pure simulators. Network I/O in the simulator transaction can hold
  SQLite's writer lock and leave physical outcome unknown after timeout/crash.
- **Exact code:** `backend/app/services/building.py::BuildingService.action`,
  `scan`, `choose_device`; `backend/app/integrations/building.py::CommandContext`,
  adapter protocols and `ConnectorRegistry`; `backend/app/models/integrations.py`
  command/state/audit models; scoped legacy mutation guard in
  `backend/app/services/authorization_operations.py::authorize_operation` (called
  from `backend/app/api/authorization.py`).
- **Current/expected:** pure simulated transformation and audit commit together;
  no live provider execution is enabled. Expected real delivery has stable command
  IDs and explicit queued/sent/acknowledged/unknown/failed outcomes, revocation,
  bounded retries and reconciliation, without implying physical confirmation.
- **Evidence/reproduction:** inspect the transaction around adapter dispatch.
  `test_building_integrations.py` covers capability/policy, duplicate replay,
  failure, credentials, elevator requests and wayfinding; included in final SQLite
  139-test run. Never reproduce on a real door/lift/life-safety controller.
- **Attempted:** existing registry, policy ordering, simulator behavior and failure
  auditing reviewed; no live-I/O bridge or speculative migration added. Configured
  StructureNode inventory deliberately still has no verified capabilities.
- **Why not proceed:** no selected controller API, provider idempotency/readback
  semantics, bench or owner-approved command/safety procedure. A generic timeout
  retry can duplicate physical action; “success” cannot mean merely sent.
- **Options:** durable outbox outside network transactions plus provider command-ID
  reconciliation, or remain read-only until a supported vendor contract is chosen.
  Keep configuration/telemetry and high-risk commands as separate capabilities.
- **Exact Astra task:** decide minimal state machine, transaction boundaries,
  authorization expiry/revocation rules and reconciliation; propose an additive
  migration and deterministic crash/fault fixture. Implement only the reviewed
  software boundary; actual bench execution needs separately authorized access.
- **Acceptance:** crash before/after send, duplicate request, stale/revoked grant,
  competing workers, provider rejection, unknown outcome, readback reconciliation
  and cross-building denial; prove no SQLite transaction remains open during I/O.
  No unauthorized or automatically retried physical action; preserve simulation.
- **Dependencies/risks:** exact controller documentation, dedicated safe bench,
  owner/vendor safety review, emergency/egress requirements. Elevators/life safety
  are not generic command adapters. Do not loosen the legacy scoped HTTP guard to
  make a future simulator pass.

## 3. ASTRA-STORAGE-003 — approved lifecycle and fleet envelope

- **Severity/impact:** MEDIUM availability/privacy/audit dependency; sustained
  operational ingestion remains unapproved. Per-device contact capacity protects
  this bounded lab, but other histories and aggregate disk growth are unbounded.
- **Exact code:** `backend/app/integrations/mqtt_sensor.py::ContactIngestor.receive`,
  `backend/scripts/mqtt_collect.py`; `backend/app/manager_repository.py::
  count_contact_observations/page_operation_activity`; `backend/app/services/activity.py::
  ActivityService.page`; `backend/app/maintenance.py::copy_database/inspect_database`;
  `backend/app/database.py` additive migrations 9/10. See DATA_LIFECYCLE.md.
- **Current/expected:** configurable per-device reject-at-capacity, indexed
  authorized keyset pages and safe new-path backup/restore; no deletion/archival.
  Expected policy separately defines observations, security/audit, identities and
  backups, fleet budget, legal holds and authority reconciliation after restore.
- **Evidence/reproduction:** `test_contact_budget.py`, `test_activity_pages.py`,
  `test_maintenance.py`, new three-building concurrent test and full environment
  restore drill pass. Use small synthetic capacity; never fill a real disk.
- **Attempted:** non-destructive persistent cap/paging, schema upgrade/index tests,
  consistent snapshots and measured history query; no guessed retention duration.
- **Why not proceed:** owner has not selected horizons, protected archive target,
  incident preservation/replay rules or a fleet storage/availability envelope.
  Those are business/privacy decisions, not authority an agent can assume.
- **Options:** bounded reject-only lab (current), approved fleet ceiling, or encrypted
  scoped verified archive before separately approved pruning. Tradeoffs and data
  classes are in DATA_LIFECYCLE.md; no claim of legal compliance is made.
- **Exact Astra task:** separate owner decisions from code, request a finite written
  policy, then design the smallest compatible budget/archive maintenance contract
  and migration. Review deduplication, binding and restoration consequences first.
- **Acceptance:** accurate scoped dry-run, unauthorized export/delete denial,
  holds, bounded atomic apply, interrupted archive/restore, duplicate/replay after
  pruning, no dangling bindings and no resurrection of revoked authority without
  explicit recovery reconciliation. Existing records remain until approved apply.
- **Dependencies/risks:** owner-approved policy and encrypted/protected archive
  infrastructure, with appropriate compliance advice where needed. Astra can
  implement a policy; it cannot invent approval or erase audit history.

## Independent review checklist and ordinary external commissioning

Review the bounded changed interfaces, not an undefined whole-application rewrite:

1. Reproduce `DEVELOPER_ONBOARDING.md` and the final external contact drill. Check
   client independence/evaluator mutation tests and restore revocation assertions.
2. Inspect ActivityService/repository authorization before LIMIT and live binding
   rechecks; run activity/capacity/tenant/concurrency tests in SQLite mode. Keep the
   per-device cap within one transaction and all historical records intact.
3. Inspect HTTP receive guard and persisted session budgets; rerun security tests
   and actual broker TLS/auth/ACL proof. Investigate concrete failures; do not
   certify the whole product from a suite count.
4. Reproduce Caddy/browser acceptance and URL restoration with restricted roles.
   UI URL state is navigation only; backend authority remains unchanged.
5. Report a bounded verdict and exact repairs. Do not enable physical providers,
   silently switch Ring methods, choose deletion periods, merge, deploy or begin
   the simulator automatically.

Owner/deployment engineer selects production domain/OS/service manager, TLS renewal,
trusted network hops, broker accounts/ACLs, backup encryption/schedule and monitoring;
then repeats commissioning on that target. Authorized repository CI must run after
publication; only local workflow commands/syntax are verified. These external
commissioning tasks are not open-ended Astra code assignments.

Future simulator work may reuse only the verified HTTPS/contact-v1 contracts after
Astra accepts that boundary. Official Ring, durable offline delivery and physical
commands remain separately gated. No new simulator source was created in Phase 1.
