# Phase A authorization checkpoint

Status: READY FOR REVIEW on `product-platform`. No Phase B implementation,
commit, merge, push, deployment, or audited runtime database migration was made.
The audited source remains at `main` commit
`71927dd60294b7570756d906d7b339d543956c41`.

## Modes and database safety

`NODUM_AUTHORIZATION_MODE=legacy_demo` is the default, preserving the audited
Amazon prototype. Its development APIs still accept synthetic actor context;
its production APIs retain the existing coarse Manager/session/CSRF gate.
This mode does not acquire tenant RBAC merely by applying migration 5.

`NODUM_AUTHORIZATION_MODE=scoped` requires a real session in development and
production. Client actor fields are checked against the session principal and
cannot select another acting identity. Target person/visitor IDs remain inputs,
subject to action/resource/scope authorization.

Scoped startup requires an explicit `DATABASE_URL` different from the audited
default `backend/nodum.db`, and disables automatic demo seeding. Operators must
also ensure that a custom URL is not their existing audited runtime database.
All verification used isolated temporary databases. No runtime database was opened
for migration, provisioning, inspection of records, or backup.

Do not point the old audited binary at a database upgraded to migration 5; its
schema-version guard will reject the newer schema. Source rollback and database
rollback are different operations. Keep the audited database separate.

## Exact identity and authorization model

Existing `NodumUser` accounts still authenticate through the existing opaque
session service. Each account references one existing building person; the
existing unique account/person association is unchanged. The server derives an
immutable `Principal(user_id, person_id)` from the HttpOnly session cookie.

Application roles are Owner, Admin, Manager, Security, Maintenance, Business Admin,
Business Staff, and Resident. An account may have multiple assignments, including
different roles in different scopes. Visitors remain domain identities and do
not receive accounts through invitation or check-in.

Every `RoleAssignment` contains `id`, `user_id`, `role`, `scope_id`, an explicit
permission list, `active`, and optional UTC `expires_at`. A role label without
permissions grants nothing. Effective authority is the union of live assignments,
limited by each role's ceiling and the requested resource's scope. There are no
wildcard/superuser grants and no automatic ownership or legacy-role conversion.

The permission catalog is:

| Category | Permissions |
| --- | --- |
| Ownership/governance | `ownership.manage`, `authorization.manage`, `accounts.read` |
| Reference information | `people.read`, `locations.read`, `businesses.read` |
| Hardware/privacy | `hardware.read`, `hardware.configure`, `camera.view` |
| Visitors | `visitors.read`, `visitors.invite`, `visitors.check_in` |
| Physical-access information | `access.read`, `access.check` |
| Maintenance/incidents | `maintenance.read`, `incidents.read`, `incidents.manage` |
| Activity/Ring | `activity.read`, `ring.read`, `ring.manage`, `ring.process`, `simulation.run` |
| AI | `ai.use` |

Role ceilings are maximum assignable permissions, never defaults:

| Role | Ceiling |
| --- | --- |
| Owner | Ownership management only; may appoint/revoke Admin assignments inside the owned scope |
| Admin | Authorization management, account reads, locations/businesses, hardware configuration/reads, Ring linking configuration, AI |
| Manager | People, locations/businesses, hardware reads and explicitly delegated configuration, visitors, access checks/reads, maintenance reads, incidents, Activity, Ring reads/processing, permitted camera content, simulation, AI |
| Security | People/locations, visitor reads/check-in, access checks/reads, incidents, Activity, Ring reads/processing, permitted camera content, hardware reads, AI |
| Maintenance | Locations, assigned-scope maintenance/hardware/access reads and access checks, AI |
| Business Admin | Scoped people/businesses/locations, visitors, access checks/reads, maintenance/hardware reads, permitted Ring/camera reads, AI |
| Business Staff | Scoped businesses/locations, delegated visitors, access checks/reads, maintenance reads, AI |
| Resident | Scoped people/locations, visitors/invitations, access checks/reads, maintenance/hardware reads, permitted Ring/camera reads, AI |

Admin does not receive people-directory, operational visitor/incident/Activity,
physical-access, Ring-inbox, or camera-content authority from the Admin role.
Owner has no operational read authority. Manager does not inherit authorization
management. A Manager can receive selected `hardware.configure` permission
without becoming an Admin.

