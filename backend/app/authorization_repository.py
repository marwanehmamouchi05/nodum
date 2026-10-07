"""Storage for explicit scope/authority records; never seed legacy ownership."""
from app.models.authorization import Scope, RoleAssignment, ResourceBinding


class MemoryAuthorizationRepository:
    def get_scope(self, identifier):
        with self._lock:
            record = self._scopes.get(identifier)
            return record.model_copy(deep=True) if record else None

    def list_scopes(self):
        with self._lock:
            return [r.model_copy(deep=True) for _, r in sorted(self._scopes.items())]

    def save_scope(self, record):
        with self._lock:
            self._scopes[record.id] = Scope.model_validate(record.model_dump())

    def get_role_assignment(self, identifier):
        with self._lock:
            record = self._role_assignments.get(identifier)
            return record.model_copy(deep=True) if record else None

    def list_role_assignments(self):
        with self._lock:
            return [r.model_copy(deep=True) for _, r in sorted(self._role_assignments.items())]

    def save_role_assignment(self, record):
        with self._lock:
            self._role_assignments[record.id] = RoleAssignment.model_validate(record.model_dump())

    def get_resource_binding(self, resource_type, resource_id):
        with self._lock:
            record = self._resource_bindings.get((resource_type, resource_id))
            return record.model_copy(deep=True) if record else None

    def save_resource_binding(self, record):
        with self._lock:
            self._resource_bindings[(record.resource_type, record.resource_id)] = ResourceBinding.model_validate(record.model_dump())


class SQLiteAuthorizationRepository:
    def get_scope(self, identifier):
        return self._get("application_scopes", identifier, Scope)

    def list_scopes(self):
        return self._list("application_scopes", Scope)

    def save_scope(self, record):
        record = Scope.model_validate(record.model_dump())
        with self.database.transaction() as connection:
            connection.execute("INSERT INTO application_scopes (id, parent_id, data) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET parent_id=excluded.parent_id, data=excluded.data",
                (record.id, record.parent_id, record.model_dump_json()))

    def get_role_assignment(self, identifier):
        return self._get("application_role_assignments", identifier, RoleAssignment)

    def list_role_assignments(self):
        return self._list("application_role_assignments", RoleAssignment)

    def save_role_assignment(self, record):
        record = RoleAssignment.model_validate(record.model_dump())
        with self.database.transaction() as connection:
            connection.execute("INSERT INTO application_role_assignments (id, user_id, scope_id, data) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET user_id=excluded.user_id, scope_id=excluded.scope_id, data=excluded.data",
                (record.id, record.user_id, record.scope_id, record.model_dump_json()))

    def get_resource_binding(self, resource_type, resource_id):
        with self.database.transaction() as connection:
            row = connection.execute("SELECT data FROM application_resource_bindings WHERE resource_type=? AND resource_id=?",
                                     (resource_type, resource_id)).fetchone()
            return ResourceBinding.model_validate_json(row[0]) if row else None

    def save_resource_binding(self, record):
        record = ResourceBinding.model_validate(record.model_dump())
        with self.database.transaction() as connection:
            connection.execute("INSERT INTO application_resource_bindings VALUES (?, ?, ?, ?) "
                "ON CONFLICT(resource_type, resource_id) DO UPDATE SET scope_id=excluded.scope_id, data=excluded.data",
                (record.resource_type, record.resource_id, record.scope_id, record.model_dump_json()))
