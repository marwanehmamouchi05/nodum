"""Application authority, deliberately separate from physical access grants."""
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
from app.models.access import NonEmptyString, UTCTimestamp


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    SECURITY = "security"
    MAINTENANCE = "maintenance"
    BUSINESS_ADMIN = "business_admin"
    BUSINESS_STAFF = "business_staff"
    RESIDENT = "resident"


class ScopeKind(str, Enum):
    ORGANIZATION = "organization"
    BUILDING = "building"
    BUSINESS = "business"
    LOCATION = "location"
    PERSON = "person"


class Permission(str, Enum):
    OWNERSHIP_MANAGE = "ownership.manage"
    AUTHORIZATION_MANAGE = "authorization.manage"
    ACCOUNTS_READ = "accounts.read"
    ACCOUNTS_MANAGE = "accounts.manage"
    PEOPLE_READ = "people.read"
    BUSINESS_STAFF_MANAGE = "business.staff.manage"
    STRUCTURE_CONFIGURE = "structure.configure"
    AFFILIATIONS_MANAGE = "affiliations.manage"
    LOCATIONS_READ = "locations.read"
    BUSINESSES_READ = "businesses.read"
    HARDWARE_READ = "hardware.read"
    HARDWARE_CONFIGURE = "hardware.configure"
    CAMERA_VIEW = "camera.view"
    VISITORS_READ = "visitors.read"
    VISITORS_INVITE = "visitors.invite"
    VISITORS_CHECK_IN = "visitors.check_in"
    ACCESS_READ = "access.read"
    ACCESS_CHECK = "access.check"
    ANNOUNCEMENTS_READ = "announcements.read"
    ANNOUNCEMENTS_PUBLISH = "announcements.publish"
    MAINTENANCE_CREATE = "maintenance.create"
    MAINTENANCE_MANAGE = "maintenance.manage"
    MAINTENANCE_READ = "maintenance.read"
    INCIDENTS_READ = "incidents.read"
    INCIDENTS_MANAGE = "incidents.manage"
    ACTIVITY_READ = "activity.read"
    RING_READ = "ring.read"
    RING_MANAGE = "ring.manage"
    RING_PROCESS = "ring.process"
    SIMULATION_RUN = "simulation.run"
    AI_USE = "ai.use"


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Scope(Record):
    id: NonEmptyString
    organization_id: NonEmptyString
    kind: ScopeKind
    parent_id: NonEmptyString | None = None
    active: bool = True


class RoleAssignment(Record):
    id: NonEmptyString
    user_id: NonEmptyString
    role: Role
    scope_id: NonEmptyString
    # Explicit subset of the role ceiling; a role label alone grants nothing.
    permissions: list[Permission] = Field(default_factory=list)
    active: bool = True
    expires_at: UTCTimestamp | None = None


class ResourceBinding(Record):
    resource_type: NonEmptyString
    resource_id: NonEmptyString
    scope_id: NonEmptyString


class Principal(Record):
    user_id: NonEmptyString
    person_id: NonEmptyString
