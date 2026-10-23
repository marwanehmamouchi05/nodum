"""Session-authenticated Ring boundaries; unverified token delivery fails closed."""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, ValidationError
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import get_repository, utc_now
from app.api.auth import get_current_user, get_auth_service, browser_page
from app.integrations.ring.config import RingSettings
from app.models.ring import RingLinkInput, RingPrincipal
from app.models.building import PersonRole
from app.services.errors import DomainError
from app.services.ring import RingService
from app.services.ring_simulation import RingSimulationService, SCENARIOS, SIM_DEVICES
from app.models.authorization import Permission as P
from app.services.scoped_repository import bind_created


router = APIRouter(prefix="/ring", tags=["Ring"])


def get_ring_service(repository=Depends(get_repository)):
    return RingService(repository, RingSettings.from_env())


def get_ring_simulation(service=Depends(get_ring_service)):
    return RingSimulationService(service)


def require_ring_principal(request: Request, user=Depends(get_current_user),
                           auth_service=Depends(get_auth_service),
                           now=Depends(utc_now)) -> RingPrincipal:
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        auth_service.check_csrf(request.cookies.get(auth_service.settings.cookie_name),
                                request.headers.get("x-csrf-token"), request.headers.get("origin"), now)
    return RingPrincipal(person_id=user.person_id, user_id=user.id,
                         masked_account_identifier=user.username[:1] + "***" + user.username[-1:])


def receive_verified_ring_code() -> str:
    # Production code delivery is separate from the hardware-free Playground.
    # Keep this closed until its vendor transport contract is verified.
    raise DomainError(503, "Ring token delivery adapter is not configured")


Service = Annotated[RingService, Depends(get_ring_service)]
Simulation = Annotated[RingSimulationService, Depends(get_ring_simulation)]
Principal = Annotated[RingPrincipal, Depends(require_ring_principal)]
Now = Annotated[datetime, Depends(utc_now)]


def playground_service(service):
    import os
    from dataclasses import replace
    from app.config import boolean
    from app.services.ring_playground import PlaygroundService
    if (service.settings.mode != "simulation" or
            (os.getenv("APP_ENV", "development") != "development" and not boolean("NODUM_JUDGE_DEMO"))):
        raise DomainError(403, "Official Playground checks are restricted to an explicit synthetic demo")
    return PlaygroundService(service.repository, replace(service.settings, api_base_url="https://api.amazonvision.com"))


def playground_scope(request, service):
    authorization = getattr(request.state, "authorization", None)
    if authorization:
        authorization.require(P.SIMULATION_RUN, "simulation", "ring")
        return service.repository.get_resource_binding("simulation", "ring").scope_id
    return "legacy-demo"


def require_simulation_operator(principal: Principal, request: Request, repository=Depends(get_repository)):
    authorization = getattr(request.state, "authorization", None)
    if authorization:
        authorization.require(P.SIMULATION_RUN, "simulation", "ring")
        return principal
    person = repository.get_person(principal.person_id)
    if not person or person.role != PersonRole.MANAGER:
        raise DomainError(403, "Ring simulation requires a manager account")
    return principal


SimulationOperator = Annotated[RingPrincipal, Depends(require_simulation_operator)]


@router.get("/playground/devices")
def playground_devices(principal: SimulationOperator, service: Service, now: Now):
    """Read official sandbox devices without importing a token as a live account."""
    import os
    from dataclasses import replace
    from app.config import boolean
    from app.integrations.ring.client import RingClient, RingRemoteError

    if (service.settings.mode != "simulation" or
            (os.getenv("APP_ENV", "development") != "development" and not boolean("NODUM_JUDGE_DEMO"))):
        raise DomainError(403, "Official Playground checks are restricted to an explicit synthetic demo")
    token = os.getenv("RING_PLAYGROUND_TOKEN", "").strip()
    if not token:
        raise DomainError(503, "Official Playground token is not configured; generate a fresh temporary token in the Ring console")
    client = RingClient(replace(service.settings, api_base_url="https://api.amazonvision.com"))
    result = client.api("GET", "/v1/devices", token)
    records = result.get("data")
    if not isinstance(records, list) or len(records) > 50:
        raise RingRemoteError()
    devices = []
    for record in records:
        if (not isinstance(record, dict) or record.get("type") != "devices"
                or not isinstance(record.get("id"), str) or len(record["id"]) > 200
                or not isinstance(record.get("attributes"), dict)):
            raise RingRemoteError()
        name = record["attributes"].get("name")
        if not isinstance(name, str) or len(name) > 200:
            raise RingRemoteError()
        devices.append({"id": record["id"], "name": name})
    return {"source": "official_ring_playground", "checked_at": now,
            "devices": devices, "scope": "Discovery only; no webhook delivery, visitor identity or physical control verified"}


