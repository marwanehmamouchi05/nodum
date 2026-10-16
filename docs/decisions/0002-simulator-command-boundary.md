# 0002: preserve pure simulation; validate results before atomic persistence

2026-10-16. Accepted for software simulation only.

## Decision and implemented boundary

Keep BuildingService.action synchronous and transactionally persist simulated
state plus its immutable command receipt. Do not insert network I/O into this
transaction. The caller's command ID and payload digest make exact replay a lookup,
not another dispatch. A replayed `executed` receipt describes historical simulation,
not current state, renewed permission, physical delivery or an open door.

The new services/simulated_commands.py validates adapter output independently of
the adapter: same device, correlation and timestamp; command-owned fields only;
lease no longer than policy allows; exact authorized person/zone/floor/route.
Input is copied before dispatch. Invalid output gets a redacted failed receipt and
does not replace device state. Existing typed schemas and API responses are retained.

The registry is trusted server wiring, not a sandbox for hostile executable code.
The validator contains adapter mistakes; it cannot prevent arbitrary Python I/O.
Memory transactions still do not roll back. SQLite acceptance is mandatory.

## Evidence

test_review_boundaries.py reproduces four previously accepted invalid outputs,
tests mutation-before-error, terminal failure replay, lost caller response,
deterministically delayed dispatch competing with a lock, atomic SQLite rollback
when receipt persistence fails, and three-building HTTP denial. Existing integration
tests cover fresh policy, revocation/expiry, offline/disabled/manual paths, duplicate
conflicts, restart, permissions and emergency denial.

A second digital-display adapter is wired through ConnectorRegistry in the test;
it implements the existing display port without changing unrelated services. This
is an extension exercise, not a physical adapter or proof that arbitrary categories
fit the present fixed enum. New protocol/category semantics need reviewed contracts.

## Future physical delivery contract (NOT implemented or enabled)

| State/evidence | Meaning | Safe next step |
|---|---|---|
| Requested | Authenticated intent received | Validate current authority, identity and capability |
| Queued | Intent and outbox committed atomically | Worker claims bounded lease with compare-and-set |
| Dispatch reserved | Worker rechecked revocation, binding/version and expiry | Commit attempt ID, then perform I/O outside transaction |
| Acknowledged | Provider confirms receipt with command ID | Await execution report; never infer physical state |
| Reported executed | Provider reports execution | Preserve provenance; reconcile independent readback if supported |
| Unknown | Timeout/crash after possible send | No blind retry; provider lookup/reconciliation or manual review |
| Rejected/expired/cancelled | Definitive non-delivery | Terminal record; new intent requires new authorization |
| Physically observed | Independent scoped timestamped readback | Separate observation, never inferred from successful HTTP |

Before a real adapter: additive durable outbox/attempt tables, immutable tenant and
device binding, payload digest, authorization expiry, unique command key per scope,
worker lease/version, provenance and append-only audit. Competing workers must not
claim one attempt. Crash before send may safely resume only when non-delivery is
known; crash after reservation must become unknown unless the provider guarantees
idempotency/status lookup. Revocation cancels unsent work; it cannot recall a
physical command already accepted. Do not automatically send an inverse command.

Acceptance must inject crashes before/after send, dropped/late ACK, wrong-device
ACK, reconnect, concurrent claims and revoked grants, while proving no SQLite write
transaction is held during I/O. Manufacturer command semantics, an authorized bench,
controller idempotency/readback, egress and safety acceptance remain prerequisites.
Elevator requests and life-safety monitoring must use approved interfaces; this
software decision is not authorization to control those systems.

The contact-v1 lab does not need this delivery subsystem. Building it now without
a selected controller or supported external command contract would add unverified
infrastructure; scoped legacy actuator mutation remains denied.
