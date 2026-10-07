# Phase E1 — Resident experience

Status: READY FOR REVIEW. Implemented on `product-platform`, without commit,
merge, push or deployment. Main and HEAD remain `71927dd60294b7570756d906d7b339d543956c41`.
Phase A–D uncommitted work is preserved. Business workspace/E2 is not started.

## Changed files for E1

New backend files:
- `backend/app/api/resident.py`
- `backend/app/models/resident.py`
- `backend/app/services/resident.py`
- `backend/app/services/resident_boundary.py`
- `backend/tests/test_resident.py`
- `backend/tests/resident_qa_server.py`

Existing A–D files extended:
- `backend/app/main.py`: Resident router.
- `backend/app/services/authorization.py`: additional personal ownership confinement.
- `backend/app/api/manager.py`: configured Resident-only accounts use their personal portal.
- `backend/app/models/manager.py`: explicitly public maintenance reply.
- `backend/app/services/manager.py`: public reply history and cancelled visits.
- `backend/app/services/agent_tools.py`: scoped Resident context and typed confirmed actions.
- `backend/app/services/orchestrator.py`: Resident context/clarification/confirmation instructions.
- `frontend/src/App.tsx`: dedicated Resident role routing; Admin/Manager precedence retained.
- `frontend/src/manager/ManagerWorkspace.tsx`: distinguish private note/public Resident reply; cancelled visit filter.

New frontend files:
- `frontend/src/resident/ResidentWorkspace.tsx`
- `frontend/src/resident/ResidentForm.tsx`
- `frontend/src/resident/ResidentHelp.tsx`
- `frontend/src/resident/api.ts`
- `frontend/src/resident/model.ts`
- `frontend/src/resident/resident.css`
- `frontend/tests/resident.test.mjs`
- `frontend/tests/resident.browser.js`

Documentation: this report and 12 screenshots under `docs/qa/resident-*.png`.
These are the E1 changes; the broader worktree also contains approved A–D files.

## Storage and authorization

No migration 9 is required. Migrations 1–8 are unchanged. Existing migration 8
operational JSON records support visitor cancellation, logical visit authorization
and public maintenance replies. No duplicate Resident storage is introduced.

The portal requires an active authenticated account, a Resident assignment with
explicit application permissions, and an active date-bounded unit affiliation.
Destination, reporter and host come from the authenticated identity and its active
affiliation. Payloads reject unexpected identity/location/authority fields.

Visitors and maintenance require personal ownership AND an authorized active unit
AND a valid resource binding. Roommates do not gain one another's records. List and
detail use the same selection; guessed unrelated and missing IDs return 404.
Configured Resident-only principals also receive additional ownership filtering in
generic scoped HTTP/AI reads. Expired/inactive affiliation never restores broader
access. Existing unaffiliated Phase A scope contracts and legacy_demo remain
compatible; those identities cannot use E1 workflows without a configured unit.
Operational multi-role users retain their explicitly delegated operator authority.

Building/floor notices have a narrow membership entitlement: announcements.read on
the active unit, matching physical hierarchy/organization, valid target binding,
and an audience containing residents. This grants no general building read access.

All tests use isolated repository databases. Browser fixture uses an OS temporary
SQLite database, explicit synthetic building and provider mapping. Audited runtime
data and empty production onboarding are untouched.

## Resident navigation and screens

Five pages: **Home, Visitors, Maintenance, Access, Notices**. There is no Admin
configuration, building operations dashboard, global security feed or Business
workspace in this portal. Existing system fonts/tokens and native semantic controls
are retained; no dependencies, external fonts, analytics or live video are added.

Home shows the resident greeting and active unit/floor, relevant current notices,
personal expected visitors and open maintenance counts, authorized quick actions,
and honest personal access state. Mobile places notices and personal summaries
before quick actions. Cards replace tables. An unavailable unit has a useful
assignment explanation and no enabled mutation controls.

Notices include published building-wide/residential/own floor/own unit notices.
Business-only, unrelated unit/floor and future notices are hidden. Expired notices
are a separate expandable archive. Title, message, publish time and optional expiry
are shown; no invented importance field.

Visitors support name, start/end window, optional note and own-unit affiliation
selection only when multiple authorized units exist. A persisted temporary logical
authorization records its unit and validity. Expected/arrived/completed/expired/
cancelled statuses and Scheduled/Active/Ended/Revoked logical states remain distinct.
Operator arrival confirmation is reused. Future/unarrived visits can be cancelled
with explicit confirmation; cancellation revokes the logical authorization and
prevents subsequent Manager arrival. No invitation grants physical access.

Maintenance supports problem, description, priority and session-derived unit and
reporter. Tracking shows Submitted, Assigned, In progress, Resolved and Closed.
Status/time updates are readable; only explicitly public messages appear. Manager
has separate **Internal note (operators only)** and **Reply to resident** fields.
Operator-private notes, assignee identity and internal actor fields stay private.