@router.post("/token-exchange")
def token_exchange(service: Service, now: Now,
                   code: Annotated[str, Depends(receive_verified_ring_code)]):
    return service.receive_code(code, now)


@router.get("/playground/evidence")
def playground_evidence(request: Request, principal: SimulationOperator, service: Service):
    return playground_service(service).evidence(playground_scope(request, service))


@router.post("/playground/sync")
def sync_playground(request: Request, principal: SimulationOperator, service: Service, now: Now):
    import os
    playground = playground_service(service)
    scope_id = playground_scope(request, service)
    guard = getattr(request.app.state, "usage_guard", None)
    if guard:
        try:
            guard.reserve([("ring-playground-minute", now.strftime("%Y-%m-%dT%H:%M"), "all", 1, 2)])
        except DomainError as exc:
            if exc.status_code == 429:
                raise DomainError(429, "Official sandbox sync is limited to two checks per minute. Stored evidence remains available.") from None
            raise
    return playground.sync(os.getenv("RING_PLAYGROUND_TOKEN", "").strip(), scope_id, now,
                           authorize=lambda: playground_scope(request, service))


@router.post("/link")
def claim_account(payload: RingLinkInput, principal: Principal, service: Service, now: Now, request: Request):
    result = service.claim(payload, principal, now)
    authorization = getattr(request.state, "authorization", None)
    if authorization:
        with service.repository.transaction():
            authorization.require(P.RING_MANAGE, "ring_link", "installation")
            scope_id = service.repository.get_resource_binding("ring_link", "installation").scope_id
            from app.services.ring import identity
            bind_created(service.repository, "ring_account", identity(service.settings.environment, result["account_id"]), scope_id)
            # Ring may deliver device events before the user finishes linking.
            # Only this independently verified account inherits the chosen scope.
            for event in service.repository.list_ring_events():
                if event.environment == service.settings.environment and event.account_id == result["account_id"]:
                    bind_created(service.repository, "ring_event", event.id, scope_id)
    return result


def link_redirect_input(nonce: Annotated[str, Query()],
                        time: Annotated[str, Query(pattern=r"^[0-9]+$", max_length=20)]):
    # Query values arrive as strings; retain the existing strict body/domain model
    # and its nonce constraints rather than weakening it to coerce JSON inputs.
    try:
        return RingLinkInput(nonce=nonce, time=int(time))
    except ValidationError as exc:
        raise RequestValidationError([
            dict(error, loc=("query", *error["loc"])) for error in exc.errors()
        ]) from None


@router.get("/link")
def claim_account_redirect(payload: Annotated[RingLinkInput, Depends(link_redirect_input)]):
    """Preserve the redirect query in the browser; never claim on GET."""
    return browser_page()


@router.get("/accounts")
def linked_accounts(principal: Principal, service: Service, request: Request):
    records = service.linked_accounts(principal)
    authorization = getattr(request.state, "authorization", None)
    if authorization:
        from app.services.ring import identity
        records = [a for a in records if authorization.allowed(P.RING_READ, "ring_account",
                    identity(a["environment"], a["account_id"]))]
    return records


@router.get("/accounts/{account_id}/devices")
def discover_devices(account_id: str, principal: Principal, service: Service, now: Now):
    return service.discover(account_id, principal, now)


@router.post("/webhooks")
async def webhook(request: Request, service: Service, now: Now):
    # Bound streaming input before buffering; verify the exact received bytes.
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 1_048_576:
            raise DomainError(413, "Ring webhook exceeds maximum size")
    result = await run_in_threadpool(service.receive_event, bytes(body),
                                    request.headers.get("x-signature"), now)
    from app.services.ring import identity
    with service.repository.transaction():
        event = service.repository.get_ring_event(result["id"])
        account = service.repository.get_ring_account(identity(event.environment, event.account_id))
        binding = service.repository.get_resource_binding("ring_account", identity(event.environment, event.account_id))
        if account and account.status == "completed" and binding:
            bind_created(service.repository, "ring_event", event.id, binding.scope_id)
    return result


