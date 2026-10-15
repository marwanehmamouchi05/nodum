# ADR 0002 — non-destructive contact telemetry capacity

Accepted 2026-10-15. Existing sensor history had no bound. Unreviewed deletion could
erase audit evidence and replay protection, so automatic retention is not introduced.

The server-owned collector configuration now sets a persistent per-device contact
observation budget (default 100,000; valid 1–1,000,000). Before inserting a new source
ID the ingestor checks an indexed count in the same SQLite write transaction as
the event and binding. Migration 10 adds the count index; no data is rewritten.
Duplicates/conflicts are checked first. Concurrency and restart cannot reset or
overrun the configured count. Only read-only MQTT contact rows count toward it.

At capacity a new ID returns a domain 429 rejection; transport exposes
`capacity_reached`, and the bounded collector CLI returns nonzero. Earlier audit
rows and duplicate identity remain intact. The count is durable; the configured
policy is private server configuration and must be consistent across collectors.
An authorized reconfiguration can raise it; publishers cannot change it in payloads.

This bounds contact growth per configured device under that policy, not all
application history or total disk use across an expanding inventory. Operator
capacity monitoring, a fleet budget and reviewed archiving remain required. A
future retention decision must specify legal/operational needs, restore behavior,
deduplication horizon and audit evidence before a destructive maintenance path.

Tests: concurrent capacity reservation, duplicate at capacity, unrelated record
exclusion, exposed capacity status, SQLite restart persistence and indexed plan.
