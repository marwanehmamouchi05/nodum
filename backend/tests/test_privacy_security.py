"""Small pre-submission boundaries, not a claim of comprehensive security."""
import json
import pytest
from app.auth_config import AuthSettings
from app.main import app, create_app
from app.models.agent import AgentRequest
from app.models.emergency import EmergencyCreateInput
from app.services.auth import AuthService
from app.services.emergencies import create_emergency
from app.services.orchestrator import run_agent
from app.integrations.bedrock import BedrockSettings
from test_agent import tools, FakeBedrock, tool_response, text_response, invitation
from test_ring import settings, remote, service, link, deliver, ACCOUNT, PRINCIPAL
from app.api.ring import get_ring_service, require_ring_principal
from conftest import NOW


@pytest.fixture
def production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_PUBLIC_ORIGIN", "https://test")


def manager_session(api, repo, person="manager-1"):
    AuthService(repo, AuthSettings.from_env()).create_user("audit-user", "audit-only-password-835", person, NOW)
    _, data, headers = api("GET", "/auth/session", include_headers=True)
    cookie = headers[b"set-cookie"].split(b";")[0]
    _, data, headers = api("POST", "/auth/login", {"username": "audit-user", "password": "audit-only-password-835"},
                          headers=[(b"cookie", cookie), (b"origin", b"https://test"),
                                   (b"x-csrf-token", data["csrf_token"].encode())], include_headers=True)
    return [(b"cookie", headers[b"set-cookie"].split(b";")[0]), (b"origin", b"https://test"),
            (b"x-csrf-token", data["csrf_token"].encode())]


@pytest.mark.parametrize("method,path", [
    ("GET", "/building/catalog"), ("GET", "/appointments"), ("GET", "/guests/permissions"),
    ("GET", "/emergencies"), ("GET", "/building/journeys"), ("GET", "/building/credential-events"),
    ("POST", "/access/check"), ("POST", "/agent/chat"), ("POST", "/guests/invite"),
])
def test_production_core_routes_require_sign_in(api, production, method, path):
    assert api(method, path, {} if method == "POST" else None)[0] == 401


def test_production_manager_can_read_but_writes_require_csrf(api, repo, production):
    headers = manager_session(api, repo)
    assert api("GET", "/building/catalog", headers=headers)[0] == 200
    body = {"person_id": "contractor-1", "zone_id": "machine-room", "purpose": "Audit"}
    assert api("POST", "/access/check", body, headers=headers[:1])[0] == 403
    assert api("POST", "/access/check", body, headers=headers)[0] == 200
    assert api("POST", "/access/check", body, headers=[headers[0], (b"origin", b"https://evil.test"), headers[2]])[0] == 403
    api("POST", "/auth/logout", {}, headers=headers)
    assert api("GET", "/building/catalog", headers=headers)[0] == 401


@pytest.mark.parametrize("person", ["resident-1", "guest-1", "contractor-1", "responder-1"])
def test_non_manager_cannot_view_directory_or_history(api, repo, production, person):
    headers = manager_session(api, repo, person)
    for path in ("/building/catalog", "/appointments", "/building/journeys"):
        assert api("GET", path, headers=headers)[0] == 403


def test_production_docs_are_not_public_but_schema_generation_works(api, production):
    application = create_app()
    # Test the HTTP boundary rather than FastAPI's lazy included-router internals.
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert api("GET", path, target_app=application)[0] == 404
    assert "/building/catalog" in application.openapi()["paths"]


def test_health_and_ring_delivery_boundaries_remain_public_fail_closed(api, production):
    assert api("GET", "/health")[0] == 200
    assert api("POST", "/ring/token-exchange", {"code": "untrusted"})[0] == 503


def test_validation_never_echoes_raw_credential(api):
    status, data = api("POST", "/building/credentials", {"value": ["private-sentinel"], "kind": "invalid"})
    assert status == 422 and "private-sentinel" not in json.dumps(data)
    assert all("input" not in error and "ctx" not in error for error in data["detail"])


@pytest.mark.parametrize("name,args", [
    ("find_people", {}), ("find_people", {"query": "a"}),
    ("list_work_orders", {}), ("list_appointments", {"business_id": "atlas-dental"}),
])
def test_agent_cannot_request_unfiltered_sensitive_directories(repo, name, args):
    assert tools(repo).run(name, args).status == "error"


def test_agent_context_excludes_unnecessary_authority_and_work_details(repo):
    registry = tools(repo, "manager-1")
    people = registry.run("find_people", {"query": "resident"}).data["items"]
    assert people and "guest_zone_ids" not in people[0]
    assert "guest_zone_ids" in tools(repo, "resident-1").run("find_people", {"query": "resident"}).data["items"][0]
    orders = registry.run("list_work_orders", {"contractor_id": "contractor-1"}).data["items"]
    assert orders and "description" not in orders[0]


def test_bedrock_receives_incident_summary_not_descriptions_or_history(repo):
    create_emergency(repo, EmergencyCreateInput(emergency_id="audit-leak", emergency_type="water_leak",
        severity="high", affected_zone_ids=["utility-room"], description="private-medical-sentinel",
        created_by="manager-1"), NOW)
    gateway = FakeBedrock(tool_response("list_active_emergencies"), text_response())
    run_agent(AgentRequest(message="Active incidents?"), gateway, tools(repo), BedrockSettings())
    wire = json.dumps(gateway.calls[-1])
    assert "audit-leak" in wire and "private-medical-sentinel" not in wire
    assert '"history"' not in wire and '"created_by"' not in wire


def test_model_does_not_receive_pending_action_identifier(repo):
    gateway = FakeBedrock(tool_response("invite_guest", invitation()), text_response())
    result = run_agent(AgentRequest(message="Invite my guest", actor_id="resident-1"), gateway,
                       tools(repo, "resident-1"), BedrockSettings())
    action_id = result.tool_results[0].data["id"]
    assert action_id not in json.dumps(gateway.calls)


def test_ring_inbox_returns_summary_but_retains_server_audit(api, service):
    app.dependency_overrides[get_ring_service] = lambda: service
    app.dependency_overrides[require_ring_principal] = lambda: PRINCIPAL
    link(service)
    receipt = deliver(service)
    status, events = api("GET", f"/ring/accounts/{ACCOUNT}/events")
    assert status == 200 and events and "raw_payload" not in events[0]
    assert service.repository.get_ring_event(receipt["id"]).raw_payload


def test_private_responses_disable_caching(api):
    _, _, headers = api("GET", "/building/catalog", include_headers=True)
    assert headers[b"cache-control"] == b"no-store"
