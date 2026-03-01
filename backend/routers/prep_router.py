# filepath: backend/routers/prep_router.py
"""
Interview Prep Router — GET /prep/{job_id}
Fetches the job + latest CV from SQLite and generates interview prep material.
"""

from fastapi import APIRouter, HTTPException
from backend.database import SessionLocal
from backend.models.job import Job
from backend.models.cv_version import CVVersion
from backend.agents.interview_prep_agent import generate_interview_prep

router = APIRouter()


@router.get("/{job_id}")
async def get_interview_prep(job_id: int):
    """Generate interview preparation material for a specific job."""
    db = SessionLocal()
    try:
        # Fetch the job
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail=f"Job with id {job_id} not found")

        # Fetch the latest CV version
        cv_version = db.query(CVVersion).order_by(CVVersion.id.desc()).first()
        if not cv_version or not cv_version.parsed_data:
            raise HTTPException(
                status_code=404,
                detail="No parsed CV found. Please upload a CV first."
            )

        # Build job dict from DB model
        job_dict = {
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "description": job.description or "",
            "platform": job.platform,
            "job_url": job.job_url,
        }

        cv_structured = cv_version.parsed_data

        # Generate prep — calls Gemini
        prep_data = generate_interview_prep(
            job=job_dict,
            cv_structured=cv_structured,
            session_id=f"prep-{job_id}",
        )

        return prep_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Interview prep generation failed: {str(e)}")
    finally:
        db.close()
