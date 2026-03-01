# filepath: backend/agents/interview_prep_agent.py
"""
Interview Prep Agent — Phase 6
Takes a selected job + parsed CV and generates comprehensive
interview preparation material via Gemini.
"""

import json
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from langfuse.decorators import observe, langfuse_context

from backend.agents.state import HirePilotState
from backend.tools.gemini_llm import get_llm, clean_json_response

logger = logging.getLogger(__name__)

# ── Gemini Prompt (from AGENT_DESIGN.md Section 8) ──────────────
JOB_PREP_PROMPT = """You are an expert interview coach and career advisor.

Given the candidate's CV and the job description, generate comprehensive interview preparation material.

Return a JSON object with these exact keys:
{{
    "technical_questions": [
        {{"question": "...", "model_answer": "...", "difficulty": "easy|medium|hard"}}
    ],
    "behavioral_questions": [
        {{"question": "...", "star_answer": {{"situation": "...", "task": "...", "action": "...", "result": "..."}}, "competency": "..."}}
    ],
    "skill_gaps": [
        {{"skill": "...", "importance": "critical|important|nice_to_have", "learning_resource": "...", "estimated_time": "..."}}
    ],
    "company_research": {{"what_to_know": ["..."], "questions_to_ask": ["..."]}},
    "salary_guidance": {{"range": "...", "negotiation_tips": ["..."]}},
    "day_one_tips": ["..."]
}}

RULES:
- Generate at least 5 technical questions (mix of easy/medium/hard).
- Generate at least 3 behavioral questions with full STAR answers.
- Identify real skill gaps between the CV and the job requirements.
- Be specific to the job title, company, and industry.
- All model answers should be detailed and actionable.
- Return ONLY valid JSON, no markdown fences.

JOB TITLE: {job_title}
COMPANY: {company}
JOB DESCRIPTION: {job_description}
CANDIDATE CV: {cv_summary}
"""


def _build_cv_summary(cv_structured: dict) -> str:
    """Flatten parsed CV into a concise text block for the prompt."""
    parts = []
    ci = cv_structured.get("contact_info", {})
    if ci.get("full_name"):
        parts.append(f"Name: {ci['full_name']}")

    summary = cv_structured.get("professional_summary", "")
    if summary:
        parts.append(f"Summary: {summary}")

    skills = cv_structured.get("skills", [])
    if skills:
        parts.append(f"Skills: {', '.join(skills)}")

    for exp in cv_structured.get("work_experience", []):
        line = f"- {exp.get('job_title', '')} at {exp.get('company', '')}"
        parts.append(line)

    for edu in cv_structured.get("education", []):
        line = f"- {edu.get('degree', '')} from {edu.get('institution', '')}"
        parts.append(line)

    for proj in cv_structured.get("projects", []):
        line = f"- Project: {proj.get('name', '')} — {proj.get('description', '')}"
        parts.append(line)

    certs = cv_structured.get("certifications", [])
    if certs:
        parts.append(f"Certifications: {', '.join(str(c) for c in certs)}")

    return "\n".join(parts) if parts else "No CV data available."


def _build_job_description(job: dict) -> str:
    """Build a job description string from a job dict."""
    parts = []
    if job.get("description"):
        parts.append(job["description"])
    if job.get("requirements"):
        reqs = job["requirements"]
        if isinstance(reqs, list):
            parts.append("Requirements: " + ", ".join(reqs))
        else:
            parts.append(f"Requirements: {reqs}")
    if job.get("responsibilities"):
        resps = job["responsibilities"]
        if isinstance(resps, list):
            parts.append("Responsibilities: " + ", ".join(resps))
        else:
            parts.append(f"Responsibilities: {resps}")
    return "\n".join(parts) if parts else "No description available."