Access shows only personal explicitly bound physical authorizations and the existing
policy engine's current outcome where delegated. No raw permission objects/IDs or
door controls appear. Empty configuration says **Access information is not
configured**; residency and configured product locations do not imply physical zones.
The policy engine uses its complete repository snapshot, preserving emergency rules.

My Unit is not a separate page in E1. Home identifies unit and floor. No personal
device controls or camera viewing are added.

## Ring and contextual assistance

Resident Ring context requires explicit personal event/device binding, matching
provider source/account, application read permissions and active unit scope. It
never imports the Manager/global entrance feed. The fixture explicitly maps a
synthetic doorbell to Apartment 101. Resident 102 sees no signal.

`visitor_arrives` renders **Someone is at your doorbell. Identity not verified.**
with Simulation and **No door was unlocked automatically.** It does not rename a
visitor, claim facial recognition, mark a visit arrived or alter physical access.
The six preserved scenarios are visitor_arrives, package_delivery,
after_hours_person, emergency_access, contact_sensor_sequence and device_lifecycle.

Ask Nodum embeds page-specific local Guide, available without Bedrock. AI reads use
resident_context filtered by the same personal scope plus ai.use. Typed
resident_invite_visitor/resident_report_maintenance actions only prepare proposals.
The UI shows exact unit, visitor/window or issue/priority and requires explicit
confirmation. Confirmation rechecks authenticated owner, current permissions,
active affiliation and scope, and remains at-most-once. The model cannot confirm.
Forged actor IDs are rejected by the existing session boundary.

Browser AI QA uses a clearly synthetic provider through the actual orchestrator,
pending-action store and confirmation API. Real AWS inference/availability is not
claimed. The existing Bedrock adapter and outage/security tests are preserved.

## Validation — October 7, 2026

| Check | Result |
|---|---|
| Full memory backend suite | 880 passed |
| Full SQLite backend suite | 880 passed |
| Resident focused suite | 34 passed |
| Resident + Manager + Admin + hierarchy + authorization | 220 passed |
| Six Ring scenarios (explicit focused run) | 6 passed |
| Frontend tests | 26 passed |
| Typecheck / lint / production build | Passed |
| Real-browser page/width matrix | 15 combinations passed: all five pages at 1440/768/390 |
| Real visitor scheduling/cancellation | Passed; no physical permission mutation |
| Real maintenance report/public reply | Passed; private note absent |
| AI proposals/confirmation/outage Guide | Passed with synthetic provider and real API/actions |
| Keyboard / focus / touch | Skip link, native keyboard controls, visible outline, 44px buttons passed |
| Loading / empty / error / recovery | Passed with controlled browser responses |
| Secret scan / git diff --check | Passed |

Privacy tests cover Resident 101 vs 102 AND roommates, business/unrelated audience
exclusion, own access authorizations, broad building grant confinement, guessed
IDs, list/detail parity, forged fields, CSRF, expired affiliation, suspended account,
permission revocation, AI scope and confirmation ownership/revocation. Existing
Manager/Admin/business isolation/auth/CSRF/CORS/Guide/Bedrock/Ring tests pass in
both complete suites. No actual hardware verification or broad camera rights are
claimed. Browser console errors during intentional 403/404/500/503 checks are
expected network failure responses; no uncaught application exception was observed.

Reproduce backend checks from `backend` with `.venv/Scripts/python.exe -m pytest` and
`--repository-backend memory` or `sqlite`, using a new isolated `--basetemp`.
Run `python -m tests.resident_qa_server` for the temporary QA backend on 8768;
start Vite on 5176 with the API base and credentialed-request variables described
in `frontend/tests/resident.browser.js`. Execute that file through Playwright.

## Screenshots

- [Home desktop](qa/resident-home-1440.png), [tablet](qa/resident-home-768.png), [phone](qa/resident-home-390.png): calm notices, personal summaries and actions.
- [Visitors](qa/resident-visitors-1440.png), [phone invitation](qa/resident-visitor-form-390.png): own visits and derived destination.
- [Maintenance](qa/resident-maintenance-1440.png), [phone issue form](qa/resident-maintenance-form-390.png): simple reporting and readable updates.
- [Access](qa/resident-access-1440.png): honest unconfigured state without door controls.
- [Notices](qa/resident-notices-1440.png): relevant audience notices only.
- [Ring](qa/resident-ring-390.png): unidentified simulated personal signal.
- [AI confirmation](qa/resident-ai-confirmation-390.png), [outage Guide](qa/resident-guide-outage-390.png).

## Remaining limitations

No Business/E2 workspace. No physical access bridge, verified door actuator,
unsupported camera/live video, biometric identity, automatic unlock or inferred
provider mapping. No visitor invitation delivery/QR credentials, photo attachments,
lease management, standalone My Unit controls or complex workspace switching.
The local Guide provides contextual guidance; natural-language data interpretation
requires available Bedrock. Ambiguous visitor dates/times require clarification.
Records created in unrelated legacy services are not silently imported or assigned
ownership. Configured devices remain unverified absent actual telemetry.

E1 is READY FOR REVIEW within this scope. Stop here; no E2 or deployment action.
