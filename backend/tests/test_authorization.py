"""Application authorization matrix, real sessions/ASGI and isolated databases."""
from datetime import timedelta
import sqlite3
import pytest
from app.auth_config import AuthSettings
from app.config import AppSettings, ConfigurationError, validate_startup
from app.models.auth import NodumUser
from app.models.authorization import Principal, Role, Permission as P, Scope, ScopeKind, RoleAssignment, ResourceBinding
from app.models.building import Zone, ZoneType
from app.models.business import Business, AppointmentCreateInput
from app.models.access import AccessPermission
from app.services.auth import AuthService, csrf_token
from app.services.authorization import AuthorizationService
from app.services.scoped_repository import ScopedRepository
from app.services.agent_actions import PendingActionStore
from app.services.agent_tools import AgentTools, confirm_action
from app.services.appointments import create_appointment
from app.services.errors import DomainError
from app.sqlite_repository import SQLiteRepository
from app.database import SQLiteDatabase, MIGRATIONS
from app.services.ring_simulation import SCENARIOS, RingSimulationService
from conftest import NOW


@pytest.fixture
def platform(repo, api, monkeypatch):
    monkeypatch.setenv("NODUM_AUTHORIZATION_MODE", "scoped")
    monkeypatch.setenv("AUTH_PUBLIC_ORIGIN", "http://test")
    monkeypatch.setenv("APP_ENV", "development")
    for identifier, person in (("manager", "manager-1"), ("resident", "resident-1"),
                                ("other", "guest-1"), ("business-x", "contractor-1"), ("business-y", "plumber-1")):
        repo.save_auth_user(NodumUser(id=identifier, username=identifier, person_id=person,
            password_hash="test-fixture-no-login-password", created_at=NOW))
    service = AuthorizationService(repo, Principal(user_id="manager", person_id="manager-1"), NOW)
    for scope in (
        Scope(id="org-a", organization_id="org-a", kind=ScopeKind.ORGANIZATION),
        Scope(id="org-b", organization_id="org-b", kind=ScopeKind.ORGANIZATION),
        Scope(id="building-a", organization_id="org-a", kind=ScopeKind.BUILDING, parent_id="org-a"),
        Scope(id="building-b", organization_id="org-b", kind=ScopeKind.BUILDING, parent_id="org-b"),
        Scope(id="business-x", organization_id="org-a", kind=ScopeKind.BUSINESS, parent_id="building-a"),
        Scope(id="business-y", organization_id="org-a", kind=ScopeKind.BUSINESS, parent_id="building-a"),
        Scope(id="resident-home", organization_id="org-a", kind=ScopeKind.PERSON, parent_id="building-a"),
        Scope(id="other-home", organization_id="org-a", kind=ScopeKind.PERSON, parent_id="building-a"),
        Scope(id="common", organization_id="org-a", kind=ScopeKind.LOCATION, parent_id="building-a"),
    ):
        service.save_scope(scope)
    bindings = {"person": {"manager-1": "building-a", "resident-1": "resident-home",
                "guest-1": "other-home", "contractor-1": "business-x", "plumber-1": "business-y"},
        "location": {"lobby": "common", "floor-5": "common", "machine-room": "building-a",
                     "utility-room": "building-a", "office-106": "business-x"},
        "business": {"atlas-dental": "business-x"},
        "simulation": {"ring": "building-a"}}
    for kind, records in bindings.items():
        for identifier, scope in records.items():
            bind(repo, kind, identifier, scope)
    # Explicit second business fixture in isolated storage only.
    zone = Zone(id="office-y", name="Private Business Y", zone_type=ZoneType.BUSINESS, floor=2)
    business = Business(id="business-y", name="Business Y", destination_zone_ids=[zone.id])
    if isinstance(repo, SQLiteRepository):
        with repo.database.transaction() as connection:
            connection.execute("INSERT INTO zones VALUES (?, ?)", (zone.id, zone.model_dump_json()))
            connection.execute("INSERT INTO businesses VALUES (?, ?)", (business.id, business.model_dump_json()))
    else:
        repo._zones[zone.id] = zone
        repo._businesses[business.id] = business
    bind(repo, "location", zone.id, "business-y")
    bind(repo, "business", business.id, "business-y")
    return repo


