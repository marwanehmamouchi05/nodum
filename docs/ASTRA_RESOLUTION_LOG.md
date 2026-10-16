# Review resolution log — 2026-10-16

Historical checkpoint report. Current authority: [NODUM_RELEASE_BASELINE.md](NODUM_RELEASE_BASELINE.md).

Base af7a3e1; isolated codex/astra-final-review. No edits to protected branches.
Tests/results below are actual local runs; no official Ring or physical testing.

## REV-RING-001 — documented classification lost (IMPORTANT)

Root cause: services/ring.py mapped only data.type and ignored attributes.sub_type.
Signed official-shaped human/package_delivery motion fixtures both reproduced the
failure. Correction maps these to existing person/package signals while preserving
unknown classifications as motion and original raw evidence. Legacy custom kinds
remain compatible. No automatic identity matching, access grant or actuator action.

Files: backend/app/services/ring.py; backend/tests/test_review_boundaries.py;
backend/app/api/ring.py (corrected custom-simulator comment).
Validation: four classification cases plus broader Ring regression; 188 relevant
tests passed immediately after fixes. Final 1,085 default / 272 SQLite pass totals
include these. Official runtime acceptance remains externally blocked.

## REV-RING-002 — replay content conflict ignored (IMPORTANT)

Root cause: same event identity compared a subset of fields, ignoring classification
and other event data. Reproduced human -> package change accepted as duplicate.
Correction compares canonical parsed data objects, while retaining delivery-meta
independence. Changed data returns 409 and preserves original event.

Files: backend/app/services/ring.py; backend/tests/test_review_boundaries.py.
Regression plus existing replay/cross-account tests pass in memory and SQLite.
Requires a valid signature; this is an integrity contract defect, not unsigned
webhook acceptance. Vendor-origin runtime remains unverified.

## REV-COMMAND-001 — adapter output exceeded service authority (IMPORTANT)

Root cause: command results validated only schema and device ID. Reproduced four
accepted outputs: longer unlock lease, wrong command ID, changed authorized person
and unrelated floor change. Correction adds command-specific allowed fields and
authorized-context validation in a small service helper; copies input before calling
the adapter. Invalid output produces failed audit and leaves saved state unchanged.

Files: backend/app/services/building.py; backend/app/services/simulated_commands.py;
backend/tests/test_review_boundaries.py.
Tests: invalid outputs; mutation then timeout; lost response/exact replay; terminal
failure replay; delayed adapter/competing lock; SQLite rollback after audit-write
fault; three-building API attempts; alternate display adapter. Existing suite covers
expired/revoked policy, emergencies, offline/manual outcomes and restart. All pass.

Limit: trusted Python adapter code is not sandboxed. Pure simulation remains the
only actuator execution path. Durable physical outbox/reconciliation is specified
in ADR 0002, not implemented or represented as verified delivery.

## REV-STORAGE-001 — no executable policy preview (MEDIUM)

Root cause: previous lifecycle work had budgets and a policy document but no scoped
what-if planner. Added a service-level contact-only dry-run with explicit cutoff,
live configuration/read authority, page/scan cap, protected classes, supplied holds,
truncation and machine-readable blockers. There is no apply/delete/archive method.

Files: backend/app/services/retention.py; backend/tests/test_retention_plan.py;
docs/DATA_LIFECYCLE.md. Eight tests pass in SQLite and default suite: isolation,
revocation, bounded/truncated scan, strict receipt-time cutoff, invalid inputs,
holds/protected records and unchanged data/idempotency. Hypothetical hold IDs are
not an authoritative hold registry. Owner policy/archive/replay decisions remain.

## Review acceptance and team handoff

New tests added to .github/workflows/verify.yml SQLite acceptance. Local full suite:
1,085 passed / four SQLite-only skipped; SQLite batch: 272 passed. Frontend unchanged,
fresh install + 34 tests/lint/type-build passed. Fresh backend/pip check passed.
Actual proxy/browser, MQTT TLS/auth/ACL, independent external full-stop recovery and
backup/restore/startup passed. Benchmark reproduced and raw metrics committed.

Reports: ASTRA_INDEPENDENT_REVIEW.md, PHASE2_READINESS_DECISION.md and updated
DIGITAL_TWIN_PHASE2_HANDOFF.md. Original/foundation/security/demo preserved.
Remaining external dependencies are explicit; no unresolved defect is reclassified
as physical readiness. Hosted CI, official Ring, encrypted operational backup
commissioning, fleet capacity and physical safety remain unverified.

## Finalization checkpoint

Tested implementation: `bcf5f9da1964cb462b1f44d307b5defc41776113`.
Final documentation is at HEAD of `codex/astra-final-review`; see
`DIGITAL_TWIN_PHASE2_HANDOFF.md` for the exact integration boundary.
No Phase 2 development, merge or deployment is part of this review.
