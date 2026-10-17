# Contact timestamp correction — independent release review, 2026-10-17

Prior official baseline: `961e437eec954bbb0347a8cfe75bd67a42a1c5ea`.
Original correction: `dd262acf41dfef8f5c8d446e743d3db431742f8d`, preserved on
`codex/contact-timestamp-containment`. Independent release branch:
`codex/timestamp-release`. Official destination: GitHub `main`.
Final release identity: tag `nodum-contact-timestamp-20261017`; resolve its commit
after fetching rather than assuming a documentation file can embed its own hash.

## Finding and review decision

NODUM-REL-001: medium availability defect in the authorized contact-publisher path.
A timestamp could parse successfully yet fall outside the supported date range
during UTC conversion. The resulting arithmetic exception escaped input validation
and triggered the collector's unexpected-failure stop path.

The correction translates only that conversion exception into ordinary validation
failure. The existing ingestion boundary rejects it without saving a valid event;
the subscriber can continue receiving valid observations. It does not change
authorization, topic rules, timestamp windows, payload schemas, deduplication,
storage transactions or fail-stop handling for genuine persistence faults.
The shared timestamp type also keeps affected HTTP models within normal validation.

Independent inspection found no source correction necessary beyond dd262ac.
Before/after reproduction executed the original normalization from the preserved
baseline and the corrected type: both invalid range cases escaped before and were
rejected as validation errors afterward. No original checkout was modified.

Three additional subscriber-level tests exercise both range cases followed by a
valid event, revoked-authority rejection and unchanged persisted row count, plus
a genuine storage error that still disconnects and records failure. Existing tests
cover wrong topic, retained messages, foreign binding, stale/future timestamps,
duplicates, conflicting identities, persistence and rollback. CI's SQLite batch
now explicitly includes the shared timestamp boundary tests.

## Lab evidence provenance

Read Building Lab `docs/PHASE3_5_DEEP_VALIDATION.md`, `docs/PHASE4_READINESS.md`,
`fixes/README.md` at `a1f3c3c5c432b437d0708ee5205545842ea687bf`. Located the clean
isolated Nodum correction at `C:/dev/nodum-contact-timestamp-fix` and verified all
seven evidence-file SHA-256 values in `phase3-5-confirmed-finding.json`.
Saved before-fix results show four failing cases; fixed live replay and broad
SQLite results are corroborating historical evidence, not this review's own counts.
No Lab code, fixture logs or credentials are imported into Nodum.

## Release acceptance

Final measured results are in `verification/timestamp-release-20261017.json`.

| Independently executed check | Result |
|---|---|
| Targeted SQLite timestamp/contact regression | 26 passed, zero failures; 2.67 s |
| Full backend | 1,095 passed, 4 SQLite-only skips, zero failures; 76.03 s |
| Full SQLite backend | 1,099 passed, zero skips/failures; 212.90 s |
| Frontend tests | 34 passed, zero failures |
| Frontend lint and TypeScript/build | PASS |
| Python correctness lint | PASS |
| External HTTPS/MQTT full-stop recovery | PASS, 14.61 s; three durable events, isolation/revocation/reconnect preserved |
| Backup/restore/preflight/startup | PASS; schema10 integrity/FKs, health200, anonymous401, docs404 |

The interrupted session's complete process output was recovered successfully; no
passing full suites were rerun. SQLite exercises all four memory-suite skips.
Hosted result is recorded after publication below.
Hosted CI must pass on the exact release commit before main is fast-forwarded.
Remote main, tag, tree identity and correction ancestry are independently checked
at delivery. No forced update or failed-check bypass is permitted.

## Preservation and remaining limits

Verified 411 original source hashes, three private configurations, original status,
backup integrity/foreign keys and security/foundation/review/demo refs unchanged.
The original fix branch is preserved; Building Lab remains clean at a1f3c3c.
No live deployment or visual simulator work forms part of this release.

This resolves malformed-input containment, not durable offline capture: clean-session
MQTT can lose downtime events; broker acknowledgement is not durable application
acceptance. Genuine storage failures still require monitoring and explicit recovery.
Official Ring Playground evidence remains unconfirmed; custom simulations remain
verified. Physical hardware, deployment commissioning and safety gates remain open.

Phase 4 may use official main at the new release tag as its Nodum baseline under a
separate assignment. Lab service authentication, task ownership, cancellation,
concurrency budgets and evidence distinctions remain separate Phase 4 requirements.
