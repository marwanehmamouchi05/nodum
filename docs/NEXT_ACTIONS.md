# Next development actions

Continue from `docs/development-state.json` in the isolated worktree; do not recreate
the baseline or rerun unrelated investigations. Two unsuccessful approaches or
30 active minutes without justified progress trigger reassessment/task switching.

| Priority / ID | Task | Benefit, effort and dependency | State |
|---|---|---|---|
| P1 PILOT-001 | Safe backup/verify/restore drill | High data-recovery impact, medium effort, no hardware | COMPLETED |
| P1 PILOT-002 | Read-only deployment preflight | High install reliability, medium effort | COMPLETED |
| P1 PILOT-004 | Reject malformed authentication origins | Session configuration reliability, small effort | COMPLETED |
| P1 ASTRA-HW-001 | Real actuator delivery state machine | High safety/integrity impact; vendor idempotency contract needed | ESCALATED; physical adapters stay disabled |
| P1 ASTRA-RING-002 | Confirm real Ring inbound linking | High integration impact; official partner contract/account needed | BLOCKED external dependency; handoff documented |
| P2 PILOT-003 | Read-only MQTT sensor adapter and broker fixture | Broad telemetry reuse; medium effort/uncertainty. First define topic/binding/replay contract, then test loopback broker; no actuator commands | PLANNED |
| P2 PILOT-005 | Clean-machine install + HTTPS proxy/session acceptance | High deployment impact; isolated dependency/runtime budget and chosen proxy needed | NEXT independent deployment task |
| P2 PILOT-006 | Select notification transport and scoped delivery queue | Core operation gap; clarify transport/cost/recipient consent before external sends | DEFERRED until transport chosen; no messages authorized |
| P3 PILOT-007 | Real pilot equipment acceptance | Exact model/firmware, permissions, bench and safety review needed | BLOCKED external dependency |

No automatic promotion into the original checkout. Restore drills always target a
new file. Keep the original source/config/database backup private and retain the
last validated isolated commit. Do not add fake health/credential claims to fill
hardware or pilot-readiness gaps.
