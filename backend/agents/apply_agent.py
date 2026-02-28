# filepath: backend/agents/apply_agent.py
# ══════════════════════════════════════════════════════════════
# Apply Agent + HITL Gate Node
# Handles: email draft generation, HITL approval check, email sending
# Rule 6 from AI_CONTEXT: No email sent without hitl_approved == True
# ══════════════════════════════════════════════════════════════

import json
import logging
from typing import Dict, Any
from datetime import datetime

from langchain_core.messages import HumanMessage
from langfuse.decorators import observe

from backend.tools.gemini_llm import get_llm, clean_json_response
from backend.tools.gmail_tool import send_email
from backend.agents.state import HirePilotState
from backend.database import SessionLocal
from backend.models.application import Application

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── In-memory store for paused graph states (HITL pattern) ──
# Key: session_id, Value: full state dict
PAUSED_STATES: Dict[str, Dict[str, Any]] = {}


# ═══════════════════════════════════════════════════════════════
# EMAIL DRAFT GENERATION
# ═══════════════════════════════════════════════════════════════

@observe(name="EmailDraftGenerator")
def generate_email_draft(
    session_id: str,
    parsed_cv: Dict[str, Any],
    job: Dict[str, Any],
    tailored_result: Dict[str, Any]
) -> str:
    """Generate a professional application email using Gemini."""
    llm, _ = get_llm(session_id, "EmailDraftGenerator")

    contact = parsed_cv.get("contact_info", {})
    name = contact.get("full_name", "Applicant")
    email = contact.get("email", "")

    job_title = job.get("title", "the position")
    company = job.get("company", "your company")

    # Extract key strengths from tailoring result
    strengths = tailored_result.get("overall_feedback", {}).get("strengths", [])
    strengths_text = ", ".join(strengths[:3]) if strengths else "strong technical skills and relevant experience"

    score = tailored_result.get("scores", {}).get("current_match_score", 0)

    prompt = f"""Write a professional job application email.

APPLICANT: {name} ({email})
JOB TITLE: {job_title}
COMPANY: {company}
KEY STRENGTHS: {strengths_text}
MATCH SCORE: {score}/100

RULES:
1. Keep it concise (150-250 words)
2. Professional but warm tone
3. Mention 2-3 specific strengths relevant to the role
4. Express genuine interest in the company
5. End with a call to action (interview request)
6. Do NOT include subject line — just the email body
7. Do NOT use placeholder brackets like [Company Name]

Return ONLY the email body text, no JSON, no markdown."""

    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content.strip()


# ═══════════════════════════════════════════════════════════════
# HITL GATE NODE — THE NON-NEGOTIABLE CHECKPOINT
# ═══════════════════════════════════════════════════════════════

@observe(name="HITLGate")
def hitl_gate_node(state: HirePilotState) -> HirePilotState:
    """
    Human-in-the-Loop gate. Checks if the user has approved sending.
    If not approved, pauses the pipeline and stores state for later resumption.
    """
    logger.info("HITL GATE: Checking approval status...")

    if "agent_logs" not in state:
        state["agent_logs"] = []

    approved = state.get("hitl_approved", False)

    if approved:
        logger.info("HITL GATE: Approved — proceeding to send.")
        state["agent_logs"].append({
            "agent": "HITLGate",
            "status": "approved",
            "message": "User approved the application. Proceeding to send."
        })
    else:
        logger.info("HITL GATE: Not approved — pausing pipeline.")
        session_id = state.get("thread_id", "default")

        # Store paused state for later resumption via /apply/approve
        PAUSED_STATES[session_id] = dict(state)

        state["agent_logs"].append({
            "agent": "HITLGate",
            "status": "paused",
            "message": "Waiting for user approval. Review tailored CV and email draft."
        })
        state["final_response"] = (
            "Your application is ready for review. "
            "Please check the tailored CV and email draft in the Application Prep page, "
            "then approve to send."
        )

    return state


