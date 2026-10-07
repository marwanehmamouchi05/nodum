"""Opt-in synthetic reference topology. Never imported by startup/seeding code."""
from app.models.structure import StructureNode, NodeKind as K, ConnectionPath
from app.models.authorization import Permission as P
from app.services.errors import DomainError


def reference_nodes(organization_id):
    prefix = organization_id + ":reference:"
    building = prefix + "building"
    nodes = [StructureNode(id=building, name="Mixed-use reference building", kind=K.BUILDING,
        organization_id=organization_id, building_id=building, parent_id=organization_id,
        scope_id=building, demo=True)]

    def add(suffix, name, kind, parent, **fields):
        identifier = prefix + suffix
        scope = parent if kind in {K.DEVICE, K.INTEGRATION} else identifier
        nodes.append(StructureNode(id=identifier, name=name, kind=kind,
            organization_id=organization_id, building_id=building, parent_id=parent,
            scope_id=scope, demo=True, **fields))
        return identifier

    for order, suffix, name, places in (
        (-1, "underground", "Underground", ["Elevator machine room", "Water pumps", "Electrical generators", "Maintenance areas"]),
        (0, "ground", "Ground Floor", ["Lobby", "Main entrance", "Elevator", "Apartment G1", "Apartment G2"]),
        (1, "floor1", "Floor 1", ["Apartment 101", "Apartment 102", "Apartment 103", "Apartment 104"]),
        (2, "floor2", "Floor 2", ["Business X", "Business Y"]),
        (3, "floor3", "Floor 3", ["Apartment 301", "Apartment 302", "Apartment 303", "Apartment 304"]),
        (4, "roof", "Roof", ["Shared roof area"]),
    ):
        floor = add(suffix, name, K.FLOOR, building, floor_order=order)
        for index, place in enumerate(places):
            location = add(f"{suffix}-location-{index}", place + " zone", K.LOCATION, floor,
                common=place in {"Lobby", "Main entrance", "Elevator", "Shared roof area"})
            if place.startswith("Apartment"):
                add(place.lower().replace(" ", "-"), place, K.UNIT, location)
            elif place.startswith("Business"):
                add(place.lower().replace(" ", "-"), place, K.BUSINESS, location)
            elif suffix == "underground":
                add(f"{suffix}-room-{index}", place, K.ROOM, location)
    integration = add("simulation", "Reference simulation adapter", K.INTEGRATION, building,
        connection_path=ConnectionPath.SIMULATION)
    for suffix, label, parent_suffix, device_type in (
        ("lobby-camera", "Demo lobby camera", "ground-location-0", "camera"),
        ("entrance-lock", "Demo entrance lock", "ground-location-1", "lock"),
        ("business-x-camera", "Demo Business X camera", "business-x", "camera"),
        ("machine-room-sensor", "Demo machine room sensor", "underground-room-0", "sensor"),
    ):
        add(suffix, label, K.DEVICE, prefix + parent_suffix,
            integration_id=integration, connection_path=ConnectionPath.SIMULATION,
            device_type=device_type)  # No capabilities asserted; no live adapter.
    return nodes


def load_reference_building(service, organization_id):
    """Explicit call against an already provisioned DEMO organization only.

    Preflight all identities before writes (memory transactions do not roll back).
    Replay validates exact fixture equality instead of overwriting configuration.
    No accounts, passwords, physical grants, or application grants are seeded.
    """
    with service.repo.transaction():
        service.auth.require(P.STRUCTURE_CONFIGURE, "structure", organization_id)
        service.auth.require(P.HARDWARE_CONFIGURE, "structure", organization_id)
        organization = service.repo.get_structure_node(organization_id)
        if not organization or organization.kind != K.ORGANIZATION or not organization.demo:
            raise DomainError(409, "Reference seed requires an explicit demo organization")
        nodes = reference_nodes(organization_id)
        for node in nodes:
            existing = service.repo.get_structure_node(node.id)
            if existing and existing != node:
                raise DomainError(409, "Reference identity has existing configuration")
            if not existing and (service.repo.get_scope(node.id)
                    or service.repo.get_resource_binding("structure", node.id)):
                raise DomainError(409, "Reference identity has existing ownership")
        for node in nodes:
            service.save(node)
        return service.catalog()
