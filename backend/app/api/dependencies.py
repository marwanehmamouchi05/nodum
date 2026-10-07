from datetime import datetime, timezone
from fastapi import Request
from fastapi import Depends

from app.repository import Repository


def get_repository(request: Request) -> Repository:
    return request.app.state.repository


def get_scoped_repository(request: Request, repository=Depends(get_repository)):
    from app.services.authorization import authorization_mode
    from app.services.scoped_repository import ScopedRepository
    if authorization_mode() == "scoped" and request.method in {"GET", "HEAD"}:
        return ScopedRepository(repository, request.state.authorization)
    return repository


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
