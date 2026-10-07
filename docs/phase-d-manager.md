# Phase D Manager checkpoint

**READY FOR REVIEW**, with the limitations below. Phase E has not begun.
All Phase A–D work remains uncommitted on `product-platform`. Main and HEAD
remain `71927dd60294b7570756d906d7b339d543956c41`. No commit, merge, push,
deployment, real provider command, or audited runtime database operation occurred.

## Manager experience

Manager is an operational role with explicit delegated permissions. A role label
does not confer Admin authority or physical access. Scoped Manager accounts open
a dedicated workspace; an explicitly assigned Admin with configuration rights
retains the Phase C Admin landing behavior. Complex workspace switching remains
future work. Legacy demo continues opening the existing operator workspace.

Navigation is Overview, People, Visitors, Access, Maintenance, Security, Activity,
and optional Announcements. Sections follow the session's explicit permissions;
backend reads and writes independently reauthorize each resource. Setup, role
creation, integration configuration, organization ownership and system configuration
are absent from Manager navigation.

Overview starts with the operator greeting and an aggregate building status with
reasons. Four compact counts show visitors today, unresolved maintenance, active
incidents and recorded offline devices. Requires attention precedes authorized
quick actions and recent activity. Mobile uses a compact section selector, readable
single-column records, and the same status/attention/action/activity order.
System fonts, existing color tokens, semantic native controls and privacy protections
are retained; no dependency, external font, analytics or shadcn installation was added.

Status priority is Incident active, Degraded systems, Attention needed, Normal.
Configured devices without supported operational records remain Unverified and
produce an attention explanation. Missing full-building read coverage is explicitly
labeled partial scope; an empty partial projection returns Status unavailable,
not Normal. Counts describe visible records and never establish physical readiness.
Successful snapshots refresh every minute; refresh failure clears the data instead
of leaving a misleading stale building status visible.

## People

People uses configured affiliations and explicit person/affiliation bindings.
Residents, Staff / Operators and Contractors have distinct groups; Businesses
lists visible businesses and visible affiliated staff. Active requires an active
account and affiliation inside its date bounds. Unit/area and end date are shown,
including the year; usernames, credentials and authentication internals are absent.
No account role is inferred from a legacy person label, and no lease system was added.
The current affiliation model represents maintenance personnel, not a separate
contractor organization or contract lifecycle.

## Announcements

Managers with `announcements.publish` can store an announcement in an explicitly
authorized building, floor or area. Fields are title, message, audience (everyone,
residential or business), publication time and optional expiry. Creator identity,
scope, building identity, demo provenance and timestamps come from the server.
Expiry must follow publication. The UI distinguishes Published, Scheduled and Expired.
Reads require `announcements.read` on the bound announcement resource.

Audience and timing are persisted, real workflow records. This phase does not
send email/push messages or implement Resident/Business announcement-reading
workspaces, audience delivery jobs, notice edits or deletion. It makes no delivery claim.

## Maintenance

`maintenance.create` reports an issue at an authorized configured location.
Reporter identity is session-derived. Records contain title, description, priority,
building/location scope, creation/update timestamps, status, optional assignee,
resolution timestamp and history. States are New, Assigned, In progress, Resolved
and Closed; explicit updates may reopen a request. Assigned requires a maintenance
person. An assignee must be visible, actively affiliated to this building and in a
maintenance role. Updates require `maintenance.manage` on both request and target.
Reads require `maintenance.read`. Notes, actors, timestamps and status history
remain persisted. No hardware repair or physical resolution is inferred from a
status change. Enterprise work orders, attachments and escalation automation are absent.

## Visitors and access

New product visits persist visitor name, session-derived host, configured destination,
time window, timestamps and demo provenance. Managers with `visitors.invite` on the
target can schedule; `visitors.check_in` on the visit and target can mark arrival
inside its window. Repeated or out-of-window arrivals are rejected. Expected,
Arrived, Active and Expired / Completed records have clear labels and a status filter.

Scheduling or arriving a product visit grants **no physical access**. Product
locations are not automatically legacy physical access zones. The UI states this
boundary explicitly. Existing appointment, check-in and temporary-permission
services remain available and are projected alongside the new visit records.
Legacy records remain invisible without explicit bindings; there is no ownership import.

Access presents a person, area, ALLOWED / DENIED and the backend's human-readable
reason. Only readable persons/physical zones with evaluation authority appear.
Temporary permissions show named areas and time windows without internal permission
objects. Evaluation sends no door command. In browser QA, a machine-room request
was DENIED: “An explicit physical access grant is required.” Backend suites also
cover allow/deny paths, visitors and physical policy safety independently.

