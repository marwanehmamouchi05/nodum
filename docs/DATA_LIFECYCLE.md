# Data lifecycle boundary

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
