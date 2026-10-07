"""Private persistence primitives; application callers use StructureService."""
from app.models.structure import StructureNode, Affiliation


class MemoryStructureRepository:
    def get_structure_node(self, identifier):
        with self._lock:
            record = self._structure_nodes.get(identifier)
            return record.model_copy(deep=True) if record else None

    def list_structure_nodes(self):
        with self._lock:
            return [r.model_copy(deep=True) for _, r in sorted(self._structure_nodes.items())]

    def save_structure_node(self, record):
        with self._lock:
            self._structure_nodes[record.id] = StructureNode.model_validate(record.model_dump())

    def list_affiliations(self):
        with self._lock:
            return [r.model_copy(deep=True) for _, r in sorted(self._affiliations.items())]

    def save_affiliation(self, record):
        with self._lock:
            self._affiliations[record.id] = Affiliation.model_validate(record.model_dump())


class SQLiteStructureRepository:
    def get_structure_node(self, identifier):
        return self._get("product_structure", identifier, StructureNode)

    def list_structure_nodes(self):
        return self._list("product_structure", StructureNode)

    def save_structure_node(self, record):
        with self.database.transaction() as connection:
            connection.execute("INSERT INTO product_structure VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET parent_id=excluded.parent_id, scope_id=excluded.scope_id, data=excluded.data",
                (record.id, record.parent_id, record.organization_id, record.building_id,
                 record.scope_id, record.integration_id, record.model_dump_json()))

    def list_affiliations(self):
        return self._list("product_affiliations", Affiliation)

    def save_affiliation(self, record):
        with self.database.transaction() as connection:
            connection.execute("INSERT INTO product_affiliations VALUES (?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                (record.id, record.user_id, record.target_id, record.model_dump_json()))
