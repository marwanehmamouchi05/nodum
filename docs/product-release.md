# Nodum product architecture and release guide

Current scoped product: Phases A–F, October 7, 2026. Earlier reports are historical checkpoints. Demo readiness does not imply physical commissioning or deployment approval.

## Roles and hierarchy

Owner recovery/Admin configuration is separate from private operations. Manager is delegated, not an inherited Admin. Resident data is personal. Business Admin is bounded to its active business; Staff receives a personal subset. Configuration privileges do not grant private camera/event visibility.

Admin navigation is Setup/Building/Hardware/Integrations/Accounts/Roles & Permissions/Policies/System & Audit. Manager has Overview/People/Visitors/Access/Maintenance/Security/Activity/Announcements. Resident has Home/Visitors/Maintenance/Access/Notices. Business has Home/Visitors/Staff/Maintenance/Access/Notices and permitted My Business; Staff has no team management by default. Actual permissions determine actions/pages.

The shared selector changes presentation only, never identity/grants/scope. It appears for multiple workspace choices and unmounts private page state on switching. It distinguishes workspace types, not multiple businesses/units. Multiple active business contexts still fail closed pending future context selection.

Organization → Building → Floor → Area → Unit/Business/Room → Device. Ownership is explicit; legacy ownership is never inferred. Reference levels: Underground, Ground Floor, Floor 1, Floor 2, Floor 3, Roof. Businesses X/Y share Floor 2 but retain isolation. Product spaces and physical access zones remain distinct; no implicit bridge is added. Operational storage is reused. Migrations remain 1–8.

## Security boundaries and session freshness

Session-derived identity → action → bound resource → active scope. Unbound resources default deny. Role labels grant nothing. Suspension, revocation, dates and permission ceilings are checked live. Tenant confinement protects generic reads, AI and workspace endpoints. Lists/details/mutations enforce matching ownership. Resident records and Staff visits/requests/access/activity are personal. Business Admin delegates its current authority intersected with the Staff ceiling in the same business. Revoking membership never globally suspends unrelated roles. Tenant projections exclude private operator notes.

Private/session responses use no-store. Sessions refresh on focus, authorization-denied responses and every 30 seconds. A 401 immediately clears private content. Grant/account changes remount workspaces; a server-derived membership marker also invalidates after affiliation edits, expiry or revocation. The marker grants no authority. Backend denial is immediate; idle display invalidation waits for the next session check, normally within 30 seconds, rather than push. Session-service failure removes the scoped workspace and offers recovery.

CSRF, CORS, signed cookies, expiry, throttling and logout remain enforced. Provider-signed ingestion retains its signature boundary. Camera viewing still needs permission, scope, policy and provider support. No unsupported live video is added.

## Ring, Activity and AI

Ring envelope → signature validation → normalization/deduplication → persisted inbox → scoped projection → operator review. Six synthetic scenarios use this signed receive pipeline. Shared entrance signals reach the Manager; tenant display requires explicit private source/resource association. Expected visits are not identity/destination evidence. Ring never automatically marks a visit arrived or unlocks a door.

The disposable demo associates simulator sources with configured common/service areas, never visitor identity or physical grants. Manager Activity formats arrival/motion/person/package signals and uses configured location only with matching source/account and hardware-read authority. Otherwise location remains unverified. Who/what/where/when/result remain projections; no event-store rewrite occurs. Legacy simulated actuators do not imply physical execution.

AI: user → authenticated filtered context → optional Bedrock → typed proposal → confirmation → fresh backend authorization/policy → execution. Ownership, scope, expiry and at-most-once consumption remain enforced. No unrelated tenant retrieval, autonomous building control or AI staff provisioning. Forms and Guide work during provider failure. The demo launcher deliberately uses unavailable-provider/local Guide fallback with no AWS calls. Automated typed-action tests use synthetic provider responses; live inference is not certified.

## Hardware reality