## Security, activity and devices

Security separates active incident summaries, device/system concerns and recent
Ring signals. Offline is taken from a recorded operational device state;
configured-only hardware is Unverified. Simulation badges stay visible. Devices
have operational status and location with a Contact Admin explanation, without
configuration, stream or unlock controls. Offline duration is not invented.

Activity projects authorized Ring signals, new operational changes, existing
actuator outcomes and appointment check-ins chronologically. Entries show time,
action, visible actor, visible location, result and simulation provenance where
available. Hidden referenced persons/areas use scoped labels. The existing event
store was retained; this is not a complete immutable compliance journal. Browser
access evaluations remain a local result rather than a new persistent access-check
event store.

## Ring visitor-arrival result

The signed `visitor_arrives` simulator produces motion, doorbell and person events
through the existing Ring receive/signature/normalization/deduplication/inbox path.
Manager Visitors shows those signals with Ring Simulation badges and explains that
identity/destination are unverified and no door was unlocked. Recent signals feed
Overview attention and authorized Activity. A Manager reviews the signal and
manually matches/checks the relevant visit; no automatic identity correlation was added.
Provider-to-product location mapping remains unverified and is labeled accordingly.

All six scenarios passed in Manager browser QA and the backend suites:
visitor_arrives, package_delivery, after_hours_person, emergency_access,
contact_sensor_sequence and device_lifecycle. Browser before/after comparisons
confirmed that scenario generation leaves visitors and temporary permissions
unchanged. Backend Manager tests additionally assert no actuator event and no
remote discovery call. Simulation provenance recognizes the reserved simulator
account as well as the source marker; actual simulator sources use device IDs.

In scoped mode, the existing simulation operator dependency now checks the explicit
`simulation.run` binding rather than requiring the obsolete legacy person role.
Legacy demo retains its manager-person gate. Scoped Manager accounts created by
Phase C as ordinary employee identities can therefore use a delegated simulator
without acquiring Admin or physical authority.

## AI and Guide

Ask Nodum is contextual to the current page and uses the existing Bedrock endpoint.
A read-only `manager_operations` tool supplies bounded attention, unresolved
maintenance, expected visitor and offline-device summaries. Every contributing
resource must satisfy its normal read permission and `ai.use`; no new model write
tool was added. Existing confirmation reauthorization remains intact.

Manager Guide contains local contextual help for all eight sections, including
the Ring arrival/identity/access boundary. It has no network or action dependency.
A mocked Bedrock 503 preserves the outage explanation and Guide while core
operations remain usable. Actual AWS Bedrock availability was not asserted.
Legacy Guide and Bedrock outage/authentication tests remain in the complete suite.

## APIs, migration and security

New endpoints are GET `/manager/snapshot`, POST `/manager/announcements`,
POST `/manager/maintenance`, PATCH `/manager/maintenance/{id}`,
POST `/manager/visitors` and POST `/manager/visitors/{id}/arrive`.
They use the existing scoped session/CSRF dependency and transaction-scoped checks.
Inputs forbid client-selected reporter/creator/scope/building authority.
Resources receive explicit bindings and unbound operational resources default deny.

Migration **8** appends `product_operations`, with typed record kinds, JSON payloads,
a scope foreign key, kind/id primary key and scope index. Applied migrations 1–7
were not edited. Both repositories implement the operational record contract.
Upgrade from migrations 1–7, restart and foreign-key enforcement are tested on
isolated SQLite files. Empty production onboarding and the opt-in reference seed
are unchanged. New operational demo records exist only in the explicit QA fixture.

## Final validation

| Check | Result |
| --- | --- |
| Complete memory backend | **846 passed**, 76.85 seconds |
| Complete SQLite backend | **846 passed**, 190.64 seconds |
| Focused Manager memory | **32 passed** |
| Focused Manager/Admin/hierarchy/authorization memory | **186 passed** |
| Frontend tests | **23 passed** |
| Typecheck | Passed |
| Lint, including saved browser script | Passed |
| Production build | Passed |
| Manager real HTTP/SQLite browser script | **8 grouped checks passed**, including **24 screen/width combinations** |
| Six Ring scenarios | Passed in browser and legacy/scoped backend regressions |
| Business/resident/default-deny/session/CSRF/revocation/AI isolation | Passed |
| Loading, backend-error recovery, empty scopes | Passed in separate browser checks |
| Keyboard focus, skip link, mobile selection, Guide, 44px buttons | Passed |
| Heuristic secret scan | **101 changed/new files, 81 text + 20 PNGs, zero flagged files** |
| `git diff --check` and new-text whitespace check | Passed |

