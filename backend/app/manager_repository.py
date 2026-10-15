"""Operational records, separate from physical access and configuration."""
from copy import deepcopy
import json


class MemoryManagerRepository:
    def get_operational_record(self, kind, identifier):
        with self._lock:
            return deepcopy(self._operational_records.get((kind, identifier)))

    def list_operational_records(self, kind):
        with self._lock:
            return deepcopy([r for (k, _), r in self._operational_records.items() if k == kind])

    def save_operational_record(self, kind, record):
        with self._lock:
            self._operational_records[kind, record["id"]] = deepcopy(record)


class SQLiteManagerRepository:
    def get_operational_record(self, kind, identifier):
        with self.database.transaction() as connection:
            row = connection.execute('SELECT data FROM product_operations WHERE kind=? AND id=?',
                                     (kind, identifier)).fetchone()
            return json.loads(row[0]) if row else None

    def list_operational_records(self, kind):
        with self.database.transaction() as connection:
            return [json.loads(r[0]) for r in connection.execute(
                "SELECT data FROM product_operations WHERE kind=? ORDER BY id", (kind,))]

    def save_operational_record(self, kind, record):
        with self.database.transaction() as connection:
            connection.execute("INSERT INTO product_operations VALUES (?, ?, ?, ?) "
                "ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",
                (kind, record["id"], record["scope_id"], json.dumps(record)))
