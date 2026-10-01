"""Coarse production console boundary; not tenant or per-resource RBAC."""
from fastapi import Depends, Request
from app.api.dependencies import get_repository, utc_now
from app.auth_config import AuthSettings
from app.config import AppSettings, ConfigurationError
from app.models.building import PersonRole
from app.services.auth import AuthService
from app.services.errors import DomainError


def require_production_operator(request: Request, repository=Depends(get_repository),
                                now=Depends(utc_now)):
    if AppSettings.from_env().environment != "production":
        return  # Local demo compatibility; never use development mode publicly.
    if request.url.path.startswith("/building/ring/"):
        return  # These routes already require the owner-bound Ring principal + CSRF.
    try:
        settings = AuthSettings.from_env()
    except ConfigurationError:
        raise DomainError(503, "Configure production Nodum authentication before using building APIs") from None
    service = AuthService(repository, settings)
    cookie = request.cookies.get(settings.cookie_name)
    user = service.user(cookie, now)
    if not user:
        raise DomainError(401, "Sign in as a Nodum manager to use the operations console")
    if repository.get_person(user.person_id).role != PersonRole.MANAGER:
        raise DomainError(403, "The operations console requires a manager account")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        service.check_csrf(cookie, request.headers.get("x-csrf-token"),
                           request.headers.get("origin"), now)