The final backend totals supersede the earlier 838 totals. The 32 Manager tests
include six Manager Ring projections and migration/configuration-outage tests.
The complete SQLite run includes the same Manager tests. Full suites include Admin,
visitor/access, auth/CSRF/CORS, Ring processing, Bedrock/Guide and isolation regressions.
No audited runtime database was used. A resumed pytest run initially failed because
the system pytest temp directory was inaccessible; fresh workspace-local test
directories passed and were removed after validation. The sandbox process helper
was unavailable during resumption, so approved shell execution was used.

The saved browser script uses real HTTP, sessions and synthetic temporary SQLite
for writes. Bedrock outage, loading/error and empty projections are explicitly
browser-mocked state tests. It is not a physical hardware or live-provider test.
The five-second Overview goal was reviewed visually, not measured in a user study.

Gitleaks is unavailable. The heuristic scan examines all changed/untracked text
files for AWS access-key identifiers, private-key headers, GitHub token formats
and Slack token formats, without printing secret values. Zero matches is not a
claim of a complete entropy-based secret audit.

## Screenshots and visual review

- [Overview desktop](qa/manager-overview-1440.png): status/reasons, compact counts,
  attention, quick actions and recent operational activity.
- [Overview tablet](qa/manager-overview-768.png): same hierarchy with adapted columns.
- [Overview mobile](qa/manager-overview-390.png): compact navigation, readable status,
  stacked attention/activity and touch-sized quick actions.
- [People](qa/manager-people-1440.png): dated affiliations, active labels and business staff.
- [Visitors desktop](qa/manager-visitors-1440.png) and
  [mobile](qa/manager-visitors-390.png): scheduled/arrived records and labeled Ring signals.
- [Access](qa/manager-access-1440.png): named-person/area evaluation and readable outcome.
- [Maintenance desktop](qa/manager-maintenance-1440.png) and
  [mobile](qa/manager-maintenance-390.png): issue detail, assignment/status and history.
- [Security](qa/manager-security-1440.png): incident, device and Ring groupings.
- [Activity](qa/manager-activity-1440.png): chronological operational records.
- [Announcements](qa/manager-announcements-1440.png): scoped audience form and saved notices.

All eight screens were inspected at 1440/768/390 with no horizontal overflow.
Screenshots depict synthetic QA data only. Manual inspection included Overview
mobile/desktop and People; automated visual/layout checks covered all combinations.

## Phase D file manifest

New source/tests/documentation (14):

- `backend/app/api/manager.py`
- `backend/app/manager_repository.py`
- `backend/app/models/manager.py`
- `backend/app/services/manager.py`
- `backend/tests/manager_qa_server.py`
- `backend/tests/test_manager.py`
- `frontend/src/manager/ManagerWorkspace.tsx`
- `frontend/src/manager/ManagerGuide.tsx`
- `frontend/src/manager/api.ts`
- `frontend/src/manager/model.ts`
- `frontend/src/manager/manager.css`
- `frontend/tests/manager.browser.js`
- `frontend/tests/manager.test.mjs`
- `docs/phase-d-manager.md`

Updated existing Phase A–C files (10):

- `backend/app/api/ring.py`
- `backend/app/database.py`
- `backend/app/main.py`
- `backend/app/models/authorization.py`
- `backend/app/repository.py`
- `backend/app/services/authorization.py`
- `backend/app/services/agent_tools.py`
- `backend/app/sqlite_repository.py`
- `frontend/src/App.tsx`
- `frontend/src/admin/model.ts`

New screenshots (12): the Manager PNGs linked above. Total Phase D manifest:
**36 files**. This distinguishes Phase D changes from the preserved uncommitted
Phase A–C work. No OpenCode delegation was used.

## Remaining limitations

- Product visit records are operational only; product-to-physical access-zone
  integration, provider/device imports and identity matching remain future work.
- Hardware verification, physical telemetry, real unlock/stream/audio and Edge
  runtime remain unimplemented or unverified. Ring ingestion does not unlock doors.
- Announcements have stored audience/timing but no external delivery or Resident/
  Business reading workspace. Full Resident/Business products were not begun.
- People requires explicit affiliations; complex lease/contractor/workspace switching,
  invitations/password reset, full work orders and richer policy editing remain future.
- Read views are scoped projections, not an immutable compliance ledger or an
  authoritative proof of physical building readiness. Large-installation pagination
  and dedicated persistent access-evaluation history remain future improvements.

**PHASE D READY FOR REVIEW.** Stop here; no Phase E, commit, merge, push or deployment.
