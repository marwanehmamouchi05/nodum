# Phase B checkpoint

Phase B implements configuration contracts only. No Admin UX, new provider,
Edge runtime, physical commands, video streams, or implicit legacy conversion.
Work remains uncommitted on `product-platform`; audited main/HEAD is
`71927dd60294b7570756d906d7b339d543956c41`.

## Hierarchy and ownership

`StructureNode` is a typed configuration record, stored separately from legacy
zones, businesses, integrations, and devices. Physical topology is:

Organization → Building → Floor → Location → Unit / Business / Room → Device.
Locations and rooms may nest. Integrations belong to a building; devices point
to one integration and one physical parent. Floors have an explicit ordering,
including negative underground order. Common/public flags describe space;
they never authorize access.

Every node has an organization, a building (except organization roots), and an
explicit application scope/resource binding. Creation validates these against
the parent; structural identities and ownership are immutable through normal
updates. Duplicate IDs, incompatible parents, scope collisions, and ownership
changes fail before writes. Unknown/unbound resources remain default-denied.

Authorization uses the existing Phase A typed scopes. Organizations/buildings
use their corresponding kinds; floors, locations, units, and rooms use location
scopes. Businesses have independent business scopes under the building, while
retaining their physical location/floor relationship. A floor grant therefore
does not inherit private business resources. Creation of a business requires
building-level configuration authority as well as authority on its physical
parent. Hardware inherits its location scope; integrations inherit building
scope. Private unit and business grants do not authorize siblings or ancestors.

Two application permissions are added: `structure.configure` and
`affiliations.manage`, available within Admin and Manager role ceilings only.
They require explicit assignments; neither role automatically receives them.
Physical access grants, camera viewing, activity, AI, and operational authority
remain separate. Admin configuration authority does not grant camera content.

## Affiliations

Affiliations connect an authenticated account and a role label to a target:
Resident → unit; Business Admin/Staff → business; Manager/Security → building
or location; Maintenance → building/location/room. They have active, start,
and end fields, validated date ordering, immutable identity, and explicit
resource bindings to the target scope. Concurrent affiliations to different
businesses are rejected across both business roles; nonoverlapping future
periods are permitted. Other simultaneous roles remain supported by Phase A.

Creation requires `affiliations.manage` on the target plus account/person read
authority for an explicitly bound account in the same organization. No missing
person ownership is inferred. An affiliation neither rebinds the person nor
grants application permissions or physical access. Date expiry describes the
affiliation; it does not implicitly revoke independent authorization grants.
That lifecycle coordination remains a future explicit workflow.

## Hardware and visualization contracts

`connection_path` is explicit `cloud`, `edge`, or `simulation` for integrations
and devices; devices must match their integration's building and path.
Configured records do not assert connectivity or execute anything. Capability
claims are rejected until supported by a verified adapter. There are no
credentials, arbitrary provider payloads, or URLs in these configuration models.

Authenticated, CSRF-protected scoped APIs:

- `GET /structure/catalog`: version 1 authorized node projection and device mappings.
- `GET /structure/nodes/{id}`: identical per-resource visibility to catalog.
- `PUT /structure/nodes/{id}`: create/configure with parent and existing-resource authorization.
- `GET /structure/devices/{id}/context`: organization/building/location/scope,
  connection path, demo marker, and readable ancestor labels for event context.
- `GET /structure/affiliations`, `PUT /structure/affiliations/{id}`: scoped configuration.

Catalog clients must handle partial trees: a unit/business user can see their
own resources without being authorized to read ancestor names or sibling data.
Device mappings appear only when both device and physical parent are readable.
No frontend changes were required. Existing visualization adoption is later work.

Mapping configured product device IDs to provider event identifiers is an
explicit future adapter binding, not guessed from legacy IDs/names. Existing
Ring processing and simulation continue on their audited records. These APIs
provide context for product devices without changing Ring ingestion or enabling
physical access to new topology through the legacy access engine. A future
explicit zone/provider bridge must preserve ownership and provider account checks.

