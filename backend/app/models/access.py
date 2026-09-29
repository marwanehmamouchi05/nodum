from datetime import timezone
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, BaseModel, Field, model_validator


UTCTimestamp = Annotated[
    AwareDatetime, AfterValidator(lambda value: value.astimezone(timezone.utc))
]
NonEmptyString = Annotated[str, Field(min_length=1, pattern=r"\S")]


class AccessRequest(BaseModel):
    person_id: NonEmptyString
    zone_id: NonEmptyString
    purpose: NonEmptyString
    requested_at: UTCTimestamp


class AccessPermission(BaseModel):
    person_id: NonEmptyString
    allowed_zone_ids: list[NonEmptyString] = Field(min_length=1)
    valid_from: UTCTimestamp
    valid_until: UTCTimestamp
    reason: NonEmptyString
    id: str = ""
    granted_by: str | None = None
    created_at: UTCTimestamp | None = None

    @model_validator(mode="after")
    def validate_period(self):
        if self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be after valid_from")
        self.allowed_zone_ids = sorted(set(self.allowed_zone_ids))
        return self


class AccessDecision(BaseModel):
    allowed: bool
    reason: str
    permission: AccessPermission | None = None


class GuestInviteInput(BaseModel):
    # Kept for API compatibility; may identify a resident or manager.
    resident_id: NonEmptyString
    guest_id: NonEmptyString
    guest_name: NonEmptyString
    allowed_zone_ids: list[NonEmptyString] = Field(min_length=1)
    valid_for_hours: int = Field(default=3, ge=1, le=24, strict=True)


class AccessCheckInput(BaseModel):
    person_id: NonEmptyString
    zone_id: NonEmptyString
    purpose: NonEmptyString
