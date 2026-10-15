"""Three populated buildings: actual HTTP sessions, guessed IDs and unchanged foreign records."""
from datetime import timedelta
import json

import pytest

from app.models.auth import NodumUser
from app.models.authorization import Permission as P, Role, RoleAssignment
from app.models.manager import MaintenanceInput, VisitorInput
from app.models.structure import Affiliation
from app.services.authorization import ROLE_CEILINGS
from app.services.manager import ManagerService
from app.services.reference_building import load_reference_building
from test_authorization import headers
from test_structure import structure, user_service  # noqa: F401
from conftest import NOW


@pytest.fixture
def buildings(structure):
    repo = structure.repo
    repo.save_auth_user(NodumUser(id="third-manager", username="third-manager", person_id="plumber-1",
                                 password_hash="fixture-no-password", created_at=NOW))
    result = []
    for organization, user in (("demo-org", "resident"), ("tenant-b", "business"), ("tenant-c", "third-manager")):
        if organization != "demo-org":
            structure.bootstrap_organization(organization, "Isolated tenant " + organization, demo=True)
            repo.save_role_assignment(RoleAssignment(id=organization + "-setup", user_id="admin", role=Role.ADMIN,
                scope_id=organization, permissions=[P.STRUCTURE_CONFIGURE, P.HARDWARE_CONFIGURE]))
            load_reference_building(structure, organization)
        prefix = organization + ":reference:"
        scoped = user_service(structure, user, prefix + "building", Role.MANAGER,
                              list(ROLE_CEILINGS[Role.MANAGER]))
        manager = ManagerService(scoped.auth)
        maintenance = manager.create("maintenance", MaintenanceInput(location_id=prefix + "apartment-101",
            title="Isolated tenant repair", description="Synthetic issue"))
        visit = manager.invite(VisitorInput(location_id=prefix + "apartment-101", name="Synthetic visitor",
            starts_at=NOW - timedelta(minutes=1), ends_at=NOW + timedelta(hours=1)))
        result.append((user, prefix, maintenance, visit))
    return result


@pytest.mark.parametrize("index", [0, 1, 2])
def test_three_building_http_matrix(api, repo, buildings, index):
    user, own_prefix, own_request, own_visit = buildings[index]
    session = headers(repo, user)
    status, snapshot = api("GET", "/manager/snapshot", headers=session)
    assert status == 200
    assert [r["id"] for r in snapshot["maintenance"]] == [own_request["id"]]
    assert [r["id"] for r in snapshot["visitors"]] == [own_visit["id"]]
    serialized = json.dumps(snapshot)
    for other_user, prefix, request, visit in buildings:
        if other_user == user:
            continue
        assert prefix not in serialized and request["id"] not in serialized and visit["id"] not in serialized
        before = (repo.get_operational_record("maintenance", request["id"]),
                  repo.get_operational_record("visitor", visit["id"]), repo.list_actuator_events())
        assert api("PATCH", "/manager/maintenance/" + request["id"], {"status": "resolved"}, headers=session)[0] == 403
        assert api("POST", "/manager/visitors/" + visit["id"] + "/arrive", headers=session)[0] == 403
        assert api("POST", "/manager/maintenance", {"location_id": prefix + "apartment-101",
            "title": "Foreign write", "description": "Denied"}, headers=session)[0] == 403
        assert api("GET", "/structure/devices/" + prefix + "machine-room-sensor/context", headers=session)[0] == 403
        assert before == (repo.get_operational_record("maintenance", request["id"]),
                          repo.get_operational_record("visitor", visit["id"]), repo.list_actuator_events())
    assert own_prefix in serialized


def test_resident_cannot_promote_to_manager_or_read_foreign_device(api, repo, structure, buildings):
    user, prefix, _, _ = buildings[0]
    user_service(structure, user, prefix + "apartment-101", Role.RESIDENT, list(P))
    repo.save_affiliation(Affiliation(id="configured-resident-home", user_id=user,
                                    role=Role.RESIDENT, target_id=prefix + "apartment-101"))
    session = headers(repo, user)
    assert api("GET", "/manager/snapshot", headers=session)[0] == 403
    other_device = buildings[1][1] + "machine-room-sensor"
    assert api("GET", "/structure/nodes/" + other_device, headers=session)[0] == 403