## Empty and demo initialization

Scoped startup remains empty (`initialize(seed_demo=False)`); migration 6 seeds
nothing. Legacy startup and Atlas Dental/residential fixtures are unchanged.
No legacy ownership is assigned. Audited runtime SQLite was not opened or migrated.

`StructureService.bootstrap_organization` is a trusted provisioning function,
deliberately unavailable through HTTP. After explicitly provisioning a principal
and configuration grants, an operator may call
`load_reference_building(service, organization_id)` against a demo-marked
organization. It is not imported or called by startup. A real organization is
rejected. Replay validates exact fixture equality rather than overwriting edits,
and identity conflicts are checked before writes.

The synthetic reference contains 6 floors, 10 apartments, Business X/Y, all
specified underground rooms, entrance/lobby/elevator/common roof, a simulation
integration, and 4 clearly labeled demo device records. It creates no people,
passwords, accounts, role assignments, physical grants, or claimed capabilities.

## Migration and validation

Migration **6** adds `product_structure` and `product_affiliations`, with
foreign keys to hierarchy parents, organizations, buildings, application scopes,
integrations, users, and affiliation targets. Existing migrations 1–5 are retained.
Tests cover clean initialization, upgrade from 1–5, restart/idempotence, foreign
keys, unchanged legacy records, default deny, and no automatic legacy ownership.
All database tests use temporary files.

Final validation:

- Full memory backend: **791 passed**.
- Full SQLite backend: **791 passed**.
- Focused structure/authorization/agent/simulator memory run: **211 passed**
  (29 structure, 102 authorization, 59 agent/Bedrock, 21 simulator).
- Earlier focused SQLite structure/authorization run: **124 passed**;
  the final full SQLite suite includes all 29 final structure tests and all
  102 authorization tests.
- Frontend: **17 passed**; typecheck, lint, and production build passed.
- All six Ring scenarios pass in both legacy and authenticated scoped paths,
  on both repository backends: visitor_arrives, package_delivery,
  after_hours_person, emergency_access, contact_sensor_sequence, device_lifecycle.
- Bedrock SDK contracts, failure handling, proposal/confirmation authorization,
  and frontend Guide regressions pass. No live cloud/provider calls were made.
- `git diff --check` passed; new source files have no trailing whitespace.
- Secret heuristic scan: **51 changed/new files, zero flagged files**.
  Gitleaks is unavailable; this is a heuristic scan, not a full Gitleaks audit.
- Audited Ring service, simulator, and auth core match HEAD after normalizing
  Windows line endings. Main/HEAD refs still point to the audited commit.
- No new frontend UI was added; Phase B validation exercises the API contracts.

**READY FOR REVIEW.** Remaining integration work: explicit provider/zone bridges,
controlled device relocation, affiliation/grant lifecycle coordination, root
provisioning UX, and visualization adoption. These are not claimed as implemented
or automatically enabled by this checkpoint. Phase C has not begun. No commit,
merge, push, deployment, audited database migration, or legacy ownership changes.

## Phase B files (16)

New:

- `backend/app/models/structure.py`
- `backend/app/structure_repository.py`
- `backend/app/services/structure.py`
- `backend/app/services/reference_building.py`
- `backend/app/api/structure.py`
- `backend/tests/test_structure.py`
- `docs/phase-b-structure.md`

Updated:

- `backend/app/database.py`
- `backend/app/repository.py`
- `backend/app/sqlite_repository.py`
- `backend/app/main.py`
- `backend/app/models/authorization.py`
- `backend/app/services/authorization.py`
- `backend/tests/test_authorization.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_ring.py`

Existing restart tests now expect the current migration list rather than a
hardcoded version 5. Phase A uncommitted changes remain present alongside this
checkpoint; this manifest lists only Phase B edits.
