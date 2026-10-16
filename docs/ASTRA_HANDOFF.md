# Astra handoff

Current closure authority: [PHASE1_FINAL_REPORT.md](PHASE1_FINAL_REPORT.md) (2026-10-16). Earlier results below are historical. Consolidated review: [ASTRA_FINAL_REVIEW_HANDOFF.md](ASTRA_FINAL_REVIEW_HANDOFF.md).

2026-10-15. Two issues documented for reasoning review. No external message or live
Astra execution has been performed. Independent maintenance/security work continues.

## ASTRA-HW-001 — Physical command delivery and reconciliation

1. Severity: HIGH; blocks safe real actuators, not software simulation.
2. Impact: inserting network I/O into simulator dispatch can hold the SQLite write
   lock and leave physical outcomes uncertain after timeout/crash.
3. Files/functions: `backend/app/services/building.py` command dispatch;
   `backend/app/integrations/building.py` `CommandContext`, adapter protocols,
   `ConnectorRegistry`; `backend/app/models/integrations.py` action/audit models.
4. Current: state transformation and command audit commit in one repository
   transaction; public provider registration only admits simulators.
5. Expected: explicit queued/sent/acknowledged/unknown/failed states for real I/O,
   stable command IDs, authorization refresh and bounded delivery/reconciliation.
6. Reproduce: inspect service transaction surrounding adapter execute. No real
   provider is installed; do not reproduce with actual door commands.
7. Investigation: existing registry/capability model and tests reviewed; physical
   providers deliberately left disabled. No schema or hardware mutation attempted.
8. Uncertainty: vendor idempotency and readback vary; no target controller selected.
9. Options: durable outbox plus provider command-ID reconciliation; begin read-only
   telemetry first. A timeout must never be automatically described as execution.
10. Requested work: decide minimal delivery state machine, transaction boundaries,
    authorization expiry/revocation behavior and audit retention; propose additive
    migration and simulator fault fixture before implementing real dispatch.
11. Acceptance: crash before/after send, duplicate submission, stale grants,
    concurrent workers, unknown outcome, provider rejection, reconciliation and
    cross-building command denial. Demonstrate no SQLite lock during network I/O.
12. Dependencies: selected documented controller API, dedicated test bench, command
    idempotency/readback contract and owner-approved physical test procedure.

## ASTRA-RING-002 — Confirm live inbound account-link contract

1. Severity: HIGH integration blocker; signed simulation remains usable.
2. Impact: real account linking cannot be claimed from mocked tokens/events.
3. Files/functions: `backend/app/api/ring.py` linking/token-exchange endpoints,
   `backend/app/services/ring.py`, `backend/app/integrations/ring/` client/config;
   `docs/ring-integration.md` existing contract notes.
4. Current: documented API client and simulation coverage; live inbound delivery
   adapter remains fail-closed until provider contract confirmation.
5. Expected: verified issuer/client authentication, nonce/user binding, expiry and
   replay handling for the actual provider-approved delivery flow.
6. Reproduce: follow the documented linking flow in an authorized staging account;
   no such account/confirmed delivery contract is available to this isolated run.
7. Investigation: preserved existing boundaries and product-release flow tests;
   no live token request, account linking or camera access attempted.
8. Uncertainty: guessing token transport or ownership would undermine privacy.
9. Recommendation: obtain current official partner contract and redacted examples;
   map exact issuer/audience/transport requirements before implementation.
10. Requested work: reconcile documented provider flow with endpoint code, implement
    only the confirmed inbound adapter, and retain simulation separately.
11. Acceptance: legitimate linking, wrong user/client/issuer, expired nonce, duplicate
    delivery, rollback, token refresh/revocation and no cross-building event leakage.
12. Dependencies: owner-authorized provider staging account, official documentation
    entitlement and secret provisioning outside Git. No approval to send real commands.


## ASTRA-RING-002 update — current linking-mode decision, 2026-10-15

1. Severity: HIGH submission/integration uncertainty; existing live inbound adapter
   remains fail-closed, not a newly demonstrated exploit.
