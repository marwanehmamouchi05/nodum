"""Local browser fixture: temporary DB, synthetic login, no audited runtime data."""
import os
from tempfile import TemporaryDirectory
from datetime import datetime, timezone
import uvicorn
from app.sqlite_repository import SQLiteRepository
from app.models.building import Person, PersonRole
from app.models.authorization import Scope, ScopeKind, RoleAssignment, Role, ResourceBinding
from app.services.authorization import ROLE_CEILINGS
from app.services.auth import AuthService
from app.auth_config import AuthSettings


if __name__ == "__main__":
    with TemporaryDirectory(prefix="nodum-admin-qa-") as directory:
        os.environ.update(DATABASE_URL="sqlite:///" + directory + "/productization.db",
            NODUM_AUTHORIZATION_MODE="scoped", APP_ENV="development",
            AUTH_PUBLIC_ORIGIN="http://127.0.0.1:8766", AUTH_TRUSTED_ORIGINS="http://127.0.0.1:5174",
            CORS_ALLOWED_ORIGINS="http://127.0.0.1:5174", CORS_ALLOW_CREDENTIALS="true")
        # Never inherit bootstrap configuration from an operator's environment.
        for key in ("AUTH_BOOTSTRAP_USERNAME", "AUTH_BOOTSTRAP_PASSWORD", "AUTH_BOOTSTRAP_PERSON_ID"):
            os.environ.pop(key, None)
        now = datetime.now(timezone.utc)
        repo = SQLiteRepository(os.environ["DATABASE_URL"])
        repo.initialize(seed_demo=False)
        repo.save_configured_person(Person(id="qa-admin-person", name="Synthetic Admin", role=PersonRole.EMPLOYEE))
        user = AuthService(repo, AuthSettings.from_env()).create_user("qa-admin", "Synthetic-local-QA-only", "qa-admin-person", now)
        repo.save_scope(Scope(id="qa-organization", organization_id="qa-organization", kind=ScopeKind.ORGANIZATION))
        repo.save_role_assignment(RoleAssignment(id="qa-admin-assignment", user_id=user.id, role=Role.ADMIN,
            scope_id="qa-organization", permissions=list(ROLE_CEILINGS[Role.ADMIN])))
        repo.save_resource_binding(ResourceBinding(resource_type="person", resource_id=user.person_id, scope_id="qa-organization"))
        repo.save_resource_binding(ResourceBinding(resource_type="account", resource_id=user.id, scope_id="qa-organization"))
        uvicorn.run("app.main:app", host="127.0.0.1", port=8766, log_level="warning")
