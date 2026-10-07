"""Client input never chooses creator, reporter, resource binding or authority."""
from typing import Literal
from pydantic import Field, model_validator
from app.models.authorization import Record
from app.models.access import NonEmptyString, UTCTimestamp


class AnnouncementInput(Record):
    location_id: NonEmptyString
    title: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1, max_length=4000)
    audience: Literal["all", "residential", "business"] = "all"
    publish_at: UTCTimestamp | None = None
    expires_at: UTCTimestamp | None = None


class MaintenanceInput(Record):
    location_id: NonEmptyString
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=4000)
    priority: Literal["low", "normal", "high"] = "normal"


class VisitorInput(Record):
    location_id: NonEmptyString
    name: str = Field(min_length=1, max_length=160)
    starts_at: UTCTimestamp
    ends_at: UTCTimestamp

    @model_validator(mode="after")
    def window(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("Visit end must follow start")
        return self


class MaintenanceUpdate(Record):
    status: Literal["new", "assigned", "in_progress", "resolved", "closed"]
    assignee_id: NonEmptyString | None = None
    note: str = Field(default="", max_length=2000)
    public_message: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def assignment(self):
        if self.status == "assigned" and not self.assignee_id:
            raise ValueError("Choose a maintenance person for Assigned status")
        return self
