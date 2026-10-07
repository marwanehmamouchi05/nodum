"""E2 contracts do not accept a client-selected business, role or owner."""
from pydantic import Field, SecretStr
from app.models.authorization import Record, Permission
from app.models.resident import ResidentVisitInput, ResidentMaintenanceInput


class BusinessVisitInput(ResidentVisitInput):
    pass


class BusinessMaintenanceInput(ResidentMaintenanceInput):
    pass


class StaffCreateInput(Record):
    name: str = Field(min_length=1, max_length=200, pattern=r'\S')
    username: str = Field(min_length=3, max_length=128)
    password: SecretStr
    permissions: list[Permission] = Field(default_factory=list)


class StaffUpdateInput(Record):
    active: bool
    permissions: list[Permission]
