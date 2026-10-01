# Backend deployment preparation

This prepares a single FastAPI/Uvicorn process behind a TLS-terminating reverse
proxy or hosting platform. Nothing is deployed by these commands unless you run
the container/startup commands yourself. `/health` remains `200 {"status":"healthy"}`.
Routes, seed data, repository/services and deterministic policies are unchanged.

**Public exposure boundary:** production building/agent APIs now require a manager
session, and writes require CSRF plus a trusted Origin. Development mode is still
an unauthenticated synthetic-data demo: never publish it with customer data.
Production /docs, /redoc and /openapi.json are disabled (offline schema generation
still works). Health, auth/login and signed Ring endpoints remain available.
This coarse gate is not tenant/resource RBAC or verified audit attribution.
Configure [sessions and exact frontend origins](authentication.md), retain
restricted ingress, and review [production blockers](production-readiness.md).
Ring token delivery still requires its Ring-confirmed adapter.

## Local development (PowerShell)

From the repository root, create `.env` from `.env.example` if you do not already
have one. Do not overwrite an existing secret file. Then:

```powershell
cd C:\dev\nodum\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.run --env-file ../.env
```

Defaults: `APP_ENV=development`, `HOST=127.0.0.1`, `PORT=8000`, one worker, no
reload. The optional dotenv file never overrides exported environment variables.
Nothing implicitly loads `.env` on import or startup. To use the Vite frontend,
set `CORS_ALLOWED_ORIGINS=http://localhost:5173` explicitly and restart.

For code reload during development only:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --env-file ../.env --host 127.0.0.1 --port 8000 --reload
```

Direct Uvicorn CLI invocation uses its own host/port/proxy flags; the application's
`HOST` and `PORT` are honored by `python -m app.run`. Startup validation and CORS
apply with either entry point. FastAPI import and OpenAPI generation perform no
database initialization, AWS credential lookup, or Ring calls.

## Production startup

Export configuration using the platform's environment/secrets facility. Example
for a local Windows production-mode check, without making the server public:

```powershell
cd C:\dev\nodum\backend
$env:APP_ENV = 'production'
$env:HOST = '127.0.0.1'
$env:PORT = '8000'
$env:DATABASE_URL = 'sqlite:///C:/dev/nodum-data/nodum.db'
$env:CORS_ALLOWED_ORIGINS = 'https://nodum.example.com'
$env:RING_REQUIRED = 'false'
.\.venv\Scripts\python.exe -m app.run
```

Use `HOST=0.0.0.0` inside a container/platform network. Terminate HTTPS at ingress;
the backend speaks HTTP on that private network. Configure the ingress to preserve
the webhook's raw body and `X-Signature`, set request/body limits, and avoid redirects
on the exact `/ring/webhooks` URL. Do not log linking nonce query strings or tokens.
Access logging is off by default in production. Configure ingress logs similarly.

`FORWARDED_ALLOW_IPS` accepts only the actual ingress IPs/CIDRs. Empty disables
forwarded-header trust. Wildcard trust is rejected. Keep the backend socket private
so direct clients cannot impersonate ingress. No HTTPS redirect middleware is
added, avoiding TLS-proxy loops and preserving health probes.

## Environment variables

All deployment-specific configuration comes from the process environment. The
complete copyable template is [`.env.example`](../.env.example); it contains no
real credentials. Policy constants and security limits remain in domain code.

| Variable | Default / production requirement |
| --- | --- |
| `APP_ENV` | `development`; set `production` for deployment |
| `HOST` | `127.0.0.1`; image default `0.0.0.0`; IPv4 or IPv6 address |
| `PORT` | `8000`; configurable 1–65535 |
| `DATABASE_URL` | Development `sqlite:///./nodum.db`; production requires an absolute file path on persistent storage |
| `CORS_ALLOWED_ORIGINS` | Empty, denies cross-origin browser access; comma-separated exact origins, no wildcard/path/trailing slash; HTTPS only in production |
| `CORS_ALLOW_CREDENTIALS` | `false`; enable only for an authenticated browser flow using explicit origins |
| `FORWARDED_ALLOW_IPS` | Empty; comma-separated trusted proxy IPs/CIDRs when behind TLS ingress |
| `LOG_LEVEL` | `info` |
| `ACCESS_LOG` | `true` in development, `false` in production; template explicitly uses `false` |
| `GRACEFUL_SHUTDOWN_SECONDS` | `30`; bounded graceful request completion on shutdown |
| `NODUM_AI_ENABLED` | Existing default `true`; set `false` when AI is unused |
| `AWS_REGION` | Existing default `eu-north-1`, with `AWS_DEFAULT_REGION` fallback |
| `BEDROCK_MODEL_ID` | Existing default `eu.amazon.nova-2-lite-v1:0` |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` | Optional credential-chain inputs; prefer a workload IAM role, never bake into the image |
| `AWS_PROFILE`, `AWS_SHARED_CREDENTIALS_FILE`, `AWS_CONFIG_FILE` | Optional SDK configuration; leave unset unless using mounted SDK configuration |
| `RING_REQUIRED` | `false`; opt-in fail-fast Ring configuration validation, not a route-enable switch |
| `RING_ENVIRONMENT` | Existing `staging` default; explicitly select `staging` or `production` when Ring is required |
| `RING_CLIENT_ID`, `RING_CLIENT_SECRET` | Required when `RING_REQUIRED=true` |
| `RING_SIGNING_KEY` | Required for Ring; legacy `RING_WEBHOOK_SECRET` fallback works when primary is absent or empty |
| `RING_ENCRYPTION_KEY` | Required for Ring; valid Fernet key, stable across restarts and backed up separately |
| `RING_API_BASE_URL` | `https://api.amazonvision.com`; explicitly set when Ring is required |
| `RING_OAUTH_TOKEN_URL` | `https://oauth.ring.com/oauth/token`; explicitly set when Ring is required |
| `RING_ACCOUNT_LINK_URL`, `RING_TOKEN_EXCHANGE_URL`, `RING_WEBHOOK_URL`, `RING_HOMEPAGE_URL` | Required HTTPS URLs when Ring is required; register appropriate URLs separately in the portal |

