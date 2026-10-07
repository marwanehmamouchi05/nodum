# Phase E2 — Business experience

**READY FOR REVIEW**, October 7, 2026. Work remains uncommitted on
`product-platform`. Main/HEAD remain `71927dd60294b7570756d906d7b339d543956c41`.
Approved A–E1 work is preserved. No Phase F, commit, merge, push or deployment.

## Files changed in E2

New backend:
- `backend/app/api/business_workspace.py`
- `backend/app/models/business_workspace.py`
- `backend/app/services/business_workspace.py`
- `backend/app/services/business_boundary.py`
- `backend/app/services/account_provisioning.py`
- `backend/tests/test_business_workspace.py`
- `backend/tests/business_qa_server.py`

Existing backend files extended:
- `backend/app/models/authorization.py`: narrow `business.staff.manage` capability.
- `backend/app/services/authorization.py`: explicit role ceilings and tenant confinement.
- `backend/app/services/admin.py`: reuse shared account provisioning; existing authority/audit preserved.
- `backend/app/api/manager.py`: configured tenant-only accounts use tenant workspaces.
- `backend/app/services/agent_tools.py`: Business context, typed proposals and fresh confirmation checks.
- `backend/app/services/orchestrator.py`: Business scope/clarification/confirmation instructions.
- `backend/app/main.py`: Business router.

New frontend:
- `frontend/src/business/BusinessWorkspace.tsx`
- `frontend/src/business/BusinessForms.tsx`
- `frontend/src/business/BusinessHelp.tsx`
- `frontend/src/business/api.ts`
- `frontend/src/business/model.ts`
- `frontend/src/business/business.css`
- `frontend/tests/business.test.mjs`
- `frontend/tests/business.browser.js`

Existing frontend files extended:
- `frontend/src/App.tsx`: dedicated Business landing, respecting Admin/Manager precedence.
- `frontend/src/admin/model.ts`: human-readable staff-management delegation label.

Documentation: this report. Screenshots: 18 `docs/qa/business-*.png` artifacts below.
The wider worktree also contains the previously approved A–E1 changes.

## Migrations and storage

No migration 9. Migrations 1–8 unchanged. Existing accounts, role assignments,
affiliations, scopes, bindings and Phase D operational JSON records are reused.
No duplicate Business visitor/maintenance/notice store or event-store rewrite.

All QA used isolated memory/SQLite test storage. The browser server uses an OS
temporary SQLite DB, explicit synthetic reference building and provider mapping.
Audited runtime data, legacy_demo and empty production onboarding are unchanged.

## Role and business boundary

Business context derives from active dated Business Admin/Staff affiliation,
matching live role grants, unit/business structure and explicit resource bindings.
Only one distinct active business is accepted. A client cannot supply a business
ID, arbitrary destination, role, host or reporter as authority.

Business Admin sees authorized business records. Business Staff sees only its own
visitors, maintenance, activity and personal access; notices are shared by matching
audience. Staff has no account-management authority. Each section/action is
permission-driven and each backend action reauthorizes independently.

Configured tenant-only principals receive an additional boundary in generic
HTTP/AI reads. Even a broad Business grant at building scope does not expose an
unaffiliated business, residential unit or global Manager projection. Existing
unaffiliated Phase A contracts remain compatible; E2 requires configured business
affiliation. Tenant expiry/inactivation never restores broader access.

List/detail/mutation projections use the same business boundary. Foreign and
missing operational/staff/notice IDs return 404 to an otherwise authorized caller.
Forged fields are rejected by immutable, extra-forbidden request models. Session,
CSRF/CORS and server-derived acting identity remain in force.

## Navigation and Home

Business Admin: **Home, Visitors, Staff, Maintenance, Access, Notices**, plus
**My Business** when hardware reads are delegated. Staff is visible only with
people.read or business.staff.manage. Other sections follow their explicit grants.

Business Staff: **Home**, and permission-dependent **Visitors, Maintenance,
Access, Notices**. No Staff management, Admin configuration, global security or
building-wide operations. Staff's own-record limitation is stated beside summaries.

Home leads with business name/floor and role, a compact Today strip, authorized
quick actions, Requires attention, relevant notices and recent business activity.
Counts derive from readable records; no synthetic fixed count or building-wide
"Normal" claim. Access says Not configured, Not evaluated, Active or Review needed
according to configured personal authorization outcomes. The layout is distinct
from both Manager's building status dashboard and Resident's personal Home.

System fonts, existing Nodum tokens and native semantic controls are retained.
No dependency, external font, analytics or unsupported component installation.

