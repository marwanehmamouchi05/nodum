# ADR 0001 — indexed operational activity and independent observers

Accepted 2026-10-15 on the isolated engineering branch.

The Manager previously loaded every operational journal record and authorized each
before returning the newest 100. Telemetry makes this cost grow with total history.
Independent equipment tests also lacked a bounded observation/correlation contract.

Decision: keep the modular monolith and SQLite. Migration 9 adds an expression
index only; no record or table is removed. The repository performs an indexed top-N
per currently authorized scope, verifies matching resource binding before LIMIT,
and merges candidates by `(at, id)` descending. Maximum 101 candidates per scope.
Manager's operational-journal contribution uses this query; other timeline sources
and workspace projections retain their existing contracts.

`GET /manager/activity` exposes version 1 operational-journal pages only, with a
100-item maximum and validated opaque keyset cursor. No OFFSET, totals or internal
digests/password/person fields. Scope grants and record-level confinement are
rechecked on every request. A cursor is navigation, not an authority credential;
sparse ownership-filtered pages can have no items and still carry a next cursor.
Records inserted newer than the cursor appear on refresh, not mid-pagination.
The cursor reflects existing UTC ISO journal strings; arbitrary timestamp ordering
or backfill semantics are not added. Live visibility can change when grants change.

MQTT rows add an optional `source_event_id` for external correlation. This is a
backward-compatible JSON field, not physical identity, permission, or health.
Older observations can lack it. No new command adapter or live actuation is enabled.

Consequences: work scales with authorized scope inventory and bounded candidates,
not total JSON journal history; scope/grant resolution is still a measured cost.
SQLite remains a single-writer store. This does not provide quotas, retention,
durable offline delivery, or pagination of Ring/actuator/appointment histories.
No audit deletion is introduced. Retention requires a separate reviewed policy.

Evidence: `tests/test_activity_pages.py`, existing Manager/MQTT/recovery suites,
external contract drill and reproducible activity benchmark. SQLite query-plan
acceptance requires the new index without a temporary sort for each scope.
