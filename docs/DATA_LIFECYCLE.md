# Data lifecycle boundary

Review supplement, 2026-10-16: `app/services/retention.py` now supplies
`plan_contact_retention(authorization, scope_id=..., before=..., now=...,
max_scan=500, held_ids=())`. This is a trusted service-level engineering preview,
not a public API, scheduler, archive or deletion command. It requires fresh
hardware.configure and activity.read for the explicit scope, uses authorized
pages, scans at most 1,000 candidate positions, excludes other journal classes,
honors supplied holds, and reports truncation. Counts are only for the scanned
visible sample, not a fleet estimate. The cutoff uses server receipt time. Holds
are hypothetical inputs, not an authoritative legal-hold registry.

`test_retention_plan.py` verifies boundary cutoff, bounded scans, protected records,
holds, foreign scope, revocation and unchanged history/replay after planning.
No apply path exists; `apply_enabled` is always false.

| Owner decision | Proposed configuration to approve | Tradeoff |
|---|---|---|
| Lab only (recommended now) | Existing per-device max_observations; approved device count and stop-at-capacity response | No deletion; ingestion eventually stops |
| Sustained telemetry | Per-class receipt-time horizon, fleet byte ceiling, archive URI/key custodian, replay horizon and protected holds | Requires archive verification and separately implemented bounded apply |
| Visitor/account information | Purpose, closure trigger, approved horizon, exceptions and responsible operator | Separate from telemetry; dependencies and privacy review required |
| Security audit and video metadata | Explicit protected class/hold policy, access roles, approved horizon | Do not inherit observation cleanup; no media capture pipeline is implied |
| Backups | Encryption/access owner, schedule, horizon, recovery objectives and authority reconciliation | Old snapshots can restore revoked sessions/grants |

No duration is preselected or claimed legally compliant. An eventual apply must
consume an approved versioned policy, recheck current scope/holds, verify a scoped
archive and preserve replay tombstones, then atomically delete a bounded batch with
its bindings and append a protected audit result. Restart resumes by durable batch
ID. Concurrent new records and policy changes must force revalidation. These are
acceptance requirements, not implemented deletion capabilities.

Phase 1 does not delete or archive application data automatically. No owner-approved
retention period, archive destination or legal-hold policy has been supplied.

| Data class | Current control | Decision before sustained operation |
|---|---|---|
| MQTT contact observations | Private collector max_observations 1..1,000,000, default 100,000 per device; atomic SQLite count/insertion, preserved duplicates, reject new IDs at capacity | Expected event rate/device count, fleet envelope, source replay horizon, operator response at capacity |
| Other operational and Ring histories | Persisted records; operational journal has indexed authorized keyset paging; other projections may scan full collections | Independent storage/retention budgets; do not describe paged reads as bounded disk usage |
| Security and configuration/actuator audit | Retained; no deletion tool or ordinary-observation cleanup | Incident preservation, tamper evidence, access review and any legal hold; do not reuse contact cutoffs |
| Identity, affiliation, credentials/session records | Existing active/expired/revoked behavior and anonymous issuance limits | Privacy purpose, account closure obligations and separately approved disposal rules |
| Backups | Consistent verified SQLite snapshot/new-path restore; includes sensitive data and potentially old sessions/grants | Protected/encrypted storage, access ownership, backup horizon and reconciliation of authority after restore |

Event receipt `at` is server time; contact `observed_at` is explicitly aware UTC
within the accepted freshness window. Never erase based solely on an untrusted
source timestamp. Scope/resource bindings determine authority; a payload tenant ID
or age filter cannot substitute for authorization. Archives would also contain
private building activity, not merely performance logs.

Owner options, with no invented duration:

1. Keep non-destructive per-device limits for a bounded lab. Simplest recovery and
   audit semantics; reaching capacity interrupts new ingestion and total fleet/other
   histories still need operator monitoring. This is the current foundation policy.
2. Add an approved fleet ceiling rejecting new ingestion before a storage envelope.
   Bounds capacity without deletion but requires the operator to accept availability
   tradeoffs and define which event classes must remain writable.
3. Encrypted scoped archive followed by separately approved bounded pruning. More
   operational complexity; requires export completeness, checksums, restore testing,
   incident holds, replay/deduplication preservation and an interruption-safe process.

Recommend option 1 for the isolated lab, then select 2/3 from measured rates and
business/privacy requirements before sustained deployment. A disk-full experiment
or guessed “compliant” duration would not resolve these decisions.

Acceptance already executable: test_contact_budget.py covers capacity, duplicates,
concurrency, exclusion of other sources/devices and durable restart/index behavior;
test_maintenance.py covers corruption, destination overwrite/races, bounded backup
and recovery. No test claims an archive/prune feature exists. Any future destructive
apply must first pass scoped dry-run, export/restore, interruption, binding integrity,
legal-hold and duplicate-after-retention tests (ASTRA-STORAGE-003).
