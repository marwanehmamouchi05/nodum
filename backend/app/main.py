import sqlite3
from datetime import datetime, timezone
from fastapi.exceptions import RequestValidationError
from app.api.operator import require_production_operator
from app.api.authorization import router as authorization_router, authorize_application_request
from app.api.auth import router as auth_router
from app.api.structure import router as structure_router
from app.api.admin import router as admin_router
from app.api.manager import router as manager_router
from app.api.resident import router as resident_router
from app.api.business_workspace import router as business_workspace_router
from app.api.demo import router as demo_router
from app.services.auth import bootstrap_user
from app.config import boolean
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import AppSettings, ConfigurationError, validate_startup
from app.sqlite_repository import SQLiteRepository
from app.services.errors import DomainError
from app.request_limits import RequestLimitsMiddleware
from app.abuse_protection import UsageGuard, TrafficLimitsMiddleware

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
        from app.services.authorization import authorization_mode
        repository.initialize(seed_demo=authorization_mode() == "legacy_demo")
    except (ValueError, OSError, RuntimeError, sqlite3.Error):
        raise ConfigurationError("Database startup failed; check DATABASE_URL, storage permissions and schema version") from None
    if boolean("NODUM_JUDGE_DEMO"):
        from app.judge_demo import prepare_judge_demo
        prepare_judge_demo(repository, datetime.now(timezone.utc))
    else:
        bootstrap_user(repository, datetime.now(timezone.utc))
    app.state.repository = repository
    app.state.agent_actions = PendingActionStore(repository)
    app.state.usage_guard = None
    if boolean("NODUM_ABUSE_PROTECTION"):
        import os
        database = os.environ.get("DATABASE_URL", "")
        if not database.startswith("sqlite:///"):
            raise ConfigurationError("Abuse protection requires persistent SQLite storage")
        ledger = Path(database.removeprefix("sqlite:///")).with_name("nodum-ai-usage.db")
        if not ledger.is_absolute():
            raise ConfigurationError("Abuse protection requires an absolute database path")
        app.state.usage_guard = UsageGuard(ledger)
    yield


def create_app():
    settings = AppSettings.from_env()
    production = settings.environment == "production"
    application = FastAPI(title="Nodum API", version="0.1.0", lifespan=lifespan,
                          docs_url=None if production else "/docs",
                          redoc_url=None if production else "/redoc",
                          openapi_url=None if production else "/openapi.json")
    application.add_middleware(
        CORSMiddleware, allow_origins=list(settings.cors_origins),
        allow_credentials=settings.cors_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    )
    application.add_middleware(RequestLimitsMiddleware)
    application.add_middleware(TrafficLimitsMiddleware)
    for router in (access_router, guests_router, appointments_router,
                   emergencies_router, agent_router, ring_router, building_router, auth_router, authorization_router):
        guards = [] if router in (auth_router, authorization_router) else [Depends(authorize_application_request)]
        if router not in (ring_router, auth_router, authorization_router):
            guards.append(Depends(require_production_operator))
        application.include_router(router, dependencies=guards)

    application.include_router(structure_router)
    application.include_router(admin_router)
    application.include_router(manager_router)
    application.include_router(resident_router)
    application.include_router(business_workspace_router)
    application.include_router(demo_router)

    @application.middleware("http")
    async def private_auth_responses(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(request, exc):
        if request.url.path.startswith("/auth/"):
            return JSONResponse(status_code=422, content={"detail": "Invalid authentication request"},
                                headers={"Cache-Control": "no-store"})
        # Pydantic's input/context can contain submitted credentials or PII.
        return JSONResponse(status_code=422, content={"detail": [
            {key: error[key] for key in ("loc", "msg", "type")} for error in exc.errors()
        ]}, headers={"Cache-Control": "no-store"})

    @application.exception_handler(DomainError)
    async def domain_error_handler(request, exc: DomainError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail},
                            headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})

    frontend = Path(__file__).resolve().parent / "web" / "product"
    has_frontend = (frontend / "index.html").is_file()
    if has_frontend:
        application.mount("/app", StaticFiles(directory=frontend, html=True), name="product")

    @application.get("/")
    def root():
        if has_frontend:
            return RedirectResponse("/app/", status_code=307)
        return {"name": "Nodum API", "status": "running"}

    @application.get("/health")
    def health():
        return {"status": "healthy"}

    return application


app = create_app()