## Staff management and delegation

New **business.staff.manage** is a narrow explicit capability in the Business Admin
and building Admin ceilings. Adding a ceiling capability grants nothing to existing
accounts: building Admin must explicitly delegate it. It does not grant general
accounts.manage, authorization.manage, organization ownership or configuration.

Add Staff creates a real account through the shared Phase C password hashing,
private person scope and account/person bindings. The destination and fixed
Business Staff role come from the server. The form honestly requests initial
credentials; it does not pretend to send an email invitation.

Grantable permissions are the intersection of:
1. the authenticated Business Admin's current Business-role permissions in this business;
2. the Business Staff ceiling;
3. the active business context and staff-management capability.

UI labels describe actual personal scope: View own visits, Schedule own visitors,
Track own maintenance requests, View personal access and Read business notices.
No Owner/Admin/Manager/Resident/Security/Maintenance role selector or grant exists.

Staff can be listed and inspected within the business, with active/inactive status.
Membership updates revoke/restore only this business's Staff affiliations and role
grants. They do not globally suspend the account or alter unrelated roles. Revocation
immediately invalidates Business authorization. Building-suspended or date-expired
accounts cannot be restored here; building Admin must handle them. Business Admin
membership and the acting user's own account are protected from Staff mutation.

## Visitors and Ring

Visitor forms accept name, arrival start/end and optional note. Destination is the
active business; host is the session principal. Typed E2 creation persists a temporary
logical authorization. Expected/Arrived/Completed/Expired/Cancelled visitor state
and Scheduled/Active/Ended/Revoked logical authorization remain distinct.

Cancel is permitted before confirmed arrival/end and revokes the logical record.
Delegated visitor check-in permits an explicit manual arrival confirmation through
the existing Manager arrival service. Neither operation grants physical permissions.
Manager-created visits without a logical authorization display **Not configured**;
E2 does not invent one during projection.

The UI explicitly says **Physical building access is not configured automatically**.
No physical door/elevator bridge or simulated actuator control is added.

Ring requires an explicit business event/device binding, matching provider source
and account, active business scope, ring.read and hardware.read. Shared main-entrance
signals are not guessed or automatically routed. The QA fixture explicitly assigns
a synthetic doorbell to Business X; Business Y cannot see it.

Presentation: **Someone is at the doorbell assigned to Business X. Identity not
verified.** Simulation is visible; no door unlock, facial recognition, visitor-name
match or automatic arrival is claimed. Review visitors manually.

## Maintenance, notices, access and devices

Maintenance accepts problem, description and priority for the derived business.
Reporter comes from the session. Admin reads delegated business requests; Staff
tracks its own. Submitted, Assigned, In progress, Resolved and Closed are readable.
Only explicitly public Manager replies and status/time updates appear; private notes
and internal assignment/actor data are not exposed.

Notices include published everyone/business audiences in the physical ancestor
building/floor/business, with valid binding and same organization. announcements.read
on the active business is a narrow membership entitlement, not general building
authority. Residential-only, unrelated business/unit/floor and future notices stay
hidden. Expired notices are behind an archive, outside current Home notices.

Access is personal for both roles: existing explicitly bound physical authorizations
and current deterministic evaluation where permitted. No raw permission objects/IDs
or actuator controls. Physical evaluation retains the full policy snapshot so hidden
emergency records cannot accidentally weaken its decision.

My Business identifies business/floor and permitted registered product devices.
Configured records remain **Unverified** without telemetry. It exposes no live video,
provider credentials, configuration controls or unrelated hardware. Staff does not
inherit device viewing rights. Existing camera policies/permissions are not bypassed.

Recent activity reuses scoped operational records with readable action, actor,
business and time. Admin sees authorized business entries; Staff sees its own entries.
Unrelated building, business and residential activity is absent.

## AI/Guide and multi-role

Ask Nodum is embedded page help. Local Business Guide works without Bedrock.
business_context respects the same boundaries plus ai.use. Typed
business_invite_visitor/business_report_maintenance only prepare proposals. The UI
shows exact business/window or problem and requires explicit confirmation.
Confirmation rechecks authenticated owner, active affiliation, current action/AI
permissions and canonical scope, preserving at-most-once execution. The model cannot
confirm, create staff or grant permissions. Provider errors remain sanitized.

Browser AI tests use a synthetic provider through the actual orchestrator, persisted
proposal store and confirmation API. No real AWS inference/availability is claimed.
Core pages and Guide survive a simulated Bedrock outage.

