"""Configuration-only storage; never persists submitted login credentials."""
from copy import deepcopy


class MemoryAdminRepository:
    def get_admin_settings(self, identifier):
        with self._lock:
            return deepcopy(self._admin_settings.get(identifier))

    def save_admin_settings(self, identifier, scope_id, data):
        with self._lock:
            self._admin_settings[identifier] = deepcopy(data)

    def list_configuration_audit(self):
        with self._lock:
            return deepcopy(list(self._configuration_audit.values()))

    def append_configuration_audit(self, record):
        with self._lock:
            self._configuration_audit[record["id"]] = deepcopy(record)

    def save_configured_person(self, person):
        with self._lock:
            self._people[person.id] = person.model_copy(deep=True)


class SQLiteAdminRepository:
    def get_admin_settings(self, identifier):
        import json
        with self.database.transaction() as connection:
            row = connection.execute("SELECT data FROM product_admin_settings WHERE id=?", (identifier,)).fetchone()
            return json.loads(row[0]) if row else None

    def save_admin_settings(self, identifier, scope_id, data):
        import json
        with self.database.transaction() as connection:
            connection.execute("INSERT INTO product_admin_settings VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data", (identifier, scope_id, json.dumps(data)))

    def list_configuration_audit(self):
        import json
        with self.database.transaction() as connection:
            return [json.loads(row[0]) for row in connection.execute("SELECT data FROM product_configuration_audit ORDER BY id")]

    def append_configuration_audit(self, record):
        import json
        with self.database.transaction() as connection:
            connection.execute("INSERT INTO product_configuration_audit VALUES (?, ?, ?)",
                (record["id"], record["scope_id"], json.dumps(record)))

    def save_configured_person(self, person):
        with self.database.transaction() as connection:
            connection.execute("INSERT INTO people VALUES (?, ?)", (person.id, person.model_dump_json()))