def bind(repo, kind, identifier, scope):
    repo.save_resource_binding(ResourceBinding(resource_type=kind, resource_id=identifier, scope_id=scope))


def grant(repo, user, role, scope, permissions, identifier=None):
    assignment = RoleAssignment(id=identifier or f"{user}-{role.value}-{scope}", user_id=user,
        role=role, scope_id=scope, permissions=permissions)
    repo.save_role_assignment(assignment)
    return assignment


def authority(repo, user="manager", now=NOW):
    return AuthorizationService(repo, Principal(user_id=user, person_id=repo.get_auth_user(user).person_id), now)


def headers(repo, user="manager"):
    cookie, _ = AuthService(repo, AuthSettings("http://test")).issue(NOW, user)
    return [(b"cookie", f"nodum_session={cookie}".encode()),
            (b"x-csrf-token", csrf_token(cookie).encode()), (b"origin", b"http://test")]


@pytest.mark.parametrize("role,permission,allowed", [
    (Role.OWNER, P.OWNERSHIP_MANAGE, True), (Role.OWNER, P.PEOPLE_READ, False),
    (Role.OWNER, P.AUTHORIZATION_MANAGE, False), (Role.OWNER, P.CAMERA_VIEW, False),
    (Role.ADMIN, P.AUTHORIZATION_MANAGE, True), (Role.ADMIN, P.HARDWARE_CONFIGURE, True),
    (Role.ADMIN, P.PEOPLE_READ, False), (Role.ADMIN, P.CAMERA_VIEW, False),
    (Role.ADMIN, P.RING_READ, False), (Role.ADMIN, P.INCIDENTS_READ, False),
    (Role.ADMIN, P.ACTIVITY_READ, False), (Role.ADMIN, P.ACCESS_CHECK, False),
    (Role.MANAGER, P.PEOPLE_READ, True), (Role.MANAGER, P.VISITORS_INVITE, True),
    (Role.MANAGER, P.AUTHORIZATION_MANAGE, False), (Role.MANAGER, P.HARDWARE_CONFIGURE, True),
    (Role.SECURITY, P.INCIDENTS_MANAGE, True), (Role.SECURITY, P.AUTHORIZATION_MANAGE, False),
    (Role.MAINTENANCE, P.MAINTENANCE_READ, True), (Role.MAINTENANCE, P.PEOPLE_READ, False),
    (Role.MAINTENANCE, P.CAMERA_VIEW, False), (Role.MAINTENANCE, P.AUTHORIZATION_MANAGE, False),
    (Role.BUSINESS_ADMIN, P.VISITORS_INVITE, True), (Role.BUSINESS_ADMIN, P.PEOPLE_READ, True),
    (Role.BUSINESS_ADMIN, P.AUTHORIZATION_MANAGE, False), (Role.BUSINESS_ADMIN, P.INCIDENTS_MANAGE, False),
    (Role.BUSINESS_STAFF, P.VISITORS_READ, True), (Role.BUSINESS_STAFF, P.PEOPLE_READ, False),
    (Role.RESIDENT, P.PEOPLE_READ, True), (Role.RESIDENT, P.VISITORS_INVITE, True),
    (Role.RESIDENT, P.INCIDENTS_READ, False), (Role.RESIDENT, P.AUTHORIZATION_MANAGE, False),
])
def test_role_permission_ceiling_even_for_malformed_trusted_grant(platform, role, permission, allowed):
    grant(platform, "manager", role, "building-a", [permission])
    assert authority(platform).allowed_scope(permission, "common") is allowed


@pytest.mark.parametrize("source,target,allowed", [
    ("org-a", "org-a", True), ("org-a", "business-x", True), ("org-a", "resident-home", True),
    ("org-a", "building-b", False), ("building-a", "common", True),
    ("building-a", "org-a", False), ("building-a", "building-b", False),
    ("business-x", "business-x", True), ("business-x", "business-y", False),
    ("business-x", "resident-home", False), ("business-x", "building-a", False),
    ("resident-home", "resident-home", True), ("resident-home", "other-home", False),
    ("resident-home", "common", False), ("common", "common", True),
    ("common", "business-x", False), ("building-b", "org-a", False),
    ("building-a", "guessed-scope", False),
])
def test_typed_scope_matrix(platform, source, target, allowed):
    grant(platform, "manager", Role.MANAGER, source, [P.PEOPLE_READ])
    assert authority(platform).allowed_scope(P.PEOPLE_READ, target) is allowed


