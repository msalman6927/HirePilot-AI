from fastapi import FastAPI

from app.database import engine
from app.models import (  # noqa: F401 – ensure all models are registered
    User, Resume, ParsedProfile, Job, JobMatch, CustomizedResume, OutreachEmail,
)
from app.database import Base
from app.routers import users_router, resumes_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="HirePilot AI",
    description="Production-ready FastAPI backend for the HirePilot AI multi-agent job acquisition platform.",
    version="0.1.0",
)

app.include_router(users_router, prefix="/api/v1")
app.include_router(resumes_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