@router.get("/accounts/{account_id}/events")
def list_events(account_id: str, principal: Principal, service: Service, request: Request):
    authorization = getattr(request.state, "authorization", None)
    return [event.model_dump(mode="json", exclude={"raw_payload"})
            for event in service.list_events(account_id, principal)
            if not authorization or authorization.allowed(P.RING_READ, "ring_event", event.id)]


class ProcessEventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    zone_id: str | None = None


@router.post("/events/{event_id}/process")
def process_event(event_id: str, payload: ProcessEventInput, principal: Principal,
                  service: Service, now: Now, request: Request):
    authorization = getattr(request.state, "authorization", None)
    if authorization:
        from app.services.authorization_operations import authorize_operation
        with service.repository.transaction():
            authorize_operation(authorization, "/ring/events/{event_id}/process",
                                payload.model_dump(), {"event_id": event_id})
            event = service.process_event(event_id, principal, payload.zone_id, now)
            if event.emergency_id and payload.zone_id:
                scope = service.repository.get_resource_binding("location", payload.zone_id).scope_id
                bind_created(service.repository, "incident", event.emergency_id, scope)
    else:
        event = service.process_event(event_id, principal, payload.zone_id, now)
    return event.model_dump(
        mode="json", exclude={"raw_payload"})


# ----- Nodum custom simulation endpoints (not official Ring Playground) --
# These endpoints exist ONLY when RING_MODE=simulation. They use the real
# RingService.receive_event() path; nothing is faked inside the API layer.

@router.get("/simulation")
def simulation_status(simulation: Simulation, now: Now, principal: SimulationOperator):
    """Report current mode plus the seeded simulation account (if available)."""
    payload: dict = {"mode": simulation.settings.mode,
                     "scenarios": [{"name": n, "label": s["label"],
                                    "description": s["description"],
                                    "event_count": len(s["events"])}
                                   for n, s in SCENARIOS.items()],
                     "device_count": len(SIM_DEVICES)}
    if simulation.settings.mode == "simulation":
        payload["account"] = simulation.account_summary(now)
    return payload


@router.get("/simulation/devices")
def simulation_devices(simulation: Simulation, principal: SimulationOperator):
    """Return the simulator's device catalog (no remote call)."""
    if simulation.settings.mode != "simulation":
        raise DomainError(403, "Ring simulation is only available in RING_MODE=simulation")
    return [device.model_dump(mode="json") for device in simulation.devices()]


@router.get("/simulation/events")
def simulation_events(simulation: Simulation, principal: SimulationOperator, request: Request):
    """Manager-only demo inbox for the simulated account; raw payload excluded."""
    if simulation.settings.mode != "simulation":
        raise DomainError(403, "Ring simulation is only available in RING_MODE=simulation")
    authorization = getattr(request.state, "authorization", None)
    return [event.model_dump(mode="json", exclude={"raw_payload"})
            for event in simulation.repository.list_ring_events()
            if event.account_id == "simulation.playground"
            and event.environment == simulation.settings.environment
            and (not authorization or authorization.allowed(P.RING_READ, "ring_event", event.id))]


class SimulationScenarioInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    zone_id: str | None = None


@router.post("/simulation/scenarios/{scenario}")
def run_simulation_scenario(scenario: str, payload: SimulationScenarioInput,
                             simulation: Simulation, principal: SimulationOperator, now: Now, request: Request):
    """Deliver a deterministic scenario into the real Ring webhook pipeline.

    Events go through ``RingService.receive_event()`` (signature-verified,
    normalized, deduped, persisted). Operators can then process them via the
    existing ``/ring/events/{id}/process`` endpoint.
    """
    if simulation.settings.mode != "simulation":
        raise DomainError(403, "Ring simulation is only available in RING_MODE=simulation")
    authorization = getattr(request.state, "authorization", None)
    if authorization:
        with simulation.repository.transaction():
            authorization.require(P.SIMULATION_RUN, "simulation", "ring")
            scope_id = simulation.repository.get_resource_binding("simulation", "ring").scope_id
            delivered = simulation.run_scenario(scenario, now)
            for event in delivered:
                bind_created(simulation.repository, "ring_event", event["id"], scope_id)
    else:
        delivered = simulation.run_scenario(scenario, now)
    return {"scenario": scenario, "events": delivered,
            "zone_hint": payload.zone_id}
