# Phase C Admin checkpoint

**READY FOR REVIEW**, subject to the explicit limitations below. Phase D has
not begun. Work remains uncommitted on `product-platform`; audited main/HEAD
remains `71927dd60294b7570756d906d7b339d543956c41`. No push, merge, deployment,
audited database migration, or real provider/hardware action was performed.

## Experience and navigation

Scoped users with configuration/governance permissions open a dedicated Admin
workspace before the operator component mounts. No visitors, incidents, private
activity, or Ring-event requests are made by Admin onboarding. Legacy demo mode
continues using the existing operator workspace. Multi-role users with setup
permissions default to Administration; no complex workspace switch was added.

Navigation follows granted permissions:

1. Setup
2. Building
3. Hardware
4. Integrations
5. Accounts
6. Roles & Permissions
7. Policies
8. System & Audit

The empty landing screen has one primary action, **Start setup**, visible
configuration counts, and an explicit synthetic-demo alternative. The initial
provisioned Admin is included in the account count; an otherwise empty install
therefore honestly shows one account, zero buildings/areas/hardware. Configured
screens use the existing system font, color tokens, buttons, forms, status
badges, spacing, keyboard focus, and responsive layout. No dependencies, external
fonts, analytics, shadcn installation, or CAD/spatial geometry were introduced.

## Onboarding and building

Setup steps are Building → Floors & Areas → Hardware → Device Mapping → Accounts
→ Roles & Permissions → Policies → Review. The current step, policy-boundary
review, and completion acknowledgement are persisted per building. Review
completion requires floors, areas, mapped registered devices, and acknowledged
policy boundaries. Hardware may be connected later; completion does not claim
physical operational readiness.

Organization identity is created only inside an explicitly provisioned
organization scope where the principal already has configuration authority.
No public setup can appoint itself Owner or Admin. Building creation supports
Residential, Commercial, and Mixed-use, with name, address, and description.
Floors have ordering, including underground floors. Typed spaces distinguish
locations/zones, residential units, businesses, and rooms; common and restricted
designations are descriptive and never implicit access grants. Names and building
details are editable. Parent/ownership changes remain controlled operations.

Visualization is a configuration-driven hierarchy tree with floor/area labels,
unit/business distinctions, and device counts, preserving the Phase B contract
for a richer visualization later. It has no fabricated geometry.

## Hardware, Ring, and Edge

Hardware inventory shows names/types, integration, cloud/edge/simulation path,
physical assignment, and honest capability/connection state. A device can be
registered without a location; it remains building-bound and explicitly marked
**Needs assignment**. Mapping reauthorizes both the source device and target
location, rejects cross-building moves, and atomically updates physical parent,
scope binding, relational storage, and configuration audit.

Ring is the supported cloud option. **Prepare Ring connection** explicitly
creates a cloud configuration record and the scoped installation binding for
the existing signed Ring linking flow. It does not fabricate a token, claim
physical connectivity, or modify legacy account ownership. Configuration
metadata requires both actual account ownership and an explicit account binding;
an unbound legacy account remains denied. The UI directs the user to start the
supported Ring-side linking flow and complete secure Nodum confirmation.
Provider confirmation and credentials remain prerequisites. Device discovery
is labeled unverified rather than replaced by a synthetic list.

Simulation records and reference devices are explicitly labeled demo. Existing
Ring visitor-arrival simulation remains available only with its existing
authorization and simulator requirements. No physical command/stream buttons
appear for unverified capabilities. Edge is **Not installed**, described as a
future local gateway, with no discovery or runtime controls.

## Accounts and permissions

New account creation validates the login and password, creates a new person and
private person scope beneath an explicitly authorized building/unit/business/
area, and binds the account and person. It grants no roles, application rights,
or physical access automatically. Passwords are hashed through the existing
audited implementation, submitted as secret inputs, omitted from responses and
audit, and cleared from the form after account creation. Accounts can be
suspended/reactivated; suspension invalidates session authority immediately.
Self-suspension and active Owner suspension are refused.

Affiliation configuration is separate, with role-appropriate target choices,
optional start/end dates, and visible unit/business assignments. It does not
change ownership or authorize access. Visitor is never offered as an account
role. Lease management is not implemented.

Roles are presented in human language. Delegation choices come from the server
for the selected scope and are intersected with the authenticated principal's
current permissions and the target role ceiling. Saving and revocation use the
existing Phase A service. Configuration-only Admin cannot delegate camera or
operational powers it does not hold. Manager setup powers are explicit grants.
Owner may appoint an existing Admin through the existing recovery boundary;
this does not expose private account/operational lists. Owner provisioning and
recovery remain trusted operations. The UI avoids accidental self-revocation.

One permission is added: `accounts.manage`, within Admin/Manager ceilings only,
requiring an explicit grant. Existing role labels still confer no automatic rights.

## Migration, policies, and audit

Migration **7** adds `product_admin_settings` and
`product_configuration_audit`, with scope foreign keys. Migrations 1–6 are
retained. Building metadata and unassigned-device support use validated JSON
extensions, retaining existing records. Tests cover clean/upgrade/restart/FK
behavior with temporary databases; no audited runtime data was opened.

Policies currently provides a persisted review of real authorization boundaries,
not a new policy engine or a pretend physical-access rule editor. The configuration
journal records Admin configuration actions without passwords, tokens, camera
content, or private operational activity. Existing Activity is unchanged. This
is not advertised as a complete immutable compliance audit of every legacy/API action.