Cloud: Ring adapter, signed ingestion and linking preparation exist; live linking/delivery still need verification. Simulation: labeled software signals, not physical readiness. Configured devices remain Unverified absent supported telemetry. Edge: future local gateway for supported local-network cameras, sensors, access controllers and building systems. **Not installed**; no runtime/discovery/protocol support is claimed.

## Local startup and first install

Use the existing Python virtual environment/pinned requirements and Node dependencies (`npm ci`). Follow README for `demo_product.py --start`: explicit opt-in, temporary SQLite database, ephemeral Ring keys, localhost:8770, frontend :5178. Synthetic accounts/password are intentionally printed. Ctrl+C discards the DB. It overrides DATABASE_URL and ignores inherited bootstrap credentials. Never deploy this launcher. Close prior localhost QA tabs or use a clean browser profile: cookies span ports. Throttling remains active; restart before clean rehearsals.

For an empty scoped installation, explicitly select a NEW non-runtime database:

```powershell
cd backend
$env:NODUM_AUTHORIZATION_MODE='scoped'
$env:DATABASE_URL='sqlite:///./product-empty.db'
$env:AUTH_PUBLIC_ORIGIN='http://127.0.0.1:8000'
$env:AUTH_TRUSTED_ORIGINS='http://127.0.0.1:5173'
$env:CORS_ALLOWED_ORIGINS='http://127.0.0.1:5173'
$env:CORS_ALLOW_CREDENTIALS='true'
.venv/Scripts/python.exe provision_admin.py --name 'Building Admin' --username 'building-admin'
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Provisioning privately prompts for a password and refuses audited/default or nonempty targets. Scoped startup seeds no demo records. Start frontend with VITE_API_BASE_URL=http://127.0.0.1:8000 and VITE_API_USE_CREDENTIALS=true → sign in → empty Admin → Start setup. Load synthetic demo building is a separate explicit Admin action restricted to demo organizations; it creates no persona accounts/access grants. The disposable launcher is the full-persona presentation path. Production needs existing HTTPS/auth/provider configuration and separate verification. Never use audited runtime data for tests.

## Validation

Backend, with NEW basetemp paths each run:

```powershell
.venv/Scripts/python.exe -m pytest -q --repository-backend memory --basetemp ../.qa-release-memory-new
.venv/Scripts/python.exe -m pytest -q --repository-backend sqlite --basetemp ../.qa-release-sqlite-new
```

Frontend: npm test/typecheck/lint/build and npm audit. Backend: `.venv/Scripts/python.exe -m pip check`. Root: `backend/.venv/Scripts/python.exe backend/scripts/release_checks.py --dependencies` scans changed/untracked text without printing matches and queries OSV for public pinned PyPI packages. Requirements encoding is handled; incomplete pins/responses fail. Gitleaks is recommended where installed; this narrower pattern scan cannot certify every possible secret.

`frontend/tests/product.browser.js` runs against :8770/:5178 in an isolated Playwright context: five roles plus Owner recovery, 105 page/width combinations, skip links/focus/keyboard/44px buttons, real visitor → signed Ring → manual arrival → Activity, same-account switching, actual affiliation revocation/restoration, 401/logout clearing, Bedrock fallback and backend error/recovery. Previous workflow scripts remain available. Screenshots: docs/qa/f-*.png.

Release tests cover migration 8 clean install, upgrade from 7, restart/idempotence, foreign keys and integrity. Earlier auth/provider/privacy/action tests remain in both full suites. Exact results are in the Phase F report.

## Limitations

No verified physical door/elevator bridge, complete provider import, live streaming, Edge runtime, facial recognition, billing/payments, receptionist product, hotel workflows, native app, broad vendor catalogue, production video infrastructure, complex lease/CAD, email/SMS/push or full password-reset platform. Staff uses initial credentials, not delivered invitations. Photos and multiple-business selection remain future work. No speculative revenue figures appear. Future appointments can call existing visitor services with authenticated context, never bypass policy. Live Ring certification, AWS availability and physical deployment remain unverified.
