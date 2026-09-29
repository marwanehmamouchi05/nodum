from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.repository import create_demo_repository
from app.services.errors import DomainError

from app.api.access import router as access_router
from app.api.guests import router as guests_router


app = FastAPI(
    title="Nodum API",
    version="0.1.0",
)


app.include_router(access_router)
app.include_router(guests_router)
app.state.repository = create_demo_repository()


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