Admin delegation requires `authorization.manage` in the target scope and every
permission being delegated in that same scope. Configuration-only Admins therefore
cannot manufacture operational authority. An initial trusted provisioner must
establish operational grants; subsequent delegation cannot exceed existing
authority. Owner's Admin-appointment exception is limited to the Admin ceiling,
so it cannot appoint an operational role or add private-content permissions.
Owner assignments themselves require trusted provisioning/recovery, not an HTTP
self-promotion endpoint. Assignment identity (account, role, scope) is immutable;
permission updates and explicit revocation are supported.

## Typed scopes and resource ownership

A `Scope` contains an ID, organization ID, kind, parent ID, and active flag.
Supported kinds and parents:

| Kind | Allowed parent |
| --- | --- |
| Organization | None; root ID must equal organization ID |
| Building | Organization |
| Business | Building |
| Location | Building, Business, or another Location |
| Person | Building, Business, or Location |

Scope authority flows downward only. Sibling businesses/people and unrelated
organizations do not inherit each other's grants. Missing, inactive, cyclic,
cross-organization, or incorrectly typed parent graphs deny access. Scope identity
and parent are immutable through the provisioning service.

`ResourceBinding(resource_type, resource_id, scope_id)` explicitly associates a
resource with one owning scope. Unbound resources are denied, including legacy
records and incoming provider events without a reviewed ownership binding.
Scopes and legacy resource bindings are established only through trusted
provisioning in Phase A. No public scope-building or ownership reassignment API
is provided. These are authorization boundaries, not Phase B building entities.

HTTP and AI share the operation contracts in
`backend/app/services/authorization_operations.py`. Filtered list/detail reads
use `ScopedRepository`. Forbidden details resolve as missing records; mutation
denials return 403. Newly invited identities/access grants inherit the explicit
host scope. Business appointments and checked-in identities/grants inherit the
explicit business/appointment scope. Incident ownership uses an authorized
common ancestor of all affected locations. Reused visitor IDs cannot transfer
between owning scopes. Mutation grants are rechecked within the domain transaction.

## Physical policy and AI boundaries

Application permissions are stored separately from the existing physical
`AccessPermission` records. `access.check` authorizes asking for a decision; it
does not authorize entry. Scoped checks disable the legacy Manager/responder
building-wide override and require explicit physical grants (or existing
validated contractor/visitor policy). Legacy checks retain the audited engine
behavior. Scoped physical evaluation uses complete permission/emergency snapshots,
even when those records are not visible to the caller. An unreadable physical
grant is omitted from the returned policy result.

Scoped AI read tools filter data before results reach Bedrock and require `ai.use`
as well as the relevant read authority. AI access checks authorize both the target
person and location, then use the full deterministic policy snapshot. Proposals
persist `authenticated_user_id` and the owning `authorization_scope_id` alongside
the exact arguments. Confirmation checks current identity, scope, grants and
expiry, consumes once, and rechecks authority in the write transaction. Legacy
unbound proposals cannot be confirmed in scoped mode, and bound proposals cannot
be consumed through the legacy confirmation path.

The Bedrock gateway, orchestrator, confirmation intent boundary, outage behavior,
and local Guide remain intact. Scoped frontend identity comes from session context;
the actor selector is hidden. Navigation/Guide topics reflect permission summaries,
while the backend remains authoritative for every resource. AI UI is hidden without
an AI grant. Account/grant context changes remount the active screen to discard its
local AI conversation/proposal state. Scope/account changes also clear cached
building data, Ring events and access decisions before requesting fresh data, and
invalidate older in-flight responses. Permission summaries refresh on window focus.

## Migration 5

Appended after unchanged migrations 1–4:

- `application_scopes`, including a parent foreign key.
- `application_role_assignments`, with user/scope foreign keys and a user/scope index.
- `application_resource_bindings`, with a composite resource key, scope foreign key,
  and scope index.

Migration initialization is transactional and repeatable. Migration 5 inserts no
roles, scopes, owners, resource bindings, or demo records. A v4 upgrade test verifies
legacy payload preservation, idempotence, schema versions 1–5, empty authorization
tables and a clean foreign-key check. Pending-action additions are optional JSON
fields; existing proposals remain readable but cannot gain authenticated authority.

## Verified checkpoint

On 2026-10-07:

- Before implementation: 660 backend tests passed.
- Focused final authorization suite: 102 passed.
- Complete final memory suite: 762 passed.
- Complete final SQLite suite: 762 passed.
- Frontend: 17 tests passed; typecheck, lint and build passed.
- Python dependency check: no broken requirements.
- All six Ring scenarios passed through the authenticated scoped HTTP gate in
  both repository suites: `visitor_arrives`, `package_delivery`, `after_hours_person`,
  `emergency_access`, `contact_sensor_sequence`, `device_lifecycle`.
