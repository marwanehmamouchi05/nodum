"""Local SQLite configuration, versioned initialization, and transaction scopes."""
from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
from threading import local
from time import monotonic, sleep


DEFAULT_DATABASE_URL = "sqlite:///./nodum.db"
BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]

# Explicit migrations, committed with their version markers. Do not edit applied
# migrations: add a new numbered entry when the schema changes.
MIGRATIONS = (
    (1, (
        "CREATE TABLE people (id TEXT PRIMARY KEY NOT NULL, data TEXT NOT NULL CHECK(json_valid(data)))",
        "CREATE TABLE zones (id TEXT PRIMARY KEY NOT NULL, data TEXT NOT NULL CHECK(json_valid(data)))",
        "CREATE TABLE businesses (id TEXT PRIMARY KEY NOT NULL, data TEXT NOT NULL CHECK(json_valid(data)))",
        """CREATE TABLE work_orders (
            id TEXT PRIMARY KEY NOT NULL, contractor_id TEXT NOT NULL REFERENCES people(id),
            data TEXT NOT NULL CHECK(json_valid(data)))""",
        """CREATE TABLE appointments (
            id TEXT PRIMARY KEY NOT NULL, business_id TEXT NOT NULL REFERENCES businesses(id),
            destination_zone_id TEXT NOT NULL REFERENCES zones(id),
            data TEXT NOT NULL CHECK(json_valid(data)))""",
        """CREATE TABLE permissions (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            id TEXT NOT NULL UNIQUE, person_id TEXT NOT NULL REFERENCES people(id),
            appointment_id TEXT REFERENCES appointments(id),
            business_id TEXT REFERENCES businesses(id),
            data TEXT NOT NULL CHECK(json_valid(data)))""",
        "CREATE INDEX permissions_person ON permissions(person_id)",
        "CREATE TABLE emergencies (id TEXT PRIMARY KEY NOT NULL, data TEXT NOT NULL CHECK(json_valid(data)))",
        """CREATE TABLE emergency_events (
            emergency_id TEXT NOT NULL REFERENCES emergencies(id),
            sequence INTEGER NOT NULL CHECK(sequence >= 0),
            data TEXT NOT NULL CHECK(json_valid(data)),
            PRIMARY KEY (emergency_id, sequence))""",
        "CREATE TABLE pending_actions (id TEXT PRIMARY KEY NOT NULL, data TEXT NOT NULL CHECK(json_valid(data)))",
    )),
    (2, (
        "CREATE TABLE ring_accounts (id TEXT PRIMARY KEY NOT NULL, data TEXT NOT NULL CHECK(json_valid(data)))",
        "CREATE TABLE ring_events (id TEXT PRIMARY KEY NOT NULL, data TEXT NOT NULL CHECK(json_valid(data)))",
        "CREATE UNIQUE INDEX ring_request_identity ON ring_events "
        "(json_extract(data, '$.environment'), json_extract(data, '$.account_id'), json_extract(data, '$.request_id'))",
        "CREATE UNIQUE INDEX ring_event_identity ON ring_events "
        "(json_extract(data, '$.environment'), json_extract(data, '$.account_id'), json_extract(data, '$.event_id'))",
    )),
    (3, (
        "CREATE TABLE building_integrations (id TEXT PRIMARY KEY NOT NULL, data TEXT NOT NULL CHECK(json_valid(data)))",
        "CREATE TABLE building_devices (id TEXT PRIMARY KEY NOT NULL, data TEXT NOT NULL CHECK(json_valid(data)))",
        "CREATE TABLE device_zone_mappings (id TEXT PRIMARY KEY NOT NULL, data TEXT NOT NULL CHECK(json_valid(data)))",
        "CREATE TABLE device_states (id TEXT PRIMARY KEY NOT NULL, data TEXT NOT NULL CHECK(json_valid(data)))",
        "CREATE TABLE credentials (id TEXT PRIMARY KEY NOT NULL, data TEXT NOT NULL CHECK(json_valid(data)))",
        "CREATE TABLE credential_events (id TEXT PRIMARY KEY NOT NULL, data TEXT NOT NULL CHECK(json_valid(data)))",
        "CREATE TABLE actuator_events (id TEXT PRIMARY KEY NOT NULL, data TEXT NOT NULL CHECK(json_valid(data)))",
        "CREATE TABLE journeys (id TEXT PRIMARY KEY NOT NULL, data TEXT NOT NULL CHECK(json_valid(data)))",
        "CREATE TABLE journey_transitions (id TEXT PRIMARY KEY NOT NULL, data TEXT NOT NULL CHECK(json_valid(data)))",
        "CREATE UNIQUE INDEX credential_fingerprint ON credentials (json_extract(data, '$.fingerprint'))",
        "CREATE INDEX transition_journey ON journey_transitions (json_extract(data, '$.journey_id'))",
    )),
    (4, (
        "CREATE TABLE auth_users (id TEXT PRIMARY KEY NOT NULL, data TEXT NOT NULL CHECK(json_valid(data)))",
        "CREATE UNIQUE INDEX auth_username ON auth_users (json_extract(data, '$.username'))",
        "CREATE UNIQUE INDEX auth_person ON auth_users (json_extract(data, '$.person_id'))",
        "CREATE TABLE auth_sessions (id TEXT PRIMARY KEY NOT NULL, data TEXT NOT NULL CHECK(json_valid(data)))",
        "CREATE TABLE auth_throttles (id TEXT PRIMARY KEY NOT NULL, data TEXT NOT NULL CHECK(json_valid(data)))",
        "CREATE INDEX ring_owner_user ON ring_accounts (json_extract(data, '$.owner_user_id'))",
    )),
)


