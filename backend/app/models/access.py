from datetime import timezone
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, BaseModel, Field, model_validator


def normalize_utc(value):
    try:
        return value.astimezone(timezone.utc)
    except OverflowError:
        # An offset can place a valid local date outside datetime's UTC range.
        # Keep this an input validation failure, not an unexpected service fault.
        raise ValueError("Timestamp is outside the representable UTC range") from None


UTCTimestamp = Annotated[AwareDatetime, AfterValidator(normalize_utc)]
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
    appointment_id: NonEmptyString | None = None
    business_id: NonEmptyString | None = None

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