def test_role_label_and_legacy_person_role_grant_nothing(platform, api):
    grant(platform, "manager", Role.MANAGER, "building-a", [])
    assert not authority(platform).allowed(P.PEOPLE_READ, "person", "manager-1")
    status, catalog = api("GET", "/building/catalog", headers=headers(platform))
    assert status == 200 and all(not values for values in catalog.values())


def test_multi_role_union_does_not_cross_scopes(platform):
    grant(platform, "manager", Role.ADMIN, "building-a", [P.HARDWARE_CONFIGURE])
    grant(platform, "manager", Role.RESIDENT, "resident-home", [P.PEOPLE_READ])
    auth = authority(platform)
    assert auth.allowed_scope(P.HARDWARE_CONFIGURE, "business-y")
    assert auth.allowed(P.PEOPLE_READ, "person", "resident-1")
    assert not auth.allowed(P.PEOPLE_READ, "person", "guest-1")
    assert not auth.allowed_scope(P.CAMERA_VIEW, "resident-home")


@pytest.mark.parametrize("change", ["revoked", "expired", "scope_disabled", "parent_disabled", "user_disabled"])
def test_revocation_rechecked_without_rebuilding_principal(platform, change):
    assignment = grant(platform, "manager", Role.MANAGER, "building-a", [P.PEOPLE_READ])
    auth = authority(platform)
    assert auth.allowed(P.PEOPLE_READ, "person", "resident-1")
    if change == "revoked":
        platform.save_role_assignment(assignment.model_copy(update={"active": False}))
    elif change == "expired":
        platform.save_role_assignment(assignment.model_copy(update={"expires_at": NOW}))
    elif change in {"scope_disabled", "parent_disabled"}:
        scope = platform.get_scope("building-a" if change == "scope_disabled" else "org-a")
        platform.save_scope(scope.model_copy(update={"active": False}))
    else:
        user = platform.get_auth_user("manager")
        platform.save_auth_user(user.model_copy(update={"active": False}))
    assert not auth.allowed(P.PEOPLE_READ, "person", "resident-1")


def appointments_fixture(repo):
    for identifier, business, zone, scope in (("appt-x", "atlas-dental", "office-106", "business-x"),
                                            ("appt-y", "business-y", "office-y", "business-y")):
        create_appointment(repo, AppointmentCreateInput(id=identifier, visitor_id=f"visitor-{identifier}",
            visitor_name=f"Synthetic {identifier}", business_id=business, destination_zone_id=zone,
            appointment_time=NOW), NOW)
        bind(repo, "appointment", identifier, scope)


@pytest.mark.parametrize("user,scope,expected", [("business-x", "business-x", "appt-x"), ("business-y", "business-y", "appt-y")])
def test_business_list_detail_guessed_id_parity(platform, api, user, scope, expected):
    appointments_fixture(platform)
    grant(platform, user, Role.BUSINESS_ADMIN, scope, [P.VISITORS_READ, P.BUSINESSES_READ, P.PEOPLE_READ])
    h = headers(platform, user)
    status, records = api("GET", "/appointments", headers=h)
    assert status == 200 and [a["id"] for a in records] == [expected]
    assert api("GET", f"/appointments/{expected}", headers=h)[0] == 200
    other = "appt-y" if expected == "appt-x" else "appt-x"
    assert api("GET", f"/appointments/{other}", headers=h)[0] == 404
    assert api("GET", "/appointments/guessed-id", headers=h)[0] == 404
    status, catalog = api("GET", "/building/catalog", headers=h)
    assert status == 200 and len(catalog["businesses"]) == 1
    assert {p["id"] for p in catalog["people"]} == {platform.get_auth_user(user).person_id}


