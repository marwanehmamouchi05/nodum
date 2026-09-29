from datetime import datetime, timezone
from fastapi import Request

from app.repository import Repository


def get_repository(request: Request) -> Repository:
    return request.app.state.repository


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