# ── LangGraph Node ───────────────────────────────────────────────
@observe(name="InterviewPrepAgent")
def interview_prep_node(state: HirePilotState) -> HirePilotState:
    """
    Generate interview preparation material for the selected job
    using the candidate's parsed CV.
    """
    logger.info("AGENT: Interview Prep — starting")
    state.setdefault("agent_logs", [])
    state["agent_logs"].append({
        "agent": "InterviewPrep",
        "action": "Generating interview preparation material",
        "status": "running",
    })

    session_id = state.get("thread_id", "default")
    llm, _ = get_llm(session_id, "InterviewPrepAgent")

    # Gather inputs
    selected_job = state.get("selected_job") or {}
    cv_structured = state.get("cv_structured") or {}

    job_title = selected_job.get("title", "Software Engineer")
    company = selected_job.get("company", "Unknown Company")
    job_description = _build_job_description(selected_job)
    cv_summary = _build_cv_summary(cv_structured)

    prompt = JOB_PREP_PROMPT.format(
        job_title=job_title,
        company=company,
        job_description=job_description,
        cv_summary=cv_summary,
    )

    try:
        response = llm.invoke([
            SystemMessage(content="You are an expert interview coach. Return ONLY valid JSON."),
            HumanMessage(content=prompt),
        ])

        cleaned = clean_json_response(response.content)
        prep_data = json.loads(cleaned)

        # Ensure required keys exist with defaults
        prep_data.setdefault("technical_questions", [])
        prep_data.setdefault("behavioral_questions", [])
        prep_data.setdefault("skill_gaps", [])
        prep_data.setdefault("company_research", {"what_to_know": [], "questions_to_ask": []})
        prep_data.setdefault("salary_guidance", {"range": "Not available", "negotiation_tips": []})
        prep_data.setdefault("day_one_tips", [])

        # Attach metadata
        prep_data["job_title"] = job_title
        prep_data["company"] = company

        state["interview_prep"] = prep_data

        langfuse_context.update_current_observation(
            input={"job_title": job_title, "company": company},
            output={"sections": list(prep_data.keys()), "tech_q_count": len(prep_data["technical_questions"])},
        )

        state["agent_logs"].append({
            "agent": "InterviewPrep",
            "action": f"Generated {len(prep_data['technical_questions'])} technical + {len(prep_data['behavioral_questions'])} behavioral questions",
            "status": "completed",
        })
        logger.info("AGENT: Interview Prep — completed successfully")

    except Exception as e:
        logger.error(f"AGENT: Interview Prep — failed: {e}")
        state["interview_prep"] = None
        state["agent_logs"].append({
            "agent": "InterviewPrep",
            "action": f"Failed to generate prep: {str(e)[:200]}",
            "status": "failed",
        })

    return state


# ── Standalone function for direct API calls (prep_router) ───────
@observe(name="InterviewPrepDirect")
def generate_interview_prep(job: dict, cv_structured: dict, session_id: str = "direct") -> dict:
    """
    Standalone helper used by prep_router to generate interview prep
    without going through the full LangGraph pipeline.
    """
    llm, _ = get_llm(session_id, "InterviewPrepAgent")

    job_title = job.get("title", "Software Engineer")
    company = job.get("company", "Unknown Company")
    job_description = _build_job_description(job)
    cv_summary = _build_cv_summary(cv_structured)

    prompt = JOB_PREP_PROMPT.format(
        job_title=job_title,
        company=company,
        job_description=job_description,
        cv_summary=cv_summary,
    )

    response = llm.invoke([
        SystemMessage(content="You are an expert interview coach. Return ONLY valid JSON."),
        HumanMessage(content=prompt),
    ])

    cleaned = clean_json_response(response.content)
    prep_data = json.loads(cleaned)

    prep_data.setdefault("technical_questions", [])
    prep_data.setdefault("behavioral_questions", [])
    prep_data.setdefault("skill_gaps", [])
    prep_data.setdefault("company_research", {"what_to_know": [], "questions_to_ask": []})
    prep_data.setdefault("salary_guidance", {"range": "Not available", "negotiation_tips": []})
    prep_data.setdefault("day_one_tips", [])
    prep_data["job_title"] = job_title
    prep_data["company"] = company

    return prep_data
