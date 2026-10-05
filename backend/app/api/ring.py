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
from app.services.errors import DomainError
from app.services.ring import RingService
from app.services.ring_simulation import RingSimulationService, SCENARIOS, SIM_DEVICES


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
    # Public docs specify server-to-server POST delivery but do not specify the
    # incoming encoding/auth contract. Install a Ring-confirmed adapter here.
    # Do not guess that this delivery has the webhook envelope/signature.
    raise DomainError(503, "Ring token delivery adapter is not configured")


Service = Annotated[RingService, Depends(get_ring_service)]
Simulation = Annotated[RingSimulationService, Depends(get_ring_simulation)]
Principal = Annotated[RingPrincipal, Depends(require_ring_principal)]
Now = Annotated[datetime, Depends(utc_now)]


@router.post("/token-exchange")
def token_exchange(service: Service, now: Now,
                   code: Annotated[str, Depends(receive_verified_ring_code)]):
    return service.receive_code(code, now)


@router.post("/link")
def claim_account(payload: RingLinkInput, principal: Principal, service: Service, now: Now):
    return service.claim(payload, principal, now)


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
def linked_accounts(principal: Principal, service: Service):
    return service.linked_accounts(principal)


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
    return await run_in_threadpool(service.receive_event, bytes(body),
                                   request.headers.get("x-signature"), now)


@router.get("/accounts/{account_id}/events")
def list_events(account_id: str, principal: Principal, service: Service):
    return [event.model_dump(mode="json", exclude={"raw_payload"})
            for event in service.list_events(account_id, principal)]


class ProcessEventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    zone_id: str | None = None


@router.post("/events/{event_id}/process")
def process_event(event_id: str, payload: ProcessEventInput, principal: Principal,
                  service: Service, now: Now):
    return service.process_event(event_id, principal, payload.zone_id, now).model_dump(
        mode="json", exclude={"raw_payload"})


# ----- Ring Playground simulation endpoints -----------------------------
# These endpoints exist ONLY when RING_MODE=simulation. They use the real
# RingService.receive_event() path; nothing is faked inside the API layer.

@router.get("/simulation")
def simulation_status(simulation: Simulation, now: Now):
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
def simulation_devices(simulation: Simulation, principal: Principal):
    """Return the simulator's device catalog (no remote call)."""
    if simulation.settings.mode != "simulation":
        raise DomainError(403, "Ring simulation is only available in RING_MODE=simulation")
    return [device.model_dump(mode="json") for device in simulation.devices()]


@router.get("/simulation/events")
def simulation_events(simulation: Simulation, principal: Principal):
    """Owner-only audit inbox for the simulated account; raw payload excluded."""
    if simulation.settings.mode != "simulation":
        raise DomainError(403, "Ring simulation is only available in RING_MODE=simulation")
    return [event.model_dump(mode="json", exclude={"raw_payload"})
            for event in simulation.repository.list_ring_events()
            if event.account_id == "simulation.playground"
            and event.environment == simulation.settings.environment]


class SimulationScenarioInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    zone_id: str | None = None


@router.post("/simulation/scenarios/{scenario}")
def run_simulation_scenario(scenario: str, payload: SimulationScenarioInput,
                             simulation: Simulation, principal: Principal, now: Now):
    """Deliver a deterministic scenario into the real Ring webhook pipeline.

    Events go through ``RingService.receive_event()`` (signature-verified,
    normalized, deduped, persisted). Operators can then process them via the
    existing ``/ring/events/{id}/process`` endpoint.
    """
    if simulation.settings.mode != "simulation":
        raise DomainError(403, "Ring simulation is only available in RING_MODE=simulation")
    delivered = simulation.run_scenario(scenario, now)
    return {"scenario": scenario, "events": delivered,
            "zone_hint": payload.zone_id}
