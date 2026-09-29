from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.access import NonEmptyString, UTCTimestamp


class AgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=6000, pattern=r"\S")
    actor_id: NonEmptyString | None = None


class AgentToolResult(BaseModel):
    tool: str
    status: Literal["success", "error", "confirmation_required"]
    data: Any


class AgentResponse(BaseModel):
    status: Literal["completed", "unavailable", "limited"]
    explanation: str
    explanation_is_authoritative: Literal[False] = False
    tool_results: list[AgentToolResult] = Field(default_factory=list)


class PendingAction(BaseModel):
    id: str
    actor_id: str
    tool: str
    arguments: dict
    created_at: UTCTimestamp
    expires_at: UTCTimestamp


class ConfirmActionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor_id: NonEmptyString