Resident + Business Admin authorization remains a union of independently scoped
contexts. Tests prove business grants cannot be borrowed for a residential scope and
each portal selects its own records. Current landing precedence is Admin, Manager,
delegated configuration, Business, Resident, legacy operator. A mixed Resident/
Business account lands in Business; there is no client-selected acting identity or
complex workspace switcher in E2. Multiple simultaneous business contexts fail closed
until an explicit future switching workflow exists.

## Validation — final results

| Check | Result |
|---|---|
| Full memory backend suite | **926 passed** |
| Full SQLite backend suite | **926 passed** |
| Focused Business tests | **46 passed**, included in both full suites |
| Business + Resident + Manager + Admin + authorization + hierarchy | **266 passed** |
| Six Ring scenario focused run | **6 passed** |
| Frontend tests | **30 passed** |
| Typecheck / lint / production build | Passed |
| Business Admin browser matrix | 7 pages × 1440/768/390 = 21 passed |
| Business Staff browser matrix | 5 pages × 1440/768/390 = 15 passed |
| Real workflows | Staff account creation, membership revoke/reactivate; visitor create/cancel/manual arrival; maintenance report/public reply passed |
| Staff mobile mutations | Own visitor and maintenance creation passed; directory and Admin-owned records hidden |
| AI actions / outage | Typed proposals and explicit confirmation through real APIs; local Guide fallback passed |
| Accessibility | Native keyboard controls, working skip link, visible focus; 44px buttons/checkbox label targets passed |
| States | Loading, empty visitors/staff/maintenance/notices, safe error and recovery passed |
| Secret pattern scan / git diff --check | Passed |

Business privacy gates cover same-floor X/Y staff, visits, requests, notices, devices,
personal access, activity, Ring associations and AI context; guessed IDs, detail/list
parity and mutations; forbidden roles/permissions, authority intersection, immediate
membership revocation, expired affiliations, suspended users, CSRF/actor spoofing,
generic Admin escalation, broad-grant confinement and Resident/Business multi-role.
All previous Resident/Manager/Admin/authorization/business isolation/Ring/auth/Guide/
Bedrock regressions remain in the full suites. No uncaught application exception
was observed in browser QA. Intentional 500/503 responses were outage/error checks.

Run backend tests from `backend` with `.venv/Scripts/python.exe -m pytest` and a
new isolated `--basetemp`, selecting `--repository-backend memory` or `sqlite`.
Frontend uses npm test/typecheck/lint/build. `tests.business_qa_server` starts the
temporary backend on 8769; Vite on 5177 requires VITE_API_BASE_URL and credentialed
requests as documented in `frontend/tests/business.browser.js`. Execute that script
through Playwright. Small final label/mobile changes were rechecked on affected
screens after the complete 36-combination run.

## Screenshots / major screens

- Business Home: [desktop](qa/business-home-1440.png), [tablet](qa/business-home-768.png), [phone](qa/business-home-390.png).
- Staff Home: [desktop](qa/business-staff-home-1440.png), [tablet](qa/business-staff-home-768.png), [phone](qa/business-staff-home-390.png).
- [Visitors](qa/business-visitors-1440.png), [mobile invitation](qa/business-visitor-form-390.png), [Ring](qa/business-ring-390.png).
- [Staff](qa/business-staff-1440.png), [mobile account/delegation form](qa/business-add-staff-390.png).
- [Maintenance](qa/business-maintenance-1440.png), [mobile report](qa/business-maintenance-form-390.png).
- [Access](qa/business-access-1440.png), [Notices](qa/business-notices-1440.png), [My Business](qa/business-my-business-1440.png).
- [AI confirmation](qa/business-ai-confirmation-390.png), [outage Guide](qa/business-guide-outage-390.png).

## Remaining limitations and extension point

No Phase F. No verified physical bridge/actuator, provider import completion, live
video, facial recognition, automatic door unlock, invitation email/QR credentials,
password reset, maintenance photos or complex workspace switching. Business Staff
reads are deliberately personal rather than a general business directory/feed.
Staff creation provides initial credentials using the existing Phase C account flow;
it does not deliver invitations. AI staff provisioning is not exposed.

Existing legacy appointment records are not silently reassigned/imported into E2.
Future appointments/receptionist automation can call the same typed visitor service
after explicit authenticated business context/authority checks and persist an optional
appointment/source reference in the operational record. Exact dates/windows and
idempotent ownership must be validated; no separate scheduler/receptionist product
or additional migration is introduced here.

**E2 READY FOR REVIEW. Stop here.**
