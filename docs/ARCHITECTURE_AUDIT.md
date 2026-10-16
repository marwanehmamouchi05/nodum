# Architecture audit — targeted engineering findings

Current closure authority: [PHASE1_FINAL_REPORT.md](PHASE1_FINAL_REPORT.md) (2026-10-16). Earlier results below are historical. Consolidated review: [ASTRA_FINAL_REVIEW_HANDOFF.md](ASTRA_FINAL_REVIEW_HANDOFF.md).

2026-10-15, isolated branch. Evidence from source inspection, real protocol drills
and automated tests. This is not a whole-codebase security certification.

| ID | Severity | Evidence and practical impact | Status / remediation |
|---|---|---|---|
| ARCH-001 | IMPORTANT | `scripts/pilot_drill.py` filtered known environment prefixes but inherited other server/proxy settings; tests could depend on operator configuration | FIXED: shared `scripts/drill_support.isolated_environment()` allowlists OS necessities; tested against injected provider, database, proxy, TLS and pip settings. Both recovery and TLS drills use it. |
| ARCH-002 | IMPORTANT | Single visitor arrival and maintenance update loaded `list_operational_records` before selecting one ID | FIXED: explicit `Repository.get_operational_record` for memory and SQLite; indexed primary-key lookup. Authorization still precedes lookup, location authorization still follows. Regression forbids bulk history loads during both mutations; existing Manager suite covers denial paths. |
| ARCH-003 | IMPORTANT | MQTT protocol depends on topic/payload semantics and tenant binding, not a universal device API | IMPLEMENTED narrowly: fixed contact payload, exact server-derived topic and sensor/building binding, per-event revocable grants, transactional activity + binding, replay digest; real local broker reconnect and malformed/retained rejection tests. No core startup dependency on Paho. |
| ARCH-004 | IMPORTANT | aMQTT test broker brings a Click requirement inconsistent with backend pins | ISOLATED: separate test-broker venv and requirement file. App pins restored; core `pip check` passed. No test broker imported into application runtime. |
| ARCH-005 | IMPORTANT | `ManagerService.snapshot` loads operational history and then truncates returned activity to 100. Permission checks are repeated per record | PARTIALLY FIXED: indexed, scope-safe operational-journal pages and contact per-device capacity implemented on the engineering branch. Other histories and approved retention/global budgets remain open. Burst test proves persistence, not long-term capacity. Do not paginate before authorization or mix tenant histories. |
| ARCH-006 | HIGH | Real actuation cannot safely be inserted into the simulator's DB transaction | ESCALATED as ASTRA-HW-001. Keep physical execution disabled until durable delivery/reconciliation and bench evidence. |
| ARCH-007 | IMPORTANT | Memory repository `transaction()` is a lock, not rollback; SQLite provides real rollback | DOCUMENTED: production collector requires SQLite. New rollback acceptance uses SQLite, not memory claims. Broader memory rollback rewrite deferred; keep test evidence classified. |
| ARCH-008 | IMPORTANT | `StructureNode` deliberately carries no verified capabilities; UI device state remains unverified | PRESERVED: MQTT observation is activity, not a general device-health/capability upgrade. Future health view needs explicit freshness/availability model and UI review. |
| ARCH-009 | IMPORTANT | Current MQTT clean-session reconnect may lose messages while offline; bounded CLI does not promise durable capture | DOCUMENTED: no exactly-once or offline queue claim. Future session/outbox/retention design needs broker-specific acceptance. Storage errors stop the collector and surface redacted failure counters. |

## Professional handoff boundaries

- Domain authorization remains in services. Optional MQTT transport has no public
  registration route, dynamic plugin loading, payload-selected scopes or actuator
  capability. Its exact contract and acceptance procedure are in `mqtt-contact.md`.
- Existing migrations are unchanged. Normalized telemetry reuses scoped operational
  activity; one additive point-read method extends the explicit repository protocol.
- No new framework, distributed queue/database or frontend redesign was introduced.
- Typed collector/event models reject extra fields; protocol and OS errors are not
  echoed with private configuration. Do not log payloads/credentials during drills.
- Verification scripts remain engineering tools, not customer installers or proof
  of deployed TLS termination, browser topology or safety commissioning.

The operational-journal paging task is now implemented and measured on the engineering branch.
Next structural work is profiling remaining histories/full snapshots and broad-scope contention;
retain all ownership filters and avoid rewriting unrelated workspace projections.


## Engineering-foundation update — 2026-10-15

Based on protected security checkpoint 6e350af in a separate managed worktree.
Migration 9 adds activity ordering index; migration 10 adds contact capacity index.
No destructive migration, architecture rewrite or frontend change. Operational
journal paging preserves live authority/binding checks. The new independent client
uses authenticated HTTPS and MQTT only; no internal imports or database mutation.
Existing pure simulator ports already represent access/reader/elevator/wayfinding;
configured product inventory remains a separate, unverified-capability layer.
An unsafe automatic bridge between those inventories was deliberately not added.

New team gates: pinned correctness lint, scoped formatting, root pytest configuration,
frontend lint/type/build and read-only, commit-pinned CI workflow. Hosted execution
and broad Python static typing are not verified. Detailed setup and extension evidence
are in DEVELOPER_ONBOARDING.md; measured limits in SCALABILITY_ASSESSMENT.md.
