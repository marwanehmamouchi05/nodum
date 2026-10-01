import sqlite3
from datetime import datetime, timezone
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from app.api.auth import router as auth_router
from app.services.auth import bootstrap_user
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import AppSettings, ConfigurationError, validate_startup
from app.sqlite_repository import SQLiteRepository
from app.services.errors import DomainError

from app.api.access import router as access_router
from app.api.guests import router as guests_router
from app.api.appointments import router as appointments_router
from app.api.emergencies import router as emergencies_router
from app.api.agent import router as agent_router
from app.api.ring import router as ring_router
from app.api.building import router as building_router
from app.services.agent_actions import PendingActionStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_startup(AppSettings.from_env())
    try:
        repository = SQLiteRepository()
        repository.initialize()
    except (ValueError, OSError, RuntimeError, sqlite3.Error):
        raise ConfigurationError("Database startup failed; check DATABASE_URL, storage permissions and schema version") from None
    bootstrap_user(repository, datetime.now(timezone.utc))
    app.state.repository = repository
    app.state.agent_actions = PendingActionStore(repository)
    yield


def create_app():
    settings = AppSettings.from_env()
    application = FastAPI(title="Nodum API", version="0.1.0", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware, allow_origins=list(settings.cors_origins),
        allow_credentials=settings.cors_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    )
    for router in (access_router, guests_router, appointments_router,
                   emergencies_router, agent_router, ring_router, building_router, auth_router):
        application.include_router(router)

    @application.middleware("http")
    async def private_auth_responses(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(("/auth/", "/ring/", "/building/ring/")):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(request, exc):
        if request.url.path.startswith("/auth/"):
            return JSONResponse(status_code=422, content={"detail": "Invalid authentication request"},
                                headers={"Cache-Control": "no-store"})
        return await request_validation_exception_handler(request, exc)

    @application.exception_handler(DomainError)
    async def domain_error_handler(request, exc: DomainError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail},
                            headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})

    @application.get("/")
    def root():
        return {"name": "Nodum API", "status": "running"}

    @application.get("/health")
    def health():
        return {"status": "healthy"}

    return application


app = create_app()
