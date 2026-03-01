# filepath: backend/main.py
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from backend.database import engine, Base
from backend.routers import cv_router, chat_router, apply_router
from backend.routers import dashboard_router, jobs_router, prep_router

# Initialize DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="HirePilot-AI Backend")

# CORS (Allow frontend to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROUTES ---
app.include_router(cv_router.router, prefix="/cv", tags=["CV"])
app.include_router(chat_router.router, prefix="/chat", tags=["Chat"])
app.include_router(apply_router.router, prefix="/apply", tags=["Apply"])
app.include_router(dashboard_router.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(jobs_router.router, prefix="/jobs", tags=["Jobs"])
app.include_router(prep_router.router, prefix="/prep", tags=["Interview Prep"])

@app.get("/")
def health_check():
    return {"status": "ok", "service": "HirePilot-AI"}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
