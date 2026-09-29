from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.api.dependencies import get_repository, utc_now
from app.integrations.bedrock import BedrockGateway, BedrockSettings, BedrockUnavailable
from app.models.agent import AgentRequest, AgentResponse, AgentToolResult, ConfirmActionInput
from app.repository import Repository
from app.services.agent_actions import PendingActionStore
from app.services.agent_tools import AgentTools, confirm_action
from app.services.errors import DomainError
from app.services.orchestrator import run_agent


router = APIRouter(prefix="/agent", tags=["agent"])


def get_agent_settings() -> BedrockSettings:
    try:
        return BedrockSettings.from_env()
    except BedrockUnavailable as exc:
        raise DomainError(503, "Invalid AI configuration") from exc


def get_gateway(settings: BedrockSettings = Depends(get_agent_settings)):
    return BedrockGateway(settings)


def get_actions(request: Request) -> PendingActionStore:
    return request.app.state.agent_actions


def get_agent_clock():
    return utc_now


@router.post("/chat", response_model=AgentResponse, responses={503: {"model": AgentResponse}})
def chat(payload: AgentRequest, repository: Repository = Depends(get_repository),
         actions: PendingActionStore = Depends(get_actions),
         gateway=Depends(get_gateway), settings: BedrockSettings = Depends(get_agent_settings),
         clock=Depends(get_agent_clock)):
    tools = AgentTools(repository, actions, payload.actor_id, clock)
    response = run_agent(payload, gateway, tools, settings)
    if response.status == "unavailable":
        return JSONResponse(status_code=503, content=response.model_dump(mode="json"))
    return response


@router.post("/actions/{action_id}/confirm", response_model=AgentToolResult)
def confirm(action_id: str, payload: ConfirmActionInput,
            repository: Repository = Depends(get_repository),
            actions: PendingActionStore = Depends(get_actions), clock=Depends(get_agent_clock)):
    return confirm_action(repository, actions, action_id, payload.actor_id, clock())
