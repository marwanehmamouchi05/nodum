# Phase 1 closure backlog

2026-10-15. One prioritized list; the final report is the readiness authority.
Classifications describe remaining responsibility, not speculative vulnerabilities.

| Priority / item | Classification | Closure evidence or bounded remaining action |
|---|---|---|
| 1. Official Ring account, portal mode and official simulator evidence | REQUIRES EXTERNAL ACCESS OR HARDWARE | Owner-authorized portal, registered HTTPS URLs, issued credentials/approved scopes and test account/device or official tool access absent. Custom simulation is preserved; see RING_DEMO_PROCEDURE.md. |
| 2. Confirmed Ring inbound delivery/callback adapter | REQUIRES ASTRA | ASTRA-RING-002 in ASTRA_FINAL_REVIEW_HANDOFF.md; no guessed payload/authentication or automatic mode switch. |
| 3. Local reverse proxy and actual browser | COMPLETED | Caddy HTTPS/static frontend/private HTTP API; browser login, invitation/pass, role/section refresh, CSRF/Origin and error/logout denial. Was FIXABLE NOW; reproduced and corrected refresh behavior. |
| 4. Production commissioning | REQUIRES OWNER DECISION | Select host/domain, TLS ownership, trusted proxy hops, operator/monitoring and backup storage; rerun selected deployment acceptance. No public deployment authorized. |
| 5. Contact capacity, query paging, non-destructive lifecycle | COMPLETED | Existing durable per-device configurable ceiling, indexed tenant pages and backup/restore. Capacity/restart/concurrency tests passed. No automatic deletion. |
| 6. Retention, archive and fleet budget policy | REQUIRES OWNER DECISION | Separate observations, security/audit, identity and backup rules; approve horizons, legal holds, restore/replay policy and encrypted archive target. Options in DATA_LIFECYCLE.md. |
| 7. Implement approved archive policy | REQUIRES ASTRA | ASTRA-STORAGE-003; policy-dependent implementation, not an incomplete unapproved cleanup job. No duration or deletion authority currently exists. |
| 8. Critical/high confirmed security defects in usable scope | COMPLETED | No unresolved confirmed critical/high issue identified in the bounded regression. Body guard, session budgets, tenant/object checks and broker boundaries pass; not a complete security assessment. |
| 9. Hardware extension contracts / two categories | COMPLETED | Contact monitoring through real MQTT wire; distinct wayfinding/display and access/reader/elevator pure simulator tests. Physical compatibility is not established. |
| 10. Durable physical command delivery | REQUIRES ASTRA | ASTRA-HW-001; keep physical dispatch disabled, design outbox/reconciliation before device-specific bench tests. |
| 11. Exact equipment and safety bench | REQUIRES EXTERNAL ACCESS OR HARDWARE | Selected models, vendor contracts, dedicated authorized bench and safety/egress acceptance required; no purchase requested before selection. |
| 12. Complete external stop/restore drill | COMPLETED | HTTPS provisioning, MQTT correlation/duplicates/malformed/reconnect/revocation; API + broker + collector stopped, snapshot restored to a new path; external API observations and revoked ingestion verified after restart. Was FIXABLE NOW. |
| 13. Practical onboarding / quality | COMPLETED | Fresh pinned backend and frontend installation, running frontend/API topology, real resident workflow, tests/lint/type-build and extension guide. Browser callback and proxy fixture committed; local Windows evidence only. |
| 14. Hosted CI observation | REQUIRES EXTERNAL ACCESS OR HARDWARE | Workflow is configured with pinned actions/read-only permissions and local commands verified. A repository runner execution requires authorized publication/access; no hosted run claimed. |
| 15. Representative reliability and large-history baseline | COMPLETED | Three buildings/users/devices, six concurrent tasks, 24 ingestions and 36 page reads, no foreign observations, post-load revocation; retained 10,000-row benchmark. No fleet throughput claim. |
| 16. Broad-scope/full-snapshot profiling, total disk budget and durable offline delivery | DEFERRED OUTSIDE PHASE 1 | Explicit limits for a future measured capacity increment; do not infer hundreds of real buildings from query microbenchmarks. |
| 17. Full simulator, extra device families, AI intensive testing and visual redesign | DEFERRED OUTSIDE PHASE 1 | Not started. Independent Astra review precedes the separate simulator assignment. |
| 18. Preserve original/checkpoints and clean final handoff | COMPLETED | Original source/config/status hashes, backup integrity and frozen refs checked before work; final verification recorded in PHASE1_FINAL_REPORT.md. |

No FIXABLE NOW item remains intentionally open at closure. External and decision
blocks prohibit official Ring/physical/production approval; they do not invalidate
the tested, disposable software foundation.