- Existing Ring regressions remained passing. Scoped scenarios persisted signed
  normalized events, bound only explicit synthetic ownership, made no remote Ring
  discovery calls, and created no physical permissions/actuator executions.
- Scoped browser regression: eight checks passed (identity, selector, navigation,
  Guide, mobile overflow, direct URL denial, cache invalidation before a delayed
  refresh, revocation); zero writes.
- Legacy AI/Guide browser regression: nine behavioral checks passed; three mocked
  chat requests, zero building writes. Screenshot-export lines were omitted from
  the existing test after a capture timeout; a separate mobile screenshot captured
  successfully with animations disabled and was visually inspected.
- Diff/whitespace inspection passed. Changed-file secret-pattern scan found no
  AWS key, private-key, GitHub token, JWT, or literal sensitive environment-value
  matches. This was a local heuristic scan; Gitleaks was not installed.

No live AWS inference, live Ring linking, physical actuation, or production release
was performed or claimed. No additional dependencies were installed. Codex implemented
and reviewed this phase directly; OpenCode was not needed.

## Remaining boundaries for review

- Legacy mode remains intentionally a synthetic demo compatibility mode, not a
  scoped commercial deployment. New product installations must explicitly select
  scoped mode and a separate database.
- Initial Owner/Admin/operational assignments and legacy ownership bindings require
  explicit trusted provisioning. No account/onboarding or recovery UI was built.
- Configuration-only Admins cannot delegate permissions they do not hold. Review
  the initial trusted operational-grant process before Phase C account management.
- Hardware mutations, credential scans, journey mutations and the Atlas composite
  demo are denied in scoped mode until their complete contracts are implemented.
  They remain working in the audited legacy mode. `hardware.configure`, `accounts.read`
  and `camera.view` include foundations for later APIs; no unsupported hardware or
  streaming endpoint was fabricated.
- Existing incident/invitation/Ring services retain some legacy domain-role checks,
  which may reject a newly configured account despite an application grant. Those
  conservative restrictions need role-specific integration later; they cannot
  bypass the application gate.
- Signed provider ingestion remains an independent machine boundary. Live Ring
  events require explicit reviewed scope association before scoped users can read
  them. The unverified inbound token-delivery adapter still fails closed.
- No live push invalidation or general authorization-change audit feed was added.
  Server grants are rechecked on requests; frontend summaries refresh on focus.
- SQLite's existing one-writer limit, local file trust boundary and at-most-once
  AI confirmation crash window remain. This checkpoint is not production certification.

## Files changed

<!-- phase-a-manifest -->

44 files:

- `README.md`
- `backend/app/api/access.py`
- `backend/app/api/agent.py`
- `backend/app/api/appointments.py`
- `backend/app/api/auth.py`
- `backend/app/api/authorization.py`
- `backend/app/api/building.py`
- `backend/app/api/dependencies.py`
- `backend/app/api/emergencies.py`
- `backend/app/api/guests.py`
- `backend/app/api/operator.py`
- `backend/app/api/ring.py`
- `backend/app/authorization_repository.py`
- `backend/app/config.py`
- `backend/app/database.py`
- `backend/app/main.py`
- `backend/app/models/agent.py`
- `backend/app/models/authorization.py`
- `backend/app/repository.py`
- `backend/app/services/access.py`
- `backend/app/services/access_engine.py`
- `backend/app/services/agent_actions.py`
- `backend/app/services/agent_tools.py`
- `backend/app/services/authorization.py`
- `backend/app/services/authorization_operations.py`
- `backend/app/services/scoped_repository.py`
- `backend/app/sqlite_repository.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_authorization.py`
- `backend/tests/test_ring.py`
- `docs/access-policy.md`
- `docs/agent-layer.md`
- `docs/authentication.md`
- `docs/persistence.md`
- `docs/phase-a-authorization.md`
- `frontend/src/App.tsx`
- `frontend/src/api/authorization.ts`
- `frontend/src/api/client.ts`
- `frontend/src/guide/GuidePanel.tsx`
- `frontend/src/hooks/useBuilding.ts`
- `frontend/src/pages/Assistant.tsx`
- `frontend/src/pages/shared.ts`
- `frontend/tests/authorization.browser.js`
- `frontend/tests/authorization.test.mjs`
