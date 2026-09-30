# SQLite persistence

Nodum uses Python's built-in sqlite3 driver. No database server, ORM, new package,
container, or cloud resource is required. Existing API paths, response models,
services, and deterministic access policies are unchanged.

## Running locally

The default is:

    DATABASE_URL=sqlite:///./nodum.db

Relative paths always resolve against the backend directory, even when launching
from the repository root. The default database is backend/nodum.db.
An absolute Windows path can use sqlite:///C:/dev/nodum-data/nodum.db; an absolute
POSIX path uses sqlite:////absolute/path/nodum.db. Parent directories are created.
Only file-backed SQLite URLs are supported; unsupported schemes, :memory:, and
URL options are rejected explicitly.

Start from backend:

    .\.venv\Scripts\python.exe -m uvicorn app.main:app --env-file ../.env --reload

Or export DATABASE_URL in the server environment. Startup reads configuration,
initializes the schema, seeds missing demo records, and installs SQLiteRepository
and its pending-action service into application state. Importing the app or
generating OpenAPI alone does not create or modify a database. Database startup
errors stop startup; there is no silent fallback to empty in-memory state.

Initialization can also run explicitly from backend:

    .\.venv\Scripts\python.exe -m app.database

This command reads the process environment; it does not load .env implicitly.
It prints the resulting database path. Repeating it is safe.
Local database files and journal/WAL/SHM sidecars are ignored by Git.

## Repository and schema

Services use the existing Repository protocol, including transaction scopes.
SQLiteRepository is the production/local implementation; InMemoryRepository
remains an isolated test implementation. No route or domain service contains SQL.
The access engine still takes domain records and is completely storage-independent.

| Table | Contents |
| --- | --- |
| schema_migrations | Applied schema versions and UTC application timestamps |
| people | Residents, guests, contractors, managers, responders, business visitors |
| zones | Zone types, floors, restriction flags |
| businesses | Business activity and destination zones |
| work_orders | Contractor IDs and work-order state |
| appointments | Visitor details, business/destination, windows, status, timestamps |
| permissions | Unique permission IDs, person/appointment/business references, scope and validity |
| emergencies | Incident identity, affected zones, assignments, status, timestamps |
| emergency_events | Ordered audit events keyed by incident and sequence |
| pending_actions | Exact agent proposal arguments, actor, creation time, expiry |
| ring_accounts | Environment-scoped Ring identity, encrypted tokens, owner/link state, UTC expiry |
| ring_events | Signed webhook inbox, raw JSON, normalized signals, deduplication IDs, processing outcome |

Migration 2 adds the Ring tables and unique delivery/event identity indexes without
changing migration 1. Ring is optional and startup makes no Ring network requests.
See [Ring configuration and deployment boundaries](ring-integration.md), including
the independent token encryption key required before account linking.

Rows have primary/unique keys and validated JSON payloads using the existing
Pydantic models. Key references use SQL foreign keys: work-order contractors,
appointment business/destination, permission person/business/appointment, and
emergency event incident. Embedded zone-ID arrays remain JSON and are validated
by existing services. Appointment visitor IDs intentionally have no person foreign
key because scheduling does not register a visitor; check-in does.

Model JSON preserves timezone-aware UTC strings, and reads reconstruct and
validate domain models. No SQLite datetime converter strips timezone information.
Lists have explicit ordering: entity IDs, permission insertion sequence,
work-order insertion order, and incident event sequence.

Emergency history is stored only in emergency_events and reconstructed on reads.
Incident updates reject rewriting/removing existing audit events and append only
new ones. The incident update and appended events commit together. This is not
cryptographic protection against direct database edits.

## Initialization and seeding

Versioned migrations are defined in app/database.py. Version 1 creates the schema
inside a transaction and records its version only if all statements succeed.
Future schema changes must add a numbered migration rather than edit an applied
migration. Unsupported/newer or noncontiguous version histories fail explicitly.
There is no automatic downgrade or destructive schema reset.

Seeding runs in a separate transaction after migrations. It reuses the existing
demo-data definition and inserts missing IDs with ON CONFLICT DO NOTHING.
Existing names, permissions, work-order activity, appointments, and incidents are
never reset. Multiple initializations and concurrent starts do not duplicate IDs.

Seeded records include resident-1, guest-1, contractor-1, manager-1, responder-1,
plumber-1; floor-5, lobby, office-106, machine-room, utility-room; Atlas Dental;
and the elevator/plumbing work orders. No permissions, appointments, active
emergencies, or agent proposals are seeded.

This introduces persistence for newly started servers. Old process-local state
cannot be recovered automatically after the old process has stopped. Existing
SQLite files using another schema are not an import source.

## Transactions and confirmation safety

Every service transaction uses BEGIN IMMEDIATE, reserving SQLite's write lock
before validation reads. This prevents two connections from both validating and
committing a duplicate invitation, appointment, check-in, or incident transition.
This conservative policy also serializes read-only repository transactions.
Connections are local to the current transaction/thread and closed afterward;
nested scopes use savepoints. SQLite uses WAL, foreign keys, FULL synchronous
mode, and a five-second busy timeout.

Guest registration plus permission, check-in's person/permission/appointment, and
incident state plus events each roll back together if persistence fails.
No database lock is held during a Bedrock network call.

PendingActionStore uses repository operations instead of its own mutable map.
Actor matching, five-minute expiry, deduplication, and the 1,000-action bound
remain unchanged. Expired proposals are cleaned on proposal creation.
Consumption deletes and commits the proposal before the domain service is called,
including expiry and later service failures. Concurrent/replayed confirmations
cannot execute it again, even across repository recreation. A crash after
consumption but before the domain commit can lose the requested action: this
preserves at-most-once execution, not guaranteed or exactly-once delivery.
Consumed/expired action records are not retained as an execution audit log.

## Verification

From backend:

    .\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider
    .\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider --repository-backend=sqlite
    .\.venv\Scripts\python.exe -m pip check

The default suite retains the existing memory fixtures and adds persistence
tests using isolated temporary files. The SQLite option runs the existing shared
repository fixture against temporary SQLite databases as well. Deliberately
constructed in-memory unit fixtures remain unchanged.

Persistence tests cover repository and real subprocess restart, UTC round trips,
all stored entities, idempotent seeds, duplicate IDs, reload access decisions,
pending confirmations, multi-connection races, forced write failures, nested
rollback, and schema initialization. Test databases never use the development DB.

## Remaining limits and backups

Use a local disk and back up the database. For a simple manual backup, stop all
backend processes cleanly before copying the database and any remaining WAL
sidecar. Do not copy only the main file while the server is writing: recent
commits may still be in WAL. SQLite's backup API is an alternative for a consistent
online backup. Backup scheduling, retention, and restore tooling are not added.

SQLite permits one writer at a time; long transactions can cause busy-timeout
errors. This is appropriate for the local hackathon, not a high-write distributed
deployment. Workers must use the same absolute file to share state.

Authentication, tenant isolation, encryption at rest, and tamper-proof auditing
remain absent. Filesystem permissions protect the database. File loss/corruption,
disk exhaustion, and unauthorized direct edits still require operational handling.
No automatic downgrade, production import workflow, or schema rollback tool is
provided. AI remains unable to authorize access.