`RING_REQUIRED=true` validates all Ring variables before opening the database or
accepting traffic and reports missing variable names without printing secrets.
It works in either application environment, allowing production-mode Nodum to test
Ring's staging configuration. It does not contact Ring. `false` preserves existing
lazy Ring configuration: even invalid Ring credentials/URLs cannot block core startup;
Ring endpoints can still report their existing 503 errors. AI remains lazy too.

SQLite migrations/seeding run at startup as before. Missing production database
configuration, invalid schema, or unwritable storage stop startup with an actionable
message. See [persistence](persistence.md) for backups and migration details.

## Docker build and local run

Build from the repository root with **backend as the build context**:

```powershell
docker build -t nodum-backend:local ./backend
docker volume create nodum-data
docker run --rm --name nodum-backend -p 127.0.0.1:8000:8000 --mount source=nodum-data,target=/data -e NODUM_AI_ENABLED=false -e RING_REQUIRED=false nodum-backend:local
```

The image defaults to production mode, `HOST=0.0.0.0`, `PORT=8000`, and
`DATABASE_URL=sqlite:////data/nodum.db`. It runs as UID/GID 10001, one Uvicorn
worker with no reload, and uses an exec-form command so shutdown signals reach
Python directly. `/data` is owned by that user; a new Docker named volume inherits
its ownership. Existing volumes and bind mounts must be writable by UID 10001.
The database directory must permit creation of WAL/SHM files, not just writing
the database file. Keep one backend replica with a local persistent volume;
do not place SQLite WAL on a shared network filesystem.

Supply a deployment-specific environment file (not the unmodified local template):

```powershell
docker run --rm --name nodum-backend -p 127.0.0.1:8000:8000 --mount source=nodum-data,target=/data --env-file .env.production -e APP_ENV=production -e HOST=0.0.0.0 -e DATABASE_URL=sqlite:////data/nodum.db nodum-backend:local
```

The local template uses loopback HOST and a relative database URL; the overrides
above prevent those local values from breaking container startup. To change the
port, set `-e PORT=8080` and publish `-p 127.0.0.1:8080:8080`. The Docker health
probe follows HOST/PORT and checks the unchanged `/health` JSON. `EXPOSE 8000`
is image metadata, not a fixed runtime binding. A probe passes after startup;
`/health` remains a lightweight liveness endpoint, not a live Ring/AWS check.

The build copies only requirements and application source. `.dockerignore`
excludes virtualenvs, local databases, secret files, caches, tests, and unrelated
repository files. Dependencies are pinned in the existing requirements file.
The Python 3.13 slim base uses a maintained tag; pin a reviewed image digest in
your release process if immutable image reproducibility is required.
No secrets are build arguments or image environment defaults.

## Before live HTTPS testing

- Provide a domain, TLS certificate/termination, ingress restrictions and rate limits.
- Mount persistent writable storage and arrange SQLite/key backups.
- Supply runtime secrets and AWS IAM permissions only for enabled capabilities.
- Configure the persisted Ring account-link UI and provide the verified inbound token adapter;
  startup validation alone does not remove their fail-closed gates.
- Register URLs in Ring's portal, connect the private-app account/devices, and run
  real signature, discovery, linking and restart tests after deployment approval.

The container approach follows the official [FastAPI Docker guidance](https://fastapi.tiangolo.com/deployment/docker/).
