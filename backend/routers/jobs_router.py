# filepath: backend/routers/jobs_router.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional

from backend.database import get_db
from backend.models.job import Job

router = APIRouter()


@router.get("/")
def get_jobs(session_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Get jobs, optionally filtered by session_id."""
    query = db.query(Job)
    if session_id:
        query = query.filter(Job.session_id == session_id)
    jobs = query.order_by(desc(Job.match_score)).all()
    return [
        {
            "id": j.id,
            "session_id": j.session_id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "platform": j.platform,
            "job_url": j.job_url,
            "description": j.description,
            "match_score": j.match_score,
            "hr_email": j.hr_email,
            "fetched_at": str(j.fetched_at) if j.fetched_at else None,
        }
        for j in jobs
    ]


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get a single job by ID."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "session_id": job.session_id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "platform": job.platform,
        "job_url": job.job_url,
        "description": job.description,
        "match_score": job.match_score,
        "hr_email": job.hr_email,
        "fetched_at": str(job.fetched_at) if job.fetched_at else None,
    }
