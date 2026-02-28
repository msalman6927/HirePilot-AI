# filepath: backend/routers/apply_router.py
# ══════════════════════════════════════════════════════════════
# Apply Router — HITL Preview + Approve Endpoints
# Rule 6: No email sent without hitl_approved == True
# ══════════════════════════════════════════════════════════════

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.job import Job
from backend.models.cv_version import CVVersion
from backend.agents.apply_agent import (
    PAUSED_STATES,
    generate_email_draft,
    hitl_gate_node,
    apply_node,
    log_hitl_decision,
)
from backend.agents.cv_tailoring_agent import (
    calculate_match_score,
    analyze as cv_analyze,
)

router = APIRouter()


# ── Pydantic Models ──────────────────────────────────────────

class HITLApproval(BaseModel):
    session_id: str
    edited_email_draft: str
    approved: bool


class PreviewResponse(BaseModel):
    session_id: str
    tailored_cv: Optional[dict] = None
    email_draft: str
    hr_email: str
    job_title: str
    company: str
    match_score: int


# ═══════════════════════════════════════════════════════════════
# GET /apply/preview/{job_id}
# Looks up job + latest CV, runs tailoring, generates email draft,
# saves paused state, returns preview for HITL review.
# ═══════════════════════════════════════════════════════════════

@router.get("/preview/{job_id}", response_model=PreviewResponse)
async def preview_application(job_id: int, session_id: str, db: Session = Depends(get_db)):
    """Preview the tailored application before sending."""

    # 1. Look up the job
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if not job.hr_email:
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} has no HR email. Cannot prepare application."
        )

    # 2. Look up latest CV version (most recent upload)
    cv_version = (
        db.query(CVVersion)
        .order_by(CVVersion.created_at.desc())
        .first()
    )
    if not cv_version:
        raise HTTPException(
            status_code=404,
            detail="No CV found. Upload a CV first."
        )

    parsed_cv = cv_version.parsed_data or {}

    # 3. Calculate match score
    job_dict = {
        "db_id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "platform": job.platform,
        "job_url": job.job_url,
        "description": job.description,
        "match_score": job.match_score,
        "hr_email": job.hr_email,
    }

    score_result = calculate_match_score(parsed_cv, job.description or "")
    match_score = score_result.get("current_match_score", 0)

    # 4. Run CV analysis / tailoring
    try:
        tailored_result = cv_analyze(
            session_id=session_id,
            parsed_cv=parsed_cv,
            job_title=job.title or "",
            job_description=job.description or ""
        )
    except Exception as e:
        # If analysis fails, still provide score-only preview
        tailored_result = {"scores": {"current_match_score": match_score}}

    # 5. Generate email draft
    email_draft = generate_email_draft(
        session_id=session_id,
        parsed_cv=parsed_cv,
        job=job_dict,
        tailored_result=tailored_result
    )

    # 6. Save paused state for later resumption
    paused_state = {
        "user_message": f"Apply to {job.title} at {job.company}",
        "thread_id": session_id,
        "cv_text": cv_version.raw_text,
        "cv_structured": parsed_cv,
        "cv_version_id": cv_version.id,
        "selected_job": job_dict,
        "tailored_cv_content": tailored_result,
        "tailored_email_draft": email_draft,
        "hitl_approved": False,
        "feedback_comments": None,
        "detected_intent": "apply",
        "agents_to_activate": ["apply"],
        "final_response": "",
        "agent_logs": [],
        "found_jobs": [],
        "job_search_criteria": None,
    }
    PAUSED_STATES[session_id] = paused_state

    return PreviewResponse(
        session_id=session_id,
        tailored_cv=tailored_result,
        email_draft=email_draft,
        hr_email=job.hr_email,
        job_title=job.title or "Unknown",
        company=job.company or "Unknown",
        match_score=match_score
    )


# ═══════════════════════════════════════════════════════════════
# POST /apply/approve
# Resumes the paused graph with HITL approval, sends the email.
# ═══════════════════════════════════════════════════════════════

@router.post("/approve")
async def approve_application(approval: HITLApproval):
    """Approve or reject the application. If approved, sends the email."""

    session_id = approval.session_id

    # 1. Retrieve paused state
    if session_id not in PAUSED_STATES:
        raise HTTPException(
            status_code=404,
            detail=f"No pending application for session {session_id}. Call /apply/preview first."
        )

    saved_state = PAUSED_STATES[session_id]

    if not approval.approved:
        # User rejected — clean up
        del PAUSED_STATES[session_id]
        log_hitl_decision(trace_id=session_id, approved=False)
        return {
            "status": "rejected",
            "message": "Application rejected by user.",
            "session_id": session_id
        }

    # 2. Update state with approval + edited draft
    saved_state["hitl_approved"] = True
    saved_state["tailored_email_draft"] = approval.edited_email_draft

    # 3. Run HITL gate (should pass now)
    state_after_gate = hitl_gate_node(saved_state)

    # 4. Run Apply node (sends email + saves to DB)
    final_state = apply_node(state_after_gate)

    # 5. Clean up paused state
    if session_id in PAUSED_STATES:
        del PAUSED_STATES[session_id]

    # 6. Log HITL decision to Langfuse
    log_hitl_decision(trace_id=session_id, approved=True)

    return {
        "status": "sent",
        "message": final_state.get("final_response", "Application sent."),
        "session_id": session_id,
        "agent_logs": final_state.get("agent_logs", [])
    }