def test_resident_isolation_and_unbound_resources(platform, api):
    grant(platform, "resident", Role.RESIDENT, "resident-home", [P.PEOPLE_READ, P.VISITORS_READ])
    h = headers(platform, "resident")
    status, catalog = api("GET", "/building/catalog", headers=h)
    assert status == 200 and [p["id"] for p in catalog["people"]] == ["resident-1"]
    assert not authority(platform, "resident").allowed(P.PEOPLE_READ, "person", "guest-1")
    assert not authority(platform, "resident").allowed(P.PEOPLE_READ, "person", "responder-1")
    assert api("GET", "/appointments", headers=h) == (200, [])


@pytest.mark.parametrize("path,body", [
    ("/appointments", {"id": "attempt", "business_id": "business-y", "destination_zone_id": "office-y"}),
    ("/guests/invite", {"resident_id": "manager-1", "guest_id": "attempt", "allowed_zone_ids": ["lobby"]}),
    ("/access/check", {"person_id": "guest-1", "zone_id": "machine-room", "purpose": "test"}),
    ("/building/devices/guessed/actions", {"id": "attempt", "person_id": "manager-1", "zone_id": "lobby", "command": "unlock"}),
    ("/building/integrations/anything", {"actor_id": "manager-1", "enabled": True}),
    ("/emergencies", {"created_by": "manager-1", "affected_zone_ids": ["lobby"]}),
])
def test_unauthorized_mutations_leave_state_unchanged(platform, api, path, body):
    before = (platform.list_appointments(), platform.list_permissions(), platform.list_emergencies(), platform.list_actuator_events())
    assert api("PATCH" if path.endswith("anything") else "POST", path, body, headers=headers(platform))[0] == 403
    assert before == (platform.list_appointments(), platform.list_permissions(), platform.list_emergencies(), platform.list_actuator_events())


@pytest.mark.parametrize("path", ["/building/catalog", "/appointments", "/emergencies", "/authorization/context", "/ring/simulation"])
def test_unauthenticated_scoped_routes_fail_closed(platform, api, path):
    assert api("GET", path)[0] == 401


def test_actor_spoof_and_csrf_fail_before_mutation(platform, api):
    grant(platform, "resident", Role.RESIDENT, "building-a", [P.VISITORS_INVITE])
    body = {"resident_id": "manager-1", "guest_id": "new", "guest_name": "Synthetic", "allowed_zone_ids": ["lobby"]}
    h = headers(platform, "resident")
    assert api("POST", "/guests/invite", body, headers=h)[0] == 403
    body["resident_id"] = "resident-1"
    assert api("POST", "/guests/invite", body, headers=h[:1])[0] == 403
    assert not platform.get_person("new")


def test_authorized_invite_binds_new_records_and_revocation_hides_them(platform, api):
    assignment = grant(platform, "resident", Role.RESIDENT, "building-a", [P.VISITORS_INVITE, P.VISITORS_READ, P.ACCESS_READ])
    body = {"resident_id": "resident-1", "guest_id": "new", "guest_name": "Synthetic", "allowed_zone_ids": ["lobby"]}
    h = headers(platform, "resident")
    status, result = api("POST", "/guests/invite", body, headers=h)
    assert status == 200, result
    assert platform.get_resource_binding("person", "new").scope_id == "resident-home"
    assert api("GET", "/guests/permissions", headers=h)[1][0]["id"] == result["permission"]["id"]
    platform.save_role_assignment(assignment.model_copy(update={"active": False}))
    assert api("GET", "/guests/permissions", headers=h) == (200, [])


def test_authorized_business_creation_and_checkin_are_scoped(platform, api):
    grant(platform, "business-x", Role.BUSINESS_ADMIN, "business-x",
        [P.VISITORS_INVITE, P.VISITORS_READ, P.VISITORS_CHECK_IN, P.ACCESS_READ])
    h = headers(platform, "business-x")
    body = {"id": "new-x", "visitor_id": "visitor-x", "visitor_name": "Synthetic", "business_id": "atlas-dental",
            "destination_zone_id": "office-106", "appointment_time": NOW.isoformat()}
    status, result = api("POST", "/appointments", body, headers=h)
    assert status == 201, result
    assert platform.get_resource_binding("appointment", "new-x").scope_id == "business-x"
    assert api("POST", "/appointments/new-x/check-in", {"visitor_id": "visitor-x", "visitor_name": "Synthetic"}, headers=h)[0] == 200
    assert platform.get_resource_binding("person", "visitor-x").scope_id == "business-x"
    body.update(id="new-y", business_id="business-y", destination_zone_id="office-y")
    assert api("POST", "/appointments", body, headers=h)[0] == 403


