from fastapi import FastAPI

from app.api.access import router as access_router


app = FastAPI(
    title="Nodum API",
    version="0.1.0",
)

app.include_router(access_router)


@app.get("/")
def root():
    return {
        "name": "Nodum API",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }