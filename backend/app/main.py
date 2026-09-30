from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.sqlite_repository import SQLiteRepository
from app.services.errors import DomainError

from app.api.access import router as access_router
from app.api.guests import router as guests_router
from app.api.appointments import router as appointments_router
from app.api.emergencies import router as emergencies_router
from app.api.agent import router as agent_router
from app.services.agent_actions import PendingActionStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    repository = SQLiteRepository()
    repository.initialize()
    app.state.repository = repository
    app.state.agent_actions = PendingActionStore(repository)
    yield


app = FastAPI(
    title="Nodum API",
    version="0.1.0",
    lifespan=lifespan,
)


app.include_router(access_router)
app.include_router(guests_router)
app.include_router(appointments_router)
app.include_router(emergencies_router)
app.include_router(agent_router)


@app.exception_handler(DomainError)
async def domain_error_handler(request, exc: DomainError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/")
def root():
    return {
        "name": "Nodum API",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }
