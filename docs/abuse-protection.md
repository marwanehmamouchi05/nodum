# Demo abuse and AI consumption controls

Enabled on the AWS judge server with `NODUM_ABUSE_PROTECTION=true`.
Other installations opt in explicitly. This is application hardening for one
Uvicorn worker, not an edge firewall or a guarantee against distributed attacks.

## AI allowances

Reservations happen before each provider call. A separate persistent SQLite
ledger, `nodum-ai-usage.db` beside the product database, stores counters only,
not prompts or credentials. Restarting the app does not reset allowances.

| Control | Limit |
| --- | --- |
| Concurrent AI questions | 1, with immediate busy response rather than a queue |
| Questions per account | 5 per UTC minute, 20 per UTC day |
| Questions across the installation | 60 per UTC day |
| Actual model-call attempts across the installation | 40 per UTC day, 200 per UTC calendar month |
| Reserved serialized input across model calls | 1 MB per UTC day, 4 MB per UTC calendar month |
| Each serialized provider context | 65,536 bytes including a 4,096-byte accounting margin |
| Output | At most 1,000 tokens per call; existing five-round/tool limits still apply |

Only the configured `eu.amazon.nova-2-lite-v1:0` model is admitted under this
allowance. Automatic SDK retries are disabled while protection is enabled.
Failed or uncertain calls keep their reservation because they may already be
billable. Accounting failure stops AI calls. Ordinary forms, the local Guide
and explicit confirmation flows remain available. Limit responses explain the
fallback. This is a finite usage allowance, not an exact dollar-based AWS cap;
provider prices, tokenization and other AWS resources must still be monitored.

## Web admission and resource limits

Before buffering bodies, the app admits at most 120 requests per client IP per
minute, 600 requests globally per minute, and 20 concurrent requests. Rejections
return 429 with Retry-After. Client addresses rely on the private loopback proxy
boundary: only Caddy can reach the app, and untrusted forwarded headers must not
be accepted from the public internet. Fixed windows can permit a boundary burst.
These small in-memory admission counters reset on restart; AI counters do not.

The existing raw-body validation retains signed bytes, rejects oversized or
ambiguous framing, and bounds body-read time. The AWS Caddy proxy additionally
limits bodies to 1 MB, headers to 16 KiB, header/body reads to ten seconds,
response writes to 120 seconds and idle connections to thirty seconds.
The app container is capped at 512 MiB, 0.75 CPU and 128 processes; the proxy at
128 MiB, 0.25 CPU and 128 processes. Container logs are rotated and bounded.

## Spending and recovery

AWS remains on its credit-funded Free account plan. The existing $20 monthly
budget alerts at $10, $16 and $20 now exclude credit/refund offsets so resource
usage is visible before credits run out. Alerts are delayed and do not stop AWS
services. No paid plan, WAF subscription or Shield Advanced was enabled.

SQLite backups include the usage ledger. Keep its latest copy during recovery;
restoring an old ledger can restore old counters. Preserve the private product
database and signing/encryption configuration. Revisit quotas before changing
the model or running multiple workers/servers.

Basic AWS Shield network protection remains available, but a single public server
can still suffer availability loss or consume network credits during an attack.
These controls do not replace an upstream WAF/CDN or an AWS-wide spending cap.

## PHP advisory check — October 22, 2026

Nodum uses Python/FastAPI, a compiled React/TypeScript frontend and the official
Caddy proxy. No PHP application files, Composer dependency, PHP-serving host
process or PHP executable in either running container was found. The two
PHP-core issues CVE-2026-109618 and CVE-2026-109619 therefore have no PHP runtime
to exploit in this deployment. This is a check of those issues, not a claim that
the whole application has no vulnerabilities. See the
[official PHP advisory](https://www.php.net/archive/2026.php).
