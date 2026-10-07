"""Resident input selects only an affiliation; destination and identity are derived."""
from pydantic import Field, model_validator
from app.models.authorization import Record
from app.models.access import NonEmptyString, UTCTimestamp


class ResidentTarget(Record):
    affiliation_id: NonEmptyString | None = None


class ResidentVisitInput(ResidentTarget):
    name: str = Field(min_length=1, max_length=160, pattern=r"\S")
    starts_at: UTCTimestamp
    ends_at: UTCTimestamp
    note: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def window(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("Visit end must follow start")
        return self


class ResidentMaintenanceInput(ResidentTarget):
    title: str = Field(min_length=1, max_length=160, pattern=r"\S")
    description: str = Field(min_length=1, max_length=4000, pattern=r"\S")
    priority: str = Field(default="normal", pattern=r"^(low|normal|high)$")
