"""Thin Ring boundaries. Deployment authentication adapters fail closed by default."""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import get_repository, utc_now
from app.integrations.ring.config import RingSettings
from app.models.ring import RingLinkInput, RingPrincipal
from app.services.errors import DomainError
from app.services.ring import RingService


router = APIRouter(prefix="/ring", tags=["Ring"])


def get_ring_service(repository=Depends(get_repository)):
    return RingService(repository, RingSettings.from_env())


def require_ring_principal() -> RingPrincipal:
    # Replace with a real authenticated, CSRF-protected session dependency at
    # deployment. Never accept a person ID/email supplied by the request as proof.
    raise DomainError(503, "Ring linking requires a configured Nodum authentication adapter")


def receive_verified_ring_code() -> str:
    # Public docs specify server-to-server POST delivery but do not specify the
    # incoming encoding/auth contract. Install a Ring-confirmed adapter here.
    # Do not guess that this delivery has the webhook envelope/signature.
    raise DomainError(503, "Ring token delivery adapter is not configured")


Service = Annotated[RingService, Depends(get_ring_service)]
Principal = Annotated[RingPrincipal, Depends(require_ring_principal)]
Now = Annotated[datetime, Depends(utc_now)]


@router.post("/token-exchange")
def token_exchange(service: Service, now: Now,
                   code: Annotated[str, Depends(receive_verified_ring_code)]):
    return service.receive_code(code, now)


@router.post("/link")
def claim_account(payload: RingLinkInput, principal: Principal, service: Service, now: Now):
    return service.claim(payload, principal, now)


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
    return service.list_events(account_id, principal)


class ProcessEventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    zone_id: str | None = None


@router.post("/events/{event_id}/process")
def process_event(event_id: str, payload: ProcessEventInput, principal: Principal,
                  service: Service, now: Now):
    return service.process_event(event_id, principal, payload.zone_id, now)
