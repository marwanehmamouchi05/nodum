# Reproducible local reverse-proxy and browser acceptance

This is disposable staging verification, not production commissioning. No listener
is public and no OS certificate trust store is changed. The real Caddy process
terminates HTTPS, serves a freshly built frontend and proxies to private loopback
HTTP Uvicorn. The app runs production configuration with a fresh synthetic SQLite
database. API, proxy, certificate, build and database are removed/stopped on exit.

## Prerequisites and invocation

Follow DEVELOPER_ONBOARDING.md for Python/core/optional MQTT dependencies and
`npm ci`. Obtain the official Caddy binary from
[Caddy releases](https://github.com/caddyserver/caddy/releases/tag/v2.11.7), verify
the platform archive against its published checksums, and keep it in ignored local
artifacts. This run used Caddy 2.11.7 Windows amd64, archive SHA-512:

```text
c308154504e53755958ffc62d8a2657ab17eefd6dd25c45dbb2c3d93d29519971f77ca652f7d0f2bcb7f980b9ba3822478865e29969d0272d7613550a43152b1
```

The published checksums use SHA-512, not SHA-256. This verifies the release archive
against the downloaded release checksum; no independent publisher-signature check
is claimed. No binary or temporary key is committed.

```powershell
backend/.venv/Scripts/python.exe backend/scripts/proxy_staging.py --caddy artifacts/caddy-2.11.7/caddy.exe --ready-file artifacts/proxy-ready.json --serve-seconds 600
```

The printed `base` is a random loopback HTTPS origin. The command is foreground;
use a second terminal/browser for checks. It validates frontend 200, SPA fallback
200, unauthorized Manager 401, absent API/docs 404 and the login script 200, and
proves `FORWARDED_ALLOW_IPS=*` refuses startup. To stop early from the second
terminal, create `artifacts/proxy-ready.stop`. Normal exit also stops both processes
and deletes temporary storage; the redacted ready report records fixture_stopped.
Use a fresh ready filename or remove a stale stop marker before another run.

## Browser procedure

Open the printed origin in an isolated Playwright context with
`ignoreHTTPSErrors: true` for this one temporary self-signed fixture. This is not a
production trust setting. Normal certificate validation rejects this certificate;
the Python wire client instead explicitly trusts just the generated certificate.

Navigate that page to the fixture origin, then run the async Playwright callback
in `frontend/tests/proxy.browser.js`. It uses only synthetic accounts supplied by
`demo_product.seed_demo`. A Playwright runner can load/evaluate that callback and
invoke it with the page; the existing Codex Playwright tool was used for this run.
No new frontend runtime dependency is required.

It signs in through the real login UI/redirect, creates a Resident visitor/pass,
reloads the Visitors screen, checks cookies, rejects missing CSRF/wrong Origin and
invalid/absent API requests, opens a deep SPA path, refreshes Manager Maintenance
and Business Visitors, signs out and verifies 401. A Resident-only login with a
forged Admin hash stays in Resident and receives 403 from Admin setup. The Admin
account listing is an authorized filtered collection (200 with no visible rows can
be correct); it is not used as a guessed-resource 403 oracle.

Actual result: `docs/verification/proxy-browser-20261015.json`. The fresh backend
environment and freshly installed frontend were also used for final repetition.

## Routing and trust requirements

The generated config follows the official
[Caddy SPA/API pattern](https://caddyserver.com/docs/caddyfile/patterns) and
[handle_path](https://caddyserver.com/docs/caddyfile/directives/handle_path).
`/api/*` loses the prefix before the backend; `/auth/*` also proxies unchanged
because the server-rendered login uses absolute same-origin URLs. Preserve this
namespace when reproducing this topology. Ring's public callback/webhook URLs
would need explicit authorized routing before a real provider run; none is exposed
or tested here. Other non-API URLs fall back to the SPA. Frontend API base is public
build-time configuration; provider secrets never enter the frontend build.

Caddy binds only 127.0.0.1, uses provided temporary certificate/key, disables its
admin endpoint, config persistence and automatic HTTPS issuance. Uvicorn trusts
only the selected loopback proxy IP. Caddy's default forwarding logic is used;
arbitrary client forwarding headers are not configured as trusted proxy identity.
The private backend port is reachable to local processes, so a real deployment
must enforce the selected network/process boundary. Wildcard trust is rejected;
no general proxy-smuggling certification or all-hop trust test is claimed.

## Other transport/recovery evidence and exclusions

- No application WebSocket client or endpoint was found in backend/app or
  frontend/src; WebSocket acceptance is not applicable to the current app.
- Actual independent HTTPS/MQTT drill and separate TLS/auth/ACL broker drill pass.
  The external drill now stops API, broker and collector, backs up/restores into a
  new DB path and checks stored events/isolation/revocation again through HTTPS.
  Restore is logically verified; SQLite file hashes need not remain identical.
- Existing initialization, corrupt/unsupported-schema rejection, atomic snapshot,
  non-overwrite/timeout and restore/preflight regressions remain executable.
- Not tested: public DNS/certificate renewal, real target OS/service manager,
  remote firewall/proxy chain, production broker, encrypted backup scheduling,
  monitoring/alerts, real Ring callbacks, hardware or physical safety. Hosted CI
  has not run. Select those environments before operational approval.