# ═══════════════════════════════════════════════════════════════
# APPLY NODE — SENDS THE EMAIL (only if HITL approved)
# ═══════════════════════════════════════════════════════════════

@observe(name="ApplyAgent")
def apply_node(state: HirePilotState) -> HirePilotState:
    """
    Sends the application email via Gmail and records in SQLite.
    Only runs if hitl_approved == True.
    """
    logger.info("AGENT: Apply Agent Active")

    if "agent_logs" not in state:
        state["agent_logs"] = []

    # Double-check HITL approval (defense in depth)
    if not state.get("hitl_approved", False):
        state["final_response"] = "Cannot send email — approval is required first."
        state["agent_logs"].append({
            "agent": "ApplyAgent",
            "status": "blocked",
            "message": "Attempted to send without HITL approval."
        })
        return state

    session_id = state.get("thread_id", "default")
    selected_job = state.get("selected_job", {})
    email_draft = state.get("tailored_email_draft", "")
    hr_email = selected_job.get("hr_email", "")

    if not hr_email:
        state["final_response"] = "No HR email found for this job. Cannot send application."
        state["agent_logs"].append({
            "agent": "ApplyAgent",
            "status": "error",
            "message": "Missing HR email address."
        })
        return state

    if not email_draft:
        state["final_response"] = "No email draft found. Please generate one first."
        state["agent_logs"].append({
            "agent": "ApplyAgent",
            "status": "error",
            "message": "Missing email draft."
        })
        return state

    job_title = selected_job.get("title", "Position")
    company = selected_job.get("company", "Company")
    subject = f"Application for {job_title} — {state.get('cv_structured', {}).get('contact_info', {}).get('full_name', 'Applicant')}"

    state["agent_logs"].append({
        "agent": "ApplyAgent",
        "status": "running",
        "message": f"Sending application to {hr_email} for {job_title} at {company}..."
    })

    try:
        # Send via Gmail
        result = send_email(to=hr_email, subject=subject, body=email_draft)
        message_id = result.get("id", "unknown")

        # Save to SQLite
        db = SessionLocal()
        try:
            application = Application(
                job_id=selected_job.get("db_id"),  # DB row id if available
                cv_version_id=state.get("cv_version_id"),
                tailored_cv=state.get("tailored_cv_content"),
                email_draft=email_draft,
                hr_email=hr_email,
                sent_at=datetime.utcnow(),
                status="Sent"
            )
            db.add(application)
            db.commit()
            db.refresh(application)
            application_id = application.id
        finally:
            db.close()

        state["final_response"] = (
            f"Application sent successfully to {hr_email} for {job_title} at {company}. "
            f"Gmail Message ID: {message_id}. Application ID: {application_id}."
        )
        state["agent_logs"].append({
            "agent": "ApplyAgent",
            "status": "completed",
            "message": f"Email sent. Application #{application_id} recorded."
        })

    except Exception as e:
        logger.error(f"Apply Agent failed: {e}", exc_info=True)
        state["final_response"] = f"Failed to send application: {str(e)}"
        state["agent_logs"].append({
            "agent": "ApplyAgent",
            "status": "error",
            "message": str(e)
        })

    return state


# ═══════════════════════════════════════════════════════════════
# LANGFUSE HITL SCORE LOGGING
# ═══════════════════════════════════════════════════════════════

def log_hitl_decision(trace_id: str, approved: bool):
    """Log HITL decision as a Langfuse score event."""
    try:
        from langfuse import Langfuse
        from backend.config import settings

        langfuse = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST
        )
        langfuse.score(
            trace_id=trace_id,
            name="hitl_approval",
            value=1.0 if approved else 0.0,
            comment=f"User {'approved' if approved else 'rejected'} the application"
        )
        langfuse.flush()
        logger.info(f"HITL decision logged to Langfuse: approved={approved}")
    except Exception as e:
        logger.warning(f"Failed to log HITL decision to Langfuse: {e}")
