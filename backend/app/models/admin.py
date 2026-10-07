from typing import Literal
from pydantic import Field, SecretStr
from app.models.authorization import Record
from app.models.access import NonEmptyString


class OrganizationInput(Record):
    scope_id: NonEmptyString
    name: str = Field(min_length=1, max_length=200)
    demo: bool = False


class AccountInput(Record):
    name: str = Field(min_length=1, max_length=200)
    username: str = Field(min_length=3, max_length=128)
    password: SecretStr
    scope_id: NonEmptyString


class AccountStateInput(Record):
    active: bool


class MappingInput(Record):
    location_id: NonEmptyString


class RingSetupInput(Record):
    building_id: NonEmptyString


class SetupInput(Record):
    step: Literal["Building", "Floors & Areas", "Hardware", "Device Mapping", "Accounts", "Roles & Permissions", "Policies", "Review"]
    policy_reviewed: bool = False
    completed: bool = False


class DemoInput(Record):
    organization_id: NonEmptyString
    confirm_synthetic: Literal[True]