def database_path(database_url: str | None = None) -> Path:
    url = database_url if database_url is not None else os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL
    if not url.startswith("sqlite:///"):
        raise ValueError("DATABASE_URL must be a file-backed sqlite:/// URL")
    value = url[len("sqlite:///"):]
    if not value or value == ":memory:" or "?" in value or "#" in value:
        raise ValueError("DATABASE_URL must name a SQLite file without URL options")
    path = Path(value).expanduser()
    # Stable across launches from the repository root or the backend directory.
    return (path if path.is_absolute() else BACKEND_DIRECTORY / path).resolve()


class SQLiteDatabase:
    def __init__(self, database_url: str | None = None):
        self.path = database_path(database_url)
        self._local = local()

    def _connect(self, timeout_ms=5000):
        connection = sqlite3.connect(self.path, timeout=timeout_ms / 1000, isolation_level=None)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(f"PRAGMA busy_timeout = {int(timeout_ms)}")
            connection.execute("PRAGMA synchronous = FULL")
        except BaseException:
            connection.close()
            raise
        return connection

    @property
    def connection(self):
        connection = getattr(self._local, "connection", None)
        if connection is None:
            raise RuntimeError("Database operation requires a transaction")
        return connection

    @contextmanager
    def transaction(self, timeout_ms=5000):
        """Serialize validation+writes across threads/processes; nest via savepoints."""
        if getattr(self._local, "connection", None) is not None:
            depth = self._local.depth + 1
            self._local.depth = depth
            savepoint = f"nodum_{depth}"
            connection = self.connection
            connection.execute(f"SAVEPOINT {savepoint}")
            try:
                yield connection
            except BaseException:
                connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                raise
            finally:
                connection.execute(f"RELEASE SAVEPOINT {savepoint}")
                self._local.depth -= 1
            return
        connection = self._connect(timeout_ms)
        self._local.connection = connection
        self._local.depth = 0
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            self._local.connection = None
            connection.close()

    def _enable_wal(self):
        # Concurrent first opens can race while changing journal mode. SQLite may
        # return BUSY immediately here despite busy_timeout; retry only contention,
        # closing the connection before waiting so neither opener holds a lock.
        deadline = monotonic() + 5
        while True:
            connection = None
            try:
                connection = self._connect()
                mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
                if mode.lower() != "wal":
                    raise RuntimeError("SQLite WAL mode could not be enabled")
                return
            except sqlite3.OperationalError as exc:
                code = getattr(exc, "sqlite_errorcode", 0) & 0xFF
                if code not in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED} or monotonic() >= deadline:
                    raise
            finally:
                if connection is not None:
                    connection.close()
            sleep(0.05)

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._enable_wal()
        with self.transaction() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
            versions = [row[0] for row in connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version")]
            known = [version for version, _ in MIGRATIONS]
            if versions != known[:len(versions)]:
                raise RuntimeError("Unsupported or inconsistent database schema version")
            for version, statements in MIGRATIONS:
                if version not in versions:
                    for statement in statements:
                        connection.execute(statement)
                    connection.execute(
                        "INSERT INTO schema_migrations VALUES (?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
                        (version,),
                    )


if __name__ == "__main__":
    from app.sqlite_repository import SQLiteRepository

    repository = SQLiteRepository()
    repository.initialize()
    print(f"Nodum database initialized: {repository.database.path}")