2. Modules: `app/api/ring.py`, `app/services/ring.py`, `app/integrations/ring/`,
   `docs/ring-integration.md`; Ring portal settings are outside this checkout.
3. Current official API documentation now describes both Ring-driven linking and
   partner-initiated OAuth with PKCE/state. It says one configured method per app.
   Current Nodum implements the Ring-driven nonce/account association path and
   gates the unconfirmed inbound code transport. No live staging proof is present.
4. Expected: the configured portal mode and exact authorized inbound/callback
   contract determine implementation; never infer ownership from an unverified code.
5. Reproduce: compare the current official guide sections 5/6 and partner-initiated
   OAuth against endpoint/dependency code; inspect portal mode in an authorized account.
6. Evidence: current official docs reviewed; Ring/custom-simulation regression suites
   retained. External MQTT proof explicitly reports official Ring NOT TESTED.
7. Attempts: source/docs comparison only; no account access, live token exchange,
   speculative callback adapter or developer-portal change.
8. Uncertainty: no authorized portal mode/settings, inbound transport example or
   official playground capture available in this session. Switching paths without
   that evidence risks breaking current linking and submission timing.
9. Options: retain Ring-driven mode and obtain exact authenticated delivery contract;
   or separately approve a partner-initiated migration with complete PKCE/state,
   redirect allowlist, session binding, token storage and callback replay tests.
10. Requested Astra work: choose the smallest safe path from confirmed portal evidence,
    specify acceptance fixtures and review the ownership/nonce or OAuth state boundary.
11. Acceptance: authorized official simulator/staging end-to-end capture; wrong
    issuer/client/user, expired/replayed nonce/code/state, revoked tokens, refresh,
    rollback and cross-account/device isolation; preserve existing product workflows.
12. Dependencies/risks: authorized Ring portal/playground, correct scopes and secrets,
    exact registered HTTPS URLs, available time before Oct 23. Do not guess credentials,
    use real accounts without authorization or call the MQTT lab an official Ring simulator.

Sources: https://developer.amazon.com/docs/ring/api-documentation.html and
https://developer.amazon.com/docs/ring/configure.html. Handoff documented locally;
no external Astra review or message has occurred.


## ASTRA-STORAGE-003 — fleet archive/retention policy (MEDIUM)

1. Severity: MEDIUM availability/audit-policy decision; contact growth now has a
   per-device guardrail, so this does not block the bounded external contact proof.
2. Modules: `app/manager_repository.py`, `app/services/activity.py`,
   `app/integrations/mqtt_sensor.py`, `app/maintenance.py`, migration history.
3. Observed: operational journal reads are paged and contact capacity is durable;
   other histories and total fleet storage remain unbounded. No deletion occurs.
4. Expected: an explicit archive/retention/global-budget policy with replay and
   restore guarantees before sustained operational ingestion.
5. Reproduce: review a configured collector at its capacity and the bounded benchmark;
   do not fill a real disk or erase records to demonstrate the issue.
6. Evidence: indexed capacity/restart/concurrency tests, safe capacity status,
   query-plan tests, and measured 1/10/100 scope histories.
7. Attempts: indexed paging and non-destructive budget implemented; destructive
   retention deliberately not guessed from the lack of policy requirements.
8. Uncertainty: no owner-selected audit horizon/archive store, incident preservation
   policy, replay horizon or fleet storage envelope. Choosing what to erase is not
   a routine performance optimization.
9. Options: encrypted immutable archive + verified export/restore before pruning;
   finite fleet budget rejecting ingestion; partitioned journal with reviewed cutoffs.
10. Requested work: specify the smallest compatible policy, its budget ownership,
    schema changes, backup ordering and the exact operator maintenance contract.
11. Acceptance: cross-tenant deletion/export denial, dry-run accuracy, atomic bounded
    apply, interrupted archive/restore, duplicate/replay after retention, evidence
    preservation and recovery with no dangling bindings.
12. Dependencies/risks: explicit retention/archive requirements, protected target
    storage and review of any destructive migration/tool. No archive/delete operation
    or external Astra communication is authorized by this local handoff itself.
