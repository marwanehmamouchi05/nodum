# Developer onboarding

Start in a separate checkout/worktree. Never run tests, bootstrap, migrations or
hardware experiments against an existing installation/database. Preserve uncommitted
work and use `codex/` branches. No automatic merge or deployment is part of this guide.

## Stack and layout

Verified local stack: Windows 11, Python 3.13.9, SQLite 3.51, Node 24.19, React 19,
TypeScript 6, Vite 8, FastAPI/Pydantic and SQLite. Exact backend pins and frontend
lockfile are authoritative. [Architecture map](ARCHITECTURE_OVERVIEW.md) explains
module ownership. `app/services` holds policy/workflows, `app/api` thin routes,
`app/integrations` adapters, `app/models` contracts and repositories all persistence.
`tools/contract_client` is deliberately independent of that Python application.

## Fresh development setup (PowerShell, repository root)

Choose paths that do not already contain an environment. Do not copy production
`.env` files or credentials. These commands install core + optional MQTT + development
lint tools, keeping the test broker separate because its dependencies differ. Its top-level version is
pinned; a full transitive broker lock and cross-OS hosted install remain unverified.

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt -r backend/requirements-mqtt.txt -r backend/requirements-dev.txt
backend/.venv/Scripts/python.exe -m pip check
python -m venv .broker
.broker/Scripts/python.exe -m pip install -r backend/requirements-mqtt-broker-test.txt
.broker/Scripts/python.exe -m pip check
cd frontend
npm ci --no-audit --no-fund
cd ..
```

On Linux use `bin/python` in each environment. The workflow uses Ubuntu; hosted
execution has not yet been observed. Local fresh app installation and frontend
`npm ci` were verified on Windows; this is not a clean-OS installation certificate.

## Start a safe product demo

First terminal, from root:

```powershell
backend/.venv/Scripts/python.exe backend/demo_product.py --start
```

This intentionally creates a temporary synthetic database, prints synthetic local
accounts, binds to loopback :8770 and deletes its database when stopped. Never
deploy the launcher. Do not reuse these credentials outside the disposable demo.

Second terminal:

```powershell
cd frontend
$env:VITE_API_BASE_URL='http://127.0.0.1:8770'
$env:VITE_API_USE_CREDENTIALS='true'
npm run dev -- --host 127.0.0.1 --port 5178 --strictPort
```

Open `http://127.0.0.1:5178`. The frontend contains only public build configuration;
never place AWS/Ring secrets there. Source styles, fonts and existing workspaces
are preserved. This mission made no product UI redesign.

For an empty persistent development install, follow the exact new-database,
private-password provisioning sequence in [product release](product-release.md#local-startup-and-first-install).
`provision_admin.py` rejects existing/nonempty/audited targets and prompts privately.
Scoped production startup requires an explicit persistent SQLite path and HTTPS
origin. The default audited database is protected; do not bypass its refusal.
Migrations append through `SQLiteDatabase.initialize`; application startup upgrades
the explicitly chosen database. Back up first with [recovery tools](backup-recovery.md).
Preflight is read-only and must never create/migrate storage.

## Quality and protocol checks

```powershell
backend/.venv/Scripts/python.exe -m ruff check backend tools/contract_client
backend/.venv/Scripts/python.exe -m pytest -q
backend/.venv/Scripts/python.exe -m pytest -q --repository-backend sqlite backend/tests/test_activity_pages.py backend/tests/test_contact_budget.py backend/tests/test_mqtt_sensor.py backend/tests/test_request_limits.py backend/tests/test_session_budget.py backend/tests/test_security_tenants.py backend/tests/test_maintenance.py
backend/.venv/Scripts/python.exe backend/scripts/external_contract_drill.py --broker-python .broker/Scripts/python.exe
backend/.venv/Scripts/python.exe backend/scripts/pilot_drill.py
```

`pytest.ini` makes root-level tests resolve the application package; running from
`backend` also remains supported. For explicit temporary directories choose a NEW
path each run; pytest can remove a supplied `--basetemp` directory. Default tests
use memory fixtures; SQLite-only cases must be run separately as above. Memory
transactions do not prove rollback. The external drill uses actual HTTPS and MQTT
but never physical equipment or a real provider account.

From `frontend`, run `npm test`, `npm run lint`, `npm run typecheck` and `npm run build`.
Build includes TypeScript checking. CI runs correctness-oriented Python lint (E9,
F63, F7, F82), regression tests, optional broker proof, recovery and frontend checks.
Scoped formatting is enforced for the new integration/paging files; format changed
files with Ruff before review. Full Python style/type coverage is not established; expand it incrementally rather
than hiding legacy findings or reformatting the entire repository.

## Making a change or extending an adapter

Begin with the relevant service/models/repository and nearby tests. Keep authority
checks and mutations in the same transaction. Append migrations and verify upgrade,
restart, integrity and recovery. Version changed external contracts and preserve
legacy routes unless an explicit migration is reviewed. Follow the [adapter
procedure](UNIVERSAL_HARDWARE_ARCHITECTURE.md#extension-procedure); select real protocol
semantics before adding device families. Only server-owned registry wiring may add
an adapter. Never add public arbitrary URLs/plugins or live I/O to pure simulators.

Representative extension exercise in this checkpoint: external source-event
correlation + paged observation API. Added one domain service/repository operation
and additive indexes; existing Manager projection consumes it. No Resident,
Business, Admin or frontend business logic changed. The standalone client can now
provision and observe through the documented interfaces. Existing wayfinding/access
simulator and MQTT tests demonstrate separate categories; no second physical adapter
was fabricated. See `test_building_integrations.py` for policy-before-dispatch tests.

Before a PR: run relevant checks, document limits and add an ADR for substantive
contract/persistence decisions. Changes remain local until owner-authorized promotion.

## Troubleshooting

- Import error for `app`: use the root pytest configuration/new checkout, or run
  from `backend`; avoid setting global PYTHONPATH to another worktree.
- Startup rejects DB/config: select a NEW explicit SQLite URL and valid exact origin;
  errors intentionally omit secret values. Do not point at the audited runtime DB.
- Frontend 401/403: sign in, verify exact origins/credential setting and fresh roles;
  a workspace selector is not an authority grant. Cookies can span localhost ports.
- Broker dependency conflict: use its own environment; never change app pins to
  satisfy the disposable broker. Paho remains optional for core API startup.
- Collector `capacity_reached`: preserve records, investigate rate/expected inventory
  and the private configured budget; no automatic audit deletion is available.
- External drill failure: keep the redacted verdict and identify the failed layer;
  never bypass TLS, CSRF, permission checks or mutate the database from the client.
