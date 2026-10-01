"""Persisted identities and opaque sessions, separate from building roles."""
from pydantic import BaseModel, Field
from app.models.access import UTCTimestamp


class NodumUser(BaseModel):
    id: str
    username: str
    person_id: str
    password_hash: str = Field(repr=False)
    active: bool = True
    created_at: UTCTimestamp

    def public(self):
        return self.model_dump(mode="json", exclude={"password_hash"})


class AuthSession(BaseModel):
    id: str  # Digest only; the bearer secret lives in the HttpOnly cookie.
    user_id: str | None = None
    created_at: UTCTimestamp
    expires_at: UTCTimestamp


class AuthThrottle(BaseModel):
    id: str
    attempts: int
    expires_at: UTCTimestamp