def test_application_permissions_do_not_grant_physical_access(platform, api):
    grant(platform, "manager", Role.MANAGER, "building-a", [P.ACCESS_CHECK])
    status, decision = api("POST", "/access/check", {"person_id": "manager-1", "zone_id": "lobby", "purpose": "test"}, headers=headers(platform))
    assert status == 200 and decision["allowed"] is False
    assert "explicit physical" in decision["reason"]


def test_policy_outcome_does_not_expose_unreadable_physical_grant(platform, api):
    grant(platform, "manager", Role.MANAGER, "building-a", [P.ACCESS_CHECK])
    permission = AccessPermission(id="physical", person_id="manager-1", allowed_zone_ids=["lobby"],
        valid_from=NOW, valid_until=NOW + timedelta(hours=1), reason="Explicit physical grant")
    platform.add_guest_permission(platform.get_person("manager-1"), permission)
    h = headers(platform)
    body = {"person_id": "manager-1", "zone_id": "lobby", "purpose": "test"}
    status, decision = api("POST", "/access/check", body, headers=h)
    assert status == 200 and decision["allowed"] and decision["permission"] is None
    bind(platform, "access_permission", "physical", "building-a")
    grant(platform, "manager", Role.MANAGER, "building-a", [P.ACCESS_CHECK, P.ACCESS_READ])
    assert api("POST", "/access/check", body, headers=h)[1]["permission"]["id"] == "physical"


def test_admin_configuration_has_no_operational_or_private_content(platform, api):
    grant(platform, "manager", Role.ADMIN, "building-a", [P.AUTHORIZATION_MANAGE, P.HARDWARE_READ, P.HARDWARE_CONFIGURE])
    assert api("GET", "/appointments", headers=headers(platform)) == (200, [])
    assert api("GET", "/emergencies", headers=headers(platform)) == (200, [])
    assert not authority(platform).allowed_scope(P.CAMERA_VIEW, "building-a")
    assert api("GET", "/building/devices/door-main/status", headers=headers(platform))[0] == 403


def test_manager_cannot_administer_grants_and_admin_cannot_escalate(platform, api):
    manager = grant(platform, "manager", Role.MANAGER, "building-a", [P.PEOPLE_READ])
    assignment = RoleAssignment(id="attempt", user_id="resident", role=Role.MANAGER,
        scope_id="building-a", permissions=[P.PEOPLE_READ])
    h = headers(platform)
    assert api("PUT", "/authorization/assignments/attempt", assignment.model_dump(mode="json"), headers=h)[0] == 403
    platform.save_role_assignment(manager.model_copy(update={"active": False}))
    grant(platform, "manager", Role.ADMIN, "building-a", [P.AUTHORIZATION_MANAGE])
    assert api("PUT", "/authorization/assignments/attempt", assignment.model_dump(mode="json"), headers=h)[0] == 403
    assert not platform.get_role_assignment("attempt")


def test_bounded_delegation_and_revocation(platform, api):
    grant(platform, "manager", Role.ADMIN, "building-a", [P.AUTHORIZATION_MANAGE, P.HARDWARE_READ])
    h = headers(platform)
    assignment = RoleAssignment(id="delegated", user_id="resident", role=Role.ADMIN,
        scope_id="business-x", permissions=[P.HARDWARE_READ])
    assert api("PUT", "/authorization/assignments/delegated", assignment.model_dump(mode="json"), headers=h)[0] == 200
    assert authority(platform, "resident").allowed_scope(P.HARDWARE_READ, "business-x")
    assert api("DELETE", "/authorization/assignments/delegated", headers=h)[0] == 200
    assert not authority(platform, "resident").allowed_scope(P.HARDWARE_READ, "business-x")


