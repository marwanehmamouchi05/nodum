"""Ring boundary and persistence records; never access permissions."""
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.models.access import NonEmptyString, UTCTimestamp


class RingAccount(BaseModel):
    id: str  # Environment-scoped hash of the opaque Ring account ID.
    environment: str
    account_id: NonEmptyString
    encrypted_tokens: str = Field(repr=False)
    expires_at: UTCTimestamp
    received_at: UTCTimestamp
    owner_id: str | None = None
    owner_user_id: str | None = None
    link_verified: bool = False
    status: Literal["unclaimed", "awaiting", "completed", "removed"] = "unclaimed"


class RingEvent(BaseModel):
    id: str
    environment: str
    account_id: NonEmptyString
    request_id: NonEmptyString
    event_id: NonEmptyString
    event_type: NonEmptyString
    source: NonEmptyString
    source_type: NonEmptyString
    occurred_at: UTCTimestamp
    received_at: UTCTimestamp
    signal: str
    raw_payload: str
    status: Literal["received", "review", "processed", "ignored"] = "received"
    emergency_id: str | None = None


class RingDevice(BaseModel):
    id: NonEmptyString
    name: str
    attributes: dict[str, Any]
    related: dict[str, dict[str, Any]] = Field(default_factory=dict)


class RingPrincipal(BaseModel):
    """Only construct from a verified, CSRF-protected server-side session."""
    person_id: NonEmptyString
    user_id: str | None = None
    masked_account_identifier: NonEmptyString


class RingLinkInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nonce: str = Field(min_length=43, max_length=43, pattern=r"^[A-Za-z0-9_-]+$")
    time: int = Field(strict=True, ge=0)


class RingTokens(BaseModel):
    access_token: SecretStr
    refresh_token: SecretStr
    expires_in: int = Field(strict=True, gt=0, le=31536000)
    token_type: Literal["Bearer"]
    scope: str = ""
