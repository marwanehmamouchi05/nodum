# Astra handoff

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