def test_owner_appoints_admin_without_private_operational_authority(platform, api):
    grant(platform, "manager", Role.OWNER, "org-a", [P.OWNERSHIP_MANAGE])
    h = headers(platform)
    assignment = RoleAssignment(id="appointed-admin", user_id="resident", role=Role.ADMIN,
        scope_id="building-a", permissions=[P.AUTHORIZATION_MANAGE, P.HARDWARE_READ])
    assert api("PUT", "/authorization/assignments/appointed-admin", assignment.model_dump(mode="json"), headers=h)[0] == 200
    assert authority(platform, "resident").allowed_scope(P.AUTHORIZATION_MANAGE, "building-a")
    assert api("GET", "/appointments", headers=h) == (200, [])
    assert api("GET", "/authorization/assignments", headers=h)[1][0]["id"] == "appointed-admin"
    assert api("DELETE", "/authorization/assignments/appointed-admin", headers=h)[0] == 200
    assert not authority(platform, "resident").allowed_scope(P.AUTHORIZATION_MANAGE, "building-a")


def test_owner_cannot_appoint_operational_role_or_admin_in_other_org(platform, api):
    grant(platform, "manager", Role.OWNER, "org-a", [P.OWNERSHIP_MANAGE])
    h = headers(platform)
    for role, scope, permission in ((Role.ADMIN, "building-b", P.HARDWARE_READ),
                                    (Role.MANAGER, "building-a", P.PEOPLE_READ)):
        assignment = RoleAssignment(id="attempt", user_id="resident", role=role, scope_id=scope, permissions=[permission])
        assert api("PUT", "/authorization/assignments/attempt", assignment.model_dump(mode="json"), headers=h)[0] == 403
    assert not platform.get_role_assignment("attempt")


def ai_fixture(repo):
    assignment = grant(repo, "resident", Role.RESIDENT, "building-a", [P.AI_USE, P.VISITORS_INVITE, P.PEOPLE_READ])
    tools = AgentTools(repo, PendingActionStore(repo), "resident-1", lambda: NOW, authority(repo, "resident"))
    return assignment, tools


def test_ai_read_tools_filter_before_model_context(platform):
    grant(platform, "business-x", Role.BUSINESS_ADMIN, "business-x", [P.AI_USE, P.PEOPLE_READ, P.BUSINESSES_READ])
    tools = AgentTools(platform, PendingActionStore(platform), "contractor-1", lambda: NOW, authority(platform, "business-x"))
    assert [r["id"] for r in tools.run("find_businesses", {}).data["items"]] == ["atlas-dental"]
    assert tools.run("find_people", {"query": "guest-1"}).data["items"] == []
    assert tools.run("check_access", {"person_id": "guest-1", "zone_id": "lobby", "purpose": "test"}).status == "error"


@pytest.mark.parametrize("change", ["revoke", "scope_rebind", "wrong_user", "legacy_unbound"])
def test_ai_confirmation_identity_scope_and_revocation(platform, change):
    assignment, tools = ai_fixture(platform)
    proposal = tools.run("invite_guest", {"resident_id": "resident-1", "guest_id": "ai-new", "guest_name": "Synthetic", "allowed_zone_ids": ["lobby"]})
    assert proposal.status == "confirmation_required", proposal
    action_id = proposal.data["id"]
    assert proposal.data["authenticated_user_id"] == "resident"
    assert proposal.data["authorization_scope_id"] == "resident-home"
    if change == "revoke":
        platform.save_role_assignment(assignment.model_copy(update={"active": False}))
    elif change == "scope_rebind":
        bind(platform, "person", "resident-1", "other-home")
    elif change == "legacy_unbound":
        action = platform.get_pending_action(action_id)
        platform.delete_pending_action(action_id)
        platform.add_pending_action(action.model_copy(update={"authenticated_user_id": None, "authorization_scope_id": None}))
    with pytest.raises(DomainError) as error:
        confirm_action(platform, PendingActionStore(platform), action_id, "resident-1", NOW,
                       authority(platform, "other" if change == "wrong_user" else "resident"))
    assert error.value.status_code == 403
    assert not platform.get_person("ai-new")