## First installation

An empty scoped installation must first receive trusted initial identity and
authority. From `backend`, explicitly select a new, empty productization database,
set `NODUM_AUTHORIZATION_MODE=scoped` and `DATABASE_URL`, then run:

```text
.venv/Scripts/python.exe provision_admin.py --name "Your name" --username your-login
```

The script privately prompts for and confirms a password. It rejects the audited
default path and existing nonempty files, seeds no legacy demo, and explicitly
creates one Owner + Admin with configuration rights only. Sign in, then name the
organization/building in the UI. This command was not run against user runtime
data; its service is tested on isolated SQLite. Existing installations use their
trusted provisioning/recovery process rather than this first-install command.

The **Load synthetic demo building** action initializes a demo-marked root only
when no organization identity has been configured, or uses a separately
provisioned demo root. A real organization is never silently converted. It loads
the Phase B reference topology, with no new accounts, credentials, hidden role
assignments, or physical grants.

## Validation

- Final full memory backend: **814 passed**.
- Final full SQLite backend: **814 passed**.
- Focused Admin/hierarchy/authorization memory: **154 passed**
  (23 Admin, 29 hierarchy, 102 authorization).
- Earlier focused SQLite: **148 passed**; final complete SQLite includes all
  final Admin tests and the remaining regressions.
- Frontend: **21 passed**; typecheck, lint, production build passed.
- Real HTTP/SQLite Admin browser run: **9 checks passed**, including 24 populated
  screen/width combinations at 1440/768/390, empty-state widths, keyboard focus,
  real creation/mapping/delegation, persisted setup, demo, and failure recovery.
- Separate real HTTP Ring preparation check passed without provider calls.
- Scoped authorization browser: **8 checks passed**, zero writes.
- Legacy Bedrock/Guide browser: **9 checks passed**, three mocked chat responses,
  zero building writes; offline/local help, outage and authentication semantics,
  mobile overflow, and skip-link behavior preserved. Behavioral code ran with
  screenshot lines omitted; original legacy test source was not changed.
- All six Ring scenarios pass in legacy and scoped paths on both backends:
  visitor_arrives, package_delivery, after_hours_person, emergency_access,
  contact_sensor_sequence, device_lifecycle.
- Final heuristic secret scan: **75 changed/new files** (67 text files and
  8 screenshots), **zero flagged files**. Gitleaks is unavailable; this is not
  claimed as a full Gitleaks audit.
- `git diff --check` passed; new text files have no trailing whitespace.
- Audited Ring processing/simulation, auth, Bedrock, and orchestrator core
  match HEAD after Windows line-ending normalization. Main/HEAD refs are unchanged.

## Limitations and future work

- Policy editing/physical-access activation remains separate; this phase provides
  a truthful boundary review, not a new access engine.
- No provider-event/product-device bridge, live discovery-to-product import,
  physical verification, stream/audio/unlock, new vendor, or Edge runtime is claimed.
  Ring account ownership/scoping remains explicit; legacy records are not adopted.
- Account invitations/email delivery, password reset/change workflow, full lease
  management, a complex workspace switch, and CAD remain out of scope here.
- Configuration audit covers the new Admin workflow; it is not a complete
  tamper-proof journal for all existing endpoints.
- Initial identity/authority requires trusted provisioning; there is no unauthenticated
  ownership-claim setup route. Partial-scope delegates see authorized projections.
- Manager/Resident/Business operational workflows were not added. Basic affiliation
  configuration does not implement those products.

## Screenshots

- [Empty desktop](qa/admin-empty-1440.png)
- [Empty mobile](qa/admin-empty-390.png)
- [Configured building tree](qa/admin-building-1440.png)
- [Hardware desktop](qa/admin-hardware-1440.png)
- [Hardware mobile](qa/admin-hardware-390.png)
- [Accounts](qa/admin-accounts-1440.png)
- [Roles & Permissions](qa/admin-permissions-1440.png)
- [Integrations](qa/admin-integrations-1440.png)

## Phase C file manifest (37)

New source/documentation (15):

- `backend/app/admin_repository.py`
- `backend/app/api/admin.py`
- `backend/app/models/admin.py`
- `backend/app/services/admin.py`
- `backend/app/services/admin_provisioning.py`
- `backend/provision_admin.py`
- `backend/tests/admin_qa_server.py`
- `backend/tests/test_admin.py`
- `frontend/src/admin/AdminWorkspace.tsx`
- `frontend/src/admin/admin.css`
- `frontend/src/admin/api.ts`
- `frontend/src/admin/model.ts`
- `frontend/tests/admin.browser.js`
- `frontend/tests/admin.test.mjs`
- `docs/phase-c-admin.md`

New screenshots (8): the eight `docs/qa/admin-*.png` files listed above.

Updated files (14):

- `README.md`
- `backend/app/database.py`
- `backend/app/main.py`
- `backend/app/repository.py`
- `backend/app/sqlite_repository.py`
- `backend/app/models/authorization.py`
- `backend/app/models/structure.py`
- `backend/app/services/authorization.py`
- `backend/app/services/structure.py`
- `backend/app/structure_repository.py`
- `frontend/src/App.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/components/ui.tsx`
- `frontend/tests/authorization.browser.js`

The worktree also retains approved uncommitted Phase A/B changes. This manifest
identifies only Phase C edits. No OpenCode delegation was used.
