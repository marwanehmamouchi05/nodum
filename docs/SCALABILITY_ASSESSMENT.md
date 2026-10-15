# Measured scalability assessment

2026-10-15. Raw reproducible result:
[activity-20261015.json](benchmarks/activity-20261015.json).
Command: `python backend/scripts/benchmark_activity.py --output artifacts/activity.json`.
Defaults: 1/10/100 building scopes, 100 journal rows each, three sequential samples
per query, one authorized building, at most 10,000 rows. CLI caps 200 events/scope
and five samples. Disposable SQLite, no network/hardware load or existing database.

Windows 11, Python 3.13.9, SQLite 3.51, 16 logical CPUs, AMD64 processor details in
the report. Normal developer machine; background targeted tests were also active,
so this is not a controlled isolated performance host. Tracemalloc overhead is
included in both query paths. With three samples p95 is effectively the maximum;
these distributions are descriptive, not statistically robust capacity estimates.

| Building scopes / total rows | Legacy full-history p50 | New indexed page p50 / p95 | Legacy / new traced Python peak |
|---|---:|---:|---:|
| 1 / 100 | 40.179 ms | 35.608 / 36.088 ms | 298,043 / 249,610 bytes |
| 10 / 1,000 | 207.725 ms | 39.615 / 54.746 ms | 1,277,372 / 239,968 bytes |
| 100 / 10,000 | 3,445.015 ms | 91.131 / 102.134 ms | 11,330,797 / 253,770 bytes |

At 100 scopes, new mean CPU/query was 88.542 ms versus 3,375 ms, approximately
10.89 sequential page queries/second versus 0.29 full-history queries/second.
No benchmark assertion failed. DB + sidecars was 8,396,800 bytes. Synthetic fixture
insertion was 4,261.64 rows/sec inside a single setup transaction; this is NOT MQTT
throughput or a durability/latency SLA. Report stores the other profiles' CPU,
throughput, seed duration, size and error counts.

## Implemented response to the bottleneck

The old operational-journal path loaded every tenant's history and repeatedly
authorized records before truncating. Migration 9 and `page_operation_activity`
query indexed top-N per authorized scope, join matching resource bindings before
LIMIT and merge bounded candidates. The current Manager uses it for journal rows;
the additive paged API supports independent observers. Query-plan and tied-cursor
regressions preserve scope boundaries and ordering. Migration 10 adds an indexed
per-device contact capacity check; it does not erase history or reset on restart.

## Practical limits

These fixtures model scope partitions, not 100 fully populated building dashboards.
Scope inventory/role resolution still grows with configured inventory; broad
multi-building operators were not benchmarked. Current transactions acquire a
SQLite write reservation for coherent reads; concurrent readers/ingestors need a
separate contention study. No concurrent HTTP workload, reconnect storm, process
RSS, sustained disk pressure, production-host latency or network saturation result
is claimed. Traced Python allocations are not total process memory.

Other projections/histories still scan collections. Per-device contact capacity is
a guardrail, not fleet retention/global disk quotas; at capacity telemetry is
rejected and requires operator action. No automated audit deletion policy exists.
Offline clean-session MQTT is lossy. Prior 250-event loopback burst is historical
transport evidence, not a current fleet benchmark.

Next bounded work: representative multi-building snapshot/HTTP concurrency with
explicit duration/memory/connection limits, read-transaction contention, indexed
scope/grant lookup if measured dominant, then an approved archive/retention policy.
Do not introduce distributed infrastructure from this one query benchmark.
