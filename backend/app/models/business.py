from datetime import timedelta
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.access import AccessPermission, NonEmptyString, UTCTimestamp


class Business(BaseModel):
    id: NonEmptyString
    name: NonEmptyString
    destination_zone_ids: list[NonEmptyString] = Field(min_length=1)
    active: bool = True


class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CHECKED_IN = "checked_in"
    CANCELLED = "cancelled"


class AppointmentCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: NonEmptyString
    visitor_id: NonEmptyString
    visitor_name: NonEmptyString
    business_id: NonEmptyString
    destination_zone_id: NonEmptyString
    appointment_time: UTCTimestamp
    access_before_minutes: int = Field(default=15, ge=0, le=120, strict=True)
    access_after_minutes: int = Field(default=60, ge=1, le=480, strict=True)

    @property
    def window_start(self):
        return self.appointment_time - timedelta(minutes=self.access_before_minutes)

    @property
    def window_end(self):
        return self.appointment_time + timedelta(minutes=self.access_after_minutes)

    @model_validator(mode="after")
    def validate_window(self):
        try:
            self.window_start
            self.window_end
        except OverflowError as exc:
            raise ValueError("Appointment access window is outside supported dates") from exc
        return self


class Appointment(AppointmentCreateInput):
    status: AppointmentStatus = AppointmentStatus.SCHEDULED
    created_at: UTCTimestamp
    checked_in_at: UTCTimestamp | None = None

    @model_validator(mode="after")
    def validate_state(self):
        if self.created_at > self.appointment_time:
            raise ValueError("Appointment cannot be created after its scheduled time")
        if self.status == AppointmentStatus.CHECKED_IN:
            if self.checked_in_at is None:
                raise ValueError("Checked-in appointments require a check-in timestamp")
            if not self.window_start <= self.checked_in_at < self.window_end:
                raise ValueError("Check-in timestamp is outside the appointment window")
            if self.checked_in_at < self.created_at:
                raise ValueError("Check-in cannot precede creation")
        elif self.checked_in_at is not None:
            raise ValueError("Only checked-in appointments may have a check-in timestamp")
        return self


class VisitorCheckInInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    visitor_id: NonEmptyString
    visitor_name: NonEmptyString


class VisitorCheckInResult(BaseModel):
    appointment: Appointment
    permission: AccessPermission
