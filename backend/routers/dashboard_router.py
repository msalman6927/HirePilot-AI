# filepath: backend/routers/dashboard_router.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional

from backend.database import get_db
from backend.models.cv_version import CVVersion
from backend.models.job import Job
from backend.models.application import Application
from backend.models.agent_log import AgentLog

router = APIRouter()

STATUS_COLORS = {
    "Sent": "blue",
    "Opened": "yellow",
    "Interview": "green",
    "Rejected": "red",
}


@router.get("/cv-versions")
def get_cv_versions(db: Session = Depends(get_db)):
    """All CV versions ordered by created_at desc."""
    versions = db.query(CVVersion).order_by(desc(CVVersion.created_at)).all()
    return [
        {
            "id": v.id,
            "filename": v.filename,
            "created_at": str(v.created_at) if v.created_at else None,
            "skills_count": len(v.parsed_data.get("skills", []) or []) if v.parsed_data else 0,
        }
        for v in versions
    ]


@router.get("/applications")
def get_applications(db: Session = Depends(get_db)):
    """All applications joined with jobs table."""
    apps = (
        db.query(Application)
        .order_by(desc(Application.sent_at))
        .all()
    )
    result = []
    for app in apps:
        job = app.job
        result.append({
            "id": app.id,
            "job_title": job.title if job else "Unknown",
            "company": job.company if job else "Unknown",
            "hr_email": app.hr_email,
            "sent_at": str(app.sent_at) if app.sent_at else None,
            "status": app.status,
            "status_color": STATUS_COLORS.get(app.status, "gray"),
        })
    return result


@router.get("/logs")
def get_agent_logs(session_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Agent logs for a session, ordered by created_at asc."""
    query = db.query(AgentLog)
    if session_id:
        query = query.filter(AgentLog.session_id == session_id)
    logs = query.order_by(AgentLog.created_at.asc()).all()
    return [
        {
            "id": log.id,
            "session_id": log.session_id,
            "agent_name": log.agent_name,
            "action": log.action,
            "status": log.status,
            "created_at": str(log.created_at) if log.created_at else None,
        }
        for log in logs
    ]


@router.get("/jobs")
def get_all_jobs(db: Session = Depends(get_db)):
    """All jobs for dashboard view."""
    jobs = db.query(Job).order_by(desc(Job.fetched_at)).all()
    return [
        {
            "id": j.id,
            "session_id": j.session_id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "platform": j.platform,
            "match_score": j.match_score,
            "fetched_at": str(j.fetched_at) if j.fetched_at else None,
        }
        for j in jobs
    ]
