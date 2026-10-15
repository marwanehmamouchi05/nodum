"""Operational records, separate from physical access and configuration."""
from copy import deepcopy
from heapq import nlargest
import json


def activity_key(record):
    return record["at"], record["id"]


class MemoryManagerRepository:
    def page_operation_activity(self, scope_ids, *, before=None, limit=101):
        if not 1 <= limit <= 101:
            raise ValueError("Activity candidate limit must be 1 to 101")
        scopes = set(scope_ids)
        with self._lock:
            records = (r for (kind, _), r in self._operational_records.items()
                if kind == "operation_activity" and r["scope_id"] in scopes
                and (b := self.get_resource_binding(kind, r["id"])) and b.scope_id == r["scope_id"]
                and (before is None or activity_key(r) < before))
            return deepcopy(nlargest(limit, records, key=activity_key))

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
    def page_operation_activity(self, scope_ids, *, before=None, limit=101):
        if not 1 <= limit <= 101:
            raise ValueError("Activity candidate limit must be 1 to 101")
        # One indexed top-N per authorized scope, then bounded merge. Foreign
        # histories cannot fill the page. No OFFSET or full-history JSON loading.
        with self.database.transaction() as connection:
            def candidates():
                for scope_id in sorted(set(scope_ids)):
                    cursor_sql = " AND (json_extract(o.data, '$.at'), o.id) < (?, ?)" if before else ""
                    params = [scope_id, *(before or ()), limit]
                    rows = connection.execute(
                        "SELECT o.data FROM product_operations o "
                        "JOIN application_resource_bindings b ON b.resource_type=o.kind "
                        "AND b.resource_id=o.id AND b.scope_id=o.scope_id "
                        "WHERE o.scope_id=? AND o.kind='operation_activity'" + cursor_sql +
                        " ORDER BY json_extract(o.data, '$.at') DESC, o.id DESC LIMIT ?", params)
                    yield from (json.loads(row[0]) for row in rows)
            return nlargest(limit, candidates(), key=activity_key)

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