def test_ai_confirmation_success_and_replay(platform):
    _, tools = ai_fixture(platform)
    proposal = tools.run("invite_guest", {"resident_id": "resident-1", "guest_id": "ai-new", "guest_name": "Synthetic", "allowed_zone_ids": ["lobby"]})
    action_id = proposal.data["id"]
    result = confirm_action(platform, PendingActionStore(platform), action_id, "resident-1", NOW, authority(platform, "resident"))
    assert result.status == "success"
    assert platform.get_resource_binding("person", "ai-new").scope_id == "resident-home"
    with pytest.raises(DomainError) as error:
        confirm_action(platform, PendingActionStore(platform), action_id, "resident-1", NOW, authority(platform, "resident"))
    assert error.value.status_code == 404


@pytest.mark.parametrize("scenario", list(SCENARIOS))
def test_all_six_ring_scenarios_with_scoped_authenticated_gate(platform, api, scenario):
    from unittest.mock import Mock
    from app.api.ring import get_ring_service
    from app.main import app
    from app.services.ring import RingService
    from app.integrations.ring.client import RingClient
    from test_ring_simulation import _make_settings
    remote = Mock(spec=RingClient)
    service = RingService(platform, _make_settings(), remote)
    app.dependency_overrides[get_ring_service] = lambda: service
    assignment = grant(platform, "manager", Role.MANAGER, "building-a", [P.SIMULATION_RUN, P.RING_READ])
    h = headers(platform)
    before_permissions = platform.list_permissions()
    status, delivered = api("POST", f"/ring/simulation/scenarios/{scenario}", {}, headers=h)
    assert status == 200, delivered
    assert len(delivered["events"]) == len(SCENARIOS[scenario]["events"])
    for event in delivered["events"]:
        assert event["is_simulation"] and platform.get_ring_event(event["id"])
        assert platform.get_resource_binding("ring_event", event["id"]).scope_id == "building-a"
    status, inbox = api("GET", "/ring/simulation/events", headers=h)
    assert status == 200 and len(inbox) == len(delivered["events"])
    assert all("raw_payload" not in event for event in inbox)
    assert platform.list_permissions() == before_permissions
    assert platform.list_actuator_events() == []
    remote.discover.assert_not_called()
    platform.save_role_assignment(assignment.model_copy(update={"active": False}))
    assert api("POST", f"/ring/simulation/scenarios/{scenario}", {}, headers=h)[0] == 403


def test_scoped_ring_inbox_hides_unbound_events(platform, api):
    from unittest.mock import Mock
    from app.api.ring import get_ring_service
    from app.main import app
    from app.services.ring import RingService
    from app.integrations.ring.client import RingClient
    from test_ring_simulation import _make_settings
    service = RingService(platform, _make_settings(), Mock(spec=RingClient))
    app.dependency_overrides[get_ring_service] = lambda: service
    grant(platform, "manager", Role.MANAGER, "building-a", [P.SIMULATION_RUN, P.RING_READ])
    RingSimulationService(service).run_scenario("visitor_arrives", NOW)
    assert platform.list_ring_events()
    assert api("GET", "/ring/simulation/events", headers=headers(platform)) == (200, [])


def test_scoped_session_context_is_server_derived_and_contains_no_password(platform, api):
    grant(platform, "resident", Role.RESIDENT, "resident-home", [P.PEOPLE_READ])
    status, session = api("GET", "/auth/session", headers=headers(platform, "resident"))
    assert status == 200 and session["authorization_mode"] == "scoped"
    assert session["authorization"]["principal"] == {"user_id": "resident", "person_id": "resident-1"}
    assert "password_hash" not in session["user"]
    assert session["authorization"]["assignments"][0]["permissions"] == ["people.read"]


def test_scoped_ai_http_rejects_spoof_before_gateway(platform, api):
    grant(platform, "resident", Role.RESIDENT, "resident-home", [P.AI_USE])
    assert api("POST", "/agent/chat", {"message": "test", "actor_id": "manager-1"}, headers=headers(platform, "resident"))[0] == 403


def test_delegated_manager_setup_permission_is_explicit(platform, api):
    grant(platform, "manager", Role.ADMIN, "building-a", [P.AUTHORIZATION_MANAGE, P.HARDWARE_CONFIGURE])
    assignment = RoleAssignment(id="manager-setup", user_id="resident", role=Role.MANAGER,
        scope_id="business-x", permissions=[P.HARDWARE_CONFIGURE])
    assert api("PUT", "/authorization/assignments/manager-setup", assignment.model_dump(mode="json"), headers=headers(platform))[0] == 200
    assert authority(platform, "resident").allowed_scope(P.HARDWARE_CONFIGURE, "business-x")
    assert not authority(platform, "resident").allowed_scope(P.HARDWARE_CONFIGURE, "business-y")
    assert not authority(platform, "resident").allowed_scope(P.AUTHORIZATION_MANAGE, "business-x")


def test_scoped_policy_uses_hidden_emergency_snapshot(platform, api):
    from app.models.emergency import EmergencyCreateInput
    from app.services.emergencies import create_emergency
    grant(platform, "manager", Role.MANAGER, "building-a", [P.ACCESS_CHECK])
    permission = AccessPermission(id="physical", person_id="manager-1", allowed_zone_ids=["lobby"],
        valid_from=NOW, valid_until=NOW + timedelta(hours=1), reason="Explicit physical grant")
    platform.add_guest_permission(platform.get_person("manager-1"), permission)
    create_emergency(platform, EmergencyCreateInput(emergency_id="hidden", emergency_type="fire_alarm", severity="high",
        affected_zone_ids=["lobby"], created_by="manager-1", description="Synthetic incident"), NOW)
    assert api("GET", "/emergencies", headers=headers(platform)) == (200, [])
    status, decision = api("POST", "/access/check", {"person_id": "manager-1", "zone_id": "lobby", "purpose": "test"}, headers=headers(platform))
    assert status == 200 and not decision["allowed"]


def test_invalid_scope_graph_is_denied(platform):
    auth = authority(platform)
    scope = platform.get_scope("business-x")
    platform.save_scope(scope.model_copy(update={"parent_id": "org-b"}))
    grant(platform, "manager", Role.MANAGER, "org-b", [P.PEOPLE_READ])
    assert not auth.allowed_scope(P.PEOPLE_READ, "business-x")


def test_scope_provisioning_rejects_reparent_and_wrong_types(platform):
    auth = authority(platform)
    with pytest.raises(DomainError):
        auth.save_scope(platform.get_scope("business-x").model_copy(update={"parent_id": "building-b"}))
    with pytest.raises(DomainError):
        auth.save_scope(Scope(id="invalid", organization_id="org-a", kind=ScopeKind.BUILDING, parent_id="resident-home"))


def test_scoped_startup_protects_audited_database_and_disables_implicit_seeding(monkeypatch, tmp_path):
    monkeypatch.setenv("NODUM_AUTHORIZATION_MODE", "scoped")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ConfigurationError, match="separate"):
        validate_startup(AppSettings.from_env())
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'product-test.db'}")
    validate_startup(AppSettings.from_env())
    repository = SQLiteRepository()
    repository.initialize(seed_demo=False)
    assert repository.list_people() == repository.list_scopes() == repository.list_role_assignments() == []


def test_migration_5_preserves_v4_records_and_claims_nothing(tmp_path):
    path = tmp_path / "v4-upgrade.db"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    for version, statements in MIGRATIONS[:4]:
        for statement in statements:
            connection.execute(statement)
        connection.execute("INSERT INTO schema_migrations VALUES (?, 'test')", (version,))
    connection.execute("INSERT INTO people VALUES ('legacy', '{\"id\":\"legacy\"}')")
    connection.commit()
    connection.close()
    database = SQLiteDatabase(f"sqlite:///{path}")
    database.initialize()
    database.initialize()
    with database.transaction() as connection:
        assert connection.execute("SELECT data FROM people WHERE id='legacy'").fetchone()[0] == '{"id":"legacy"}'
        assert [r[0] for r in connection.execute("SELECT version FROM schema_migrations ORDER BY version")] == [version for version, _ in MIGRATIONS]
        for table in ("application_scopes", "application_role_assignments", "application_resource_bindings"):
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
