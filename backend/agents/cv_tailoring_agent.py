# filepath: backend/agents/cv_tailoring_agent.py
# ══════════════════════════════════════════════════════════════════
# PORTED FROM BOWJOB: cv-jd-matching/improvement_engine.py
# See BOWJOB_REFERENCE.md Section 7 & Section 9 (TASK-018)
#
# VERBATIM methods (zero changes):
#   calculate_match_score, get_improvement_suggestions,
#   _generate_suggestion_summary, _count_projects,
#   _inject_projects_to_work_exp, _apply_project_guardrail,
#   _add_field_paths, _get_section_content
#
# REPLACED OpenAI → Gemini in:
#   analyze, _generate_missing_projects, chat_with_section
# ══════════════════════════════════════════════════════════════════

import json
import re
import uuid
import logging
from typing import Dict, Any, Optional, List

from langchain_core.messages import HumanMessage, SystemMessage
from langfuse.decorators import observe

from backend.tools.gemini_llm import get_llm, clean_json_response
from backend.agents.state import HirePilotState
from backend.agents._cv_improvement_schema import (
    CV_IMPROVEMENT_FUNCTION,
    CV_IMPROVEMENT_SYSTEM_PROMPT,
    CV_CHAT_SYSTEM_PROMPT,
    SECTION_CHAT_FUNCTION,
    SCORE_WEIGHTS,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# DETERMINISTIC SCORING — NO LLM — PORTED VERBATIM FROM BOWJOB
# ═══════════════════════════════════════════════════════════════

def calculate_match_score(
    parsed_cv: Dict[str, Any],
    job_description: str,
    jd_requirements: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    DETERMINISTIC score — NO LLM used here. Ported VERBATIM from BowJob.

    Scoring Formula (100 points total):
    - Skills: 35 points (matched_skills / required_skills * 35)
    - Experience: 25 points (cv_years / required_years * 25, capped at 25)
    - Education: 15 points (degree match level)
    - Projects: 15 points (0=0, 1=5, 2=10, 3+=15)
    - Keywords: 10 points (keywords_found / total_keywords * 10)
    """
    cv_text = json.dumps(parsed_cv).lower()
    jd_lower = job_description.lower()

    jd_keywords = set()
    words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9+#.-]*[a-zA-Z0-9]\b|\b[A-Z]{2,}\b', job_description)
    for word in words:
        if len(word) > 2:
            jd_keywords.add(word.lower())

    stop_words = {'the', 'and', 'for', 'with', 'our', 'you', 'your', 'will', 'are', 'have',
                  'has', 'been', 'being', 'was', 'were', 'can', 'could', 'should', 'would',
                  'may', 'might', 'must', 'shall', 'this', 'that', 'these', 'those', 'what',
                  'which', 'who', 'whom', 'where', 'when', 'why', 'how', 'all', 'each',
                  'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'than',
                  'too', 'very', 'just', 'also', 'only', 'own', 'same', 'into', 'over',
                  'after', 'before', 'between', 'under', 'again', 'further', 'then', 'once',
                  'here', 'there', 'about', 'above', 'below', 'from', 'down', 'out', 'off',
                  'through', 'during', 'including', 'include', 'includes', 'etc', 'ability',
                  'able', 'work', 'working', 'worked', 'team', 'teams', 'role', 'roles',
                  'job', 'jobs', 'position', 'positions', 'company', 'companies',
                  'organization', 'organizations', 'looking', 'seeking', 'ideal', 'candidate',
                  'candidates', 'opportunity', 'opportunities'}

    jd_keywords = {w for w in jd_keywords if w not in stop_words and len(w) > 2}

    # SKILLS SCORE (35 points)
    cv_skills = parsed_cv.get("skills", []) or []
    if isinstance(cv_skills, dict):
        all_skills = []
        for key, val in cv_skills.items():
            if isinstance(val, list):
                all_skills.extend(val)
        cv_skills = all_skills

    cv_skills_lower = [s.lower() if isinstance(s, str) else str(s).lower() for s in cv_skills]
    cv_skills_text = ' '.join(cv_skills_lower)

    skills_matched = 0
    for kw in jd_keywords:
        if kw in cv_skills_text or kw in cv_text:
            skills_matched += 1

    skills_score = min(35, (skills_matched / max(len(jd_keywords), 1)) * 35) if jd_keywords else 20

    # EXPERIENCE SCORE (25 points)
    cv_years = parsed_cv.get("total_years_of_experience", 0) or 0

    years_patterns = [
        r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*experience',
        r'minimum\s*(?:of)?\s*(\d+)\s*(?:years?|yrs?)',
        r'at\s*least\s*(\d+)\s*(?:years?|yrs?)',
        r'(\d+)\s*-\s*\d+\s*(?:years?|yrs?)',
    ]

    required_years = 0
    for pattern in years_patterns:
        match = re.search(pattern, jd_lower)
        if match:
            required_years = int(match.group(1))
            break

    if required_years > 0:
        experience_ratio = min(cv_years / required_years, 1.5)
        experience_score = min(25, experience_ratio * 25)
    else:
        experience_score = min(25, cv_years * 2.5) if cv_years > 0 else 10

    # EDUCATION SCORE (15 points)
    cv_education = parsed_cv.get("education", []) or []
    has_degree = len(cv_education) > 0
    degree_keywords = ['bachelor', 'master', 'phd', 'doctorate', 'degree', 'mba', 'bs', 'ms', 'ba', 'ma']
    jd_requires_degree = any(dk in jd_lower for dk in degree_keywords)

    if has_degree:
        education_score = 15
    elif not jd_requires_degree:
        education_score = 12
    else:
        education_score = 5

    # PROJECTS SCORE (15 points)
    cv_projects = parsed_cv.get("projects", []) or []
    project_count = len(cv_projects) if isinstance(cv_projects, list) else 0

    if project_count >= 3:
        projects_score = 15
    elif project_count == 2:
        projects_score = 10
    elif project_count == 1:
        projects_score = 5
    else:
        projects_score = 0

    # KEYWORDS SCORE (10 points)
    keywords_found = 0
    for kw in jd_keywords:
        if kw in cv_text:
            keywords_found += 1

    keywords_score = min(10, (keywords_found / max(len(jd_keywords), 1)) * 10) if jd_keywords else 5

    # TOTAL
    total_score = round(skills_score + experience_score + education_score + projects_score + keywords_score)

    if total_score >= 80:
        rating = "Excellent"
    elif total_score >= 65:
        rating = "Good"
    elif total_score >= 50:
        rating = "Fair"
    else:
        rating = "Poor"

    return {
        "current_match_score": total_score,
        "rating": rating,
        "breakdown": {
            "skills_score": round(skills_score, 1),
            "experience_score": round(experience_score, 1),
            "education_score": round(education_score, 1),
            "projects_score": round(projects_score, 1),
            "keywords_score": round(keywords_score, 1)
        },
        "details": {
            "jd_keywords_count": len(jd_keywords),
            "keywords_matched": keywords_found,
            "cv_years": cv_years,
            "required_years": required_years,
            "project_count": project_count,
            "skills_count": len(cv_skills)
        }
    }


# ═══════════════════════════════════════════════════════════════
# SUGGESTION ENGINE — PORTED VERBATIM FROM BOWJOB
# ═══════════════════════════════════════════════════════════════

def get_improvement_suggestions(
    parsed_cv: Dict[str, Any],
    job_description: str
) -> Dict[str, Any]:
    """Generate actionable suggestions based on score gaps. Ported VERBATIM."""
    scores = calculate_match_score(parsed_cv, job_description)
    breakdown = scores["breakdown"]
    details = scores["details"]

    suggestions = []
    priority = 1

    if breakdown["projects_score"] < 15:
        project_count = details["project_count"]
        needed = 3 - project_count
        if needed > 0:
            suggestions.append({
                "priority": priority,
                "section": "projects",
                "current_score": breakdown["projects_score"],
                "max_score": 15,
                "potential_gain": 15 - breakdown["projects_score"],
                "action": f"Add {needed} more project(s) to reach 3 total",
                "hint": "Ask me to 'add a project about [technology from JD]'",
                "impact": "high"
            })
            priority += 1

    if breakdown["skills_score"] < 28:
        suggestions.append({
            "priority": priority,
            "section": "skills",
            "current_score": breakdown["skills_score"],
            "max_score": 35,
            "potential_gain": min(10, 35 - breakdown["skills_score"]),
            "action": f"Add more JD-relevant skills ({details['keywords_matched']}/{details['jd_keywords_count']} keywords matched)",
            "hint": "Ask me to 'add missing skills from the JD'",
            "impact": "high"
        })
        priority += 1

    if breakdown["keywords_score"] < 7:
        suggestions.append({
            "priority": priority,
            "section": "work_experience",
            "current_score": breakdown["keywords_score"],
            "max_score": 10,
            "potential_gain": 10 - breakdown["keywords_score"],
            "action": "Inject more JD keywords into work experience descriptions",
            "hint": "Ask me to 'optimize my work experience for ATS'",
            "impact": "medium"
        })
        priority += 1

    if breakdown["experience_score"] < 20:
        if details["cv_years"] < details["required_years"]:
            suggestions.append({
                "priority": priority,
                "section": "work_experience",
                "current_score": breakdown["experience_score"],
                "max_score": 25,
                "potential_gain": 5,
                "action": f"Experience gap: you have {details['cv_years']} years, JD wants {details['required_years']}+",
                "hint": "Ask me to 'emphasize transferable skills'",
                "impact": "medium"
            })
            priority += 1

    if breakdown["education_score"] < 15:
        suggestions.append({
            "priority": priority,
            "section": "education",
            "current_score": breakdown["education_score"],
            "max_score": 15,
            "potential_gain": 15 - breakdown["education_score"],
            "action": "Add relevant education or certifications",
            "hint": "Ask me to 'suggest certifications for this role'",
            "impact": "low"
        })
        priority += 1

    total_potential = sum(s["potential_gain"] for s in suggestions)

    return {
        "current_score": scores["current_match_score"],
        "potential_score": min(95, scores["current_match_score"] + total_potential),
        "rating": scores["rating"],
        "suggestions": suggestions[:5],
        "summary": _generate_suggestion_summary(suggestions) if suggestions else "Your CV is well-optimized for this role!"
    }


def _generate_suggestion_summary(suggestions: list) -> str:
    """Generate human-readable summary. Ported VERBATIM."""
    if not suggestions:
        return "No major improvements needed."
    top = suggestions[0]
    if top["section"] == "projects":
        return f"Focus on adding projects to gain up to {top['potential_gain']} points."
    elif top["section"] == "skills":
        return f"Add more JD-relevant skills to gain up to {top['potential_gain']} points."
    elif top["section"] == "work_experience":
        return f"Enhance work experience with JD keywords to improve your score."
    else:
        return f"Focus on {top['section']} to improve your match score."


# ═══════════════════════════════════════════════════════════════
# PROJECT GUARDRAIL — PORTED VERBATIM FROM BOWJOB
# ═══════════════════════════════════════════════════════════════

def _count_projects(result: Dict[str, Any], parsed_cv: Dict[str, Any]) -> int:
    """Count total projects in analysis response. Ported VERBATIM."""
    cv_has_projects = parsed_cv.get("projects") not in [None, []]
    if cv_has_projects:
        modified = len(result.get("cv_sections", {}).get("projects", []))
        new = len(result.get("non_cv_sections", {}).get("projects", []))
        return modified + new
    else:
        count = 0
        for job in result.get("cv_sections", {}).get("work_experience", []):
            for desc in job.get("descriptions", []):
                if desc.get("tag") == "new":
                    count += 1
        return count


def _generate_missing_projects(
    session_id: str,
    parsed_cv: Dict[str, Any],
    job_title: str,
    job_description: str,
    needed: int,
    cv_has_projects: bool
) -> list:
    """Generate missing projects. REPLACED OpenAI with Gemini."""
    prompt = f"""Generate EXACTLY {needed} highly relevant project(s) for this job application.

JOB TITLE: {job_title}
JOB DESCRIPTION: {job_description}

REQUIREMENTS:
1. Each project must target a SPECIFIC JD requirement
2. Include realistic metrics and outcomes
3. Naturally inject 3-5 JD keywords into each description
4. Make projects impressive and recruiter-attractive

Return ONLY a JSON array of {needed} project(s) with fields:
name, description, technologies, reason, tag (always "new")

Return ONLY valid JSON. No markdown. No code blocks."""

    try:
        llm, _ = get_llm(session_id, "ProjectGenerator")
        response = llm.invoke([HumanMessage(content=prompt)])
        content = clean_json_response(response.content)
        data = json.loads(content)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "projects" in data:
            return data["projects"]
        else:
            return list(data.values())[0] if data else []
    except Exception as e:
        logger.error(f"Failed to generate projects: {e}")
        return []


def _inject_projects_to_work_exp(result: Dict[str, Any], projects: list) -> None:
    """Inject projects as new descriptions into work experience. Ported VERBATIM."""
    work_exp = result.get("cv_sections", {}).get("work_experience", [])
    if not work_exp:
        if "cv_sections" not in result:
            result["cv_sections"] = {}
        if "work_experience" not in result["cv_sections"]:
            result["cv_sections"]["work_experience"] = []
        work_exp = result["cv_sections"]["work_experience"]

    for project in projects:
        desc = {
            "content": f"{project.get('name', 'Project')}: {project.get('description', '')}",
            "tag": "new",
            "reason": project.get("reason", "Generated to meet JD requirements")
        }
        if work_exp:
            if "descriptions" not in work_exp[0]:
                work_exp[0]["descriptions"] = []
            work_exp[0]["descriptions"].append(desc)
        else:
            work_exp.append({
                "job_title": "Relevant Experience",
                "company": "Various Projects",
                "descriptions": [desc]
            })


def _apply_project_guardrail(
    session_id: str,
    result: Dict[str, Any],
    parsed_cv: Dict[str, Any],
    job_title: str,
    job_description: str
) -> Dict[str, Any]:
    """Ensure minimum 3 projects exist. Ported VERBATIM (Gemini replaces OpenAI in _generate_missing_projects)."""
    project_count = _count_projects(result, parsed_cv)
    cv_has_projects = parsed_cv.get("projects") not in [None, []]

    if project_count < 3:
        missing = 3 - project_count
        additional_projects = _generate_missing_projects(
            session_id, parsed_cv, job_title, job_description, missing, cv_has_projects
        )
        if additional_projects:
            if cv_has_projects:
                if "non_cv_sections" not in result:
                    result["non_cv_sections"] = {}
                if "projects" not in result["non_cv_sections"]:
                    result["non_cv_sections"]["projects"] = []
                result["non_cv_sections"]["projects"].extend(additional_projects)
            else:
                _inject_projects_to_work_exp(result, additional_projects)

    return result


# ═══════════════════════════════════════════════════════════════
# FIELD PATH GENERATOR — PORTED VERBATIM FROM BOWJOB
# ═══════════════════════════════════════════════════════════════

def _add_field_paths(result: Dict[str, Any], parsed_cv: Dict[str, Any]) -> Dict[str, Any]:
    """Add field_path to each recommendation so frontend knows where to apply changes. Ported VERBATIM."""
    cv_sections = result.get("cv_sections", {})
    non_cv_sections = result.get("non_cv_sections", {})

    if "title" in cv_sections and cv_sections["title"]:
        cv_sections["title"]["field_path"] = "title"

    if "professional_summary" in cv_sections and cv_sections["professional_summary"]:
        cv_sections["professional_summary"]["field_path"] = "professional_summary"

    if "work_experience" in cv_sections:
        for job_idx, job in enumerate(cv_sections.get("work_experience", [])):
            job["job_index"] = job_idx
            if "descriptions" in job:
                cv_work_exp = parsed_cv.get("work_experience", [])
                existing_desc_count = 0
                if job_idx < len(cv_work_exp):
                    existing_descs = cv_work_exp[job_idx].get("description", [])
                    if isinstance(existing_descs, list):
                        existing_desc_count = len(existing_descs)
                new_desc_idx = existing_desc_count
                for desc_idx, desc in enumerate(job["descriptions"]):
                    if desc.get("tag") == "modified" and desc.get("original_content"):
                        if job_idx < len(cv_work_exp):
                            cv_descs = cv_work_exp[job_idx].get("description", [])
                            if isinstance(cv_descs, list):
                                for i, cv_desc in enumerate(cv_descs):
                                    if cv_desc == desc.get("original_content"):
                                        desc["field_path"] = f"work_experience[{job_idx}].description[{i}]"
                                        break
                                else:
                                    desc["field_path"] = f"work_experience[{job_idx}].description[{desc_idx}]"
                    elif desc.get("tag") == "new":
                        desc["field_path"] = f"work_experience[{job_idx}].description[{new_desc_idx}]"
                        new_desc_idx += 1

    if "skills" in cv_sections:
        cv_skills = parsed_cv.get("skills", [])
        existing_count = len(cv_skills) if isinstance(cv_skills, list) else 0
        for idx, skill in enumerate(cv_sections.get("skills", [])):
            skill["field_path"] = f"skills[{existing_count + idx}]"

    if "projects" in cv_sections:
        for idx, project in enumerate(cv_sections.get("projects", [])):
            cv_projects = parsed_cv.get("projects", [])
            if cv_projects and project.get("original_name"):
                for i, cv_proj in enumerate(cv_projects):
                    if cv_proj.get("name") == project.get("original_name"):
                        project["field_path"] = f"projects[{i}]"
                        break
                else:
                    project["field_path"] = f"projects[{idx}]"
            else:
                project["field_path"] = f"projects[{idx}]"

    if "projects" in non_cv_sections:
        cv_projects = parsed_cv.get("projects", [])
        existing_count = len(cv_projects) if isinstance(cv_projects, list) else 0
        cv_section_projects = len(cv_sections.get("projects", []))
        start_idx = existing_count + cv_section_projects
        for idx, project in enumerate(non_cv_sections.get("projects", [])):
            project["field_path"] = f"projects[{start_idx + idx}]"

    if "certifications" in non_cv_sections:
        cv_certs = parsed_cv.get("certifications", [])
        existing_count = len(cv_certs) if isinstance(cv_certs, list) else 0
        for idx, cert in enumerate(non_cv_sections.get("certifications", [])):
            cert["field_path"] = f"certifications[{existing_count + idx}]"

    if "skills" in non_cv_sections:
        for idx, skill in enumerate(non_cv_sections.get("skills", [])):
            if isinstance(skill, dict):
                skill["field_path"] = f"skills[{idx}]"
            elif isinstance(skill, str):
                non_cv_sections["skills"][idx] = {
                    "content": skill,
                    "field_path": f"skills[{idx}]",
                    "tag": "new"
                }

    if "awards" in non_cv_sections:
        for idx, award in enumerate(non_cv_sections.get("awards", [])):
            award["field_path"] = f"awards_scholarships[{idx}]"

    if "professional_summary" in non_cv_sections and non_cv_sections["professional_summary"]:
        non_cv_sections["professional_summary"]["field_path"] = "professional_summary"

    return result


# ═══════════════════════════════════════════════════════════════
# SECTION CONTENT HELPER — PORTED VERBATIM FROM BOWJOB
# ═══════════════════════════════════════════════════════════════

def _get_section_content(parsed_cv: Dict[str, Any], section: str) -> Any:
    """Extract content for a specific section. Ported VERBATIM."""
    section_map = {
        "entire_resume": parsed_cv,
        "professional_summary": parsed_cv.get("professional_summary"),
        "work_experience": parsed_cv.get("work_experience"),
        "education": parsed_cv.get("education"),
        "skills": parsed_cv.get("skills"),
        "projects": parsed_cv.get("projects"),
        "certifications": parsed_cv.get("certifications"),
        "contact_info": parsed_cv.get("contact_info"),
        "title": parsed_cv.get("title"),
        "languages": parsed_cv.get("languages"),
        "awards_scholarships": parsed_cv.get("awards_scholarships"),
        "publications": parsed_cv.get("publications")
    }
    return section_map.get(section, parsed_cv)


# ═══════════════════════════════════════════════════════════════
# MAIN ANALYSIS — GEMINI REPLACES OPENAI tool_choice
# ═══════════════════════════════════════════════════════════════

@observe(name="CVAnalysis")
def analyze(
    session_id: str,
    parsed_cv: Dict[str, Any],
    job_title: str,
    job_description: str,
    options: Dict[str, bool] = None,
    instructions: str = None
) -> Dict[str, Any]:
    """Main analysis function. OpenAI tool_choice REPLACED with Gemini JSON prompt."""
    cv_text = json.dumps(parsed_cv, indent=2)

    user_instructions_section = ""
    if instructions and instructions.strip():
        user_instructions_section = f"""
PRIORITY OVERRIDE - USER CUSTOM INSTRUCTIONS:
{instructions}
"""

    # Build the JSON schema description for Gemini to follow
    schema_fields = CV_IMPROVEMENT_FUNCTION[0]["function"]["parameters"]["properties"].keys()
    required_fields = ", ".join(schema_fields)

    prompt = f"""{CV_IMPROVEMENT_SYSTEM_PROMPT}

Return ONLY a valid JSON object. No markdown. No code blocks. No explanation.

Required top-level keys:
{required_fields}

{user_instructions_section}

JOB TITLE: {job_title}

JOB DESCRIPTION:
{job_description}

PARSED CV DATA:
{cv_text}"""

    llm, _ = get_llm(session_id, "CVTailoringAgent")
    response = llm.invoke([HumanMessage(content=prompt)])
    clean = clean_json_response(response.content)

    try:
        result = json.loads(clean)
    except json.JSONDecodeError:
        # Attempt fix: remove trailing commas
        fixed = re.sub(r',(\s*[}\]])', r'\1', clean)
        result = json.loads(fixed)

    # Apply project guardrail (minimum 3 projects)
    result = _apply_project_guardrail(session_id, result, parsed_cv, job_title, job_description)

    # Add field paths for frontend
    result = _add_field_paths(result, parsed_cv)

    # Override scores with deterministic calculation (BowJob pattern)
    deterministic_scores = calculate_match_score(parsed_cv, job_description)
    result["scores"] = {
        "current_match_score": deterministic_scores["current_match_score"],
        "potential_score_after_changes": min(95, deterministic_scores["current_match_score"] + 20),
        "rating": deterministic_scores["rating"],
        "breakdown": deterministic_scores["breakdown"]
    }

    return result


# ═══════════════════════════════════════════════════════════════
# SECTION CHAT — GEMINI REPLACES OPENAI tool_choice
# ═══════════════════════════════════════════════════════════════

@observe(name="CVSectionChat")
def chat_with_section(
    session_id: str,
    message: str,
    section: str,
    session_context: Dict[str, Any]
) -> Dict[str, Any]:
    """Chat with section context. OpenAI REPLACED with Gemini JSON prompt."""
    job_title = session_context.get("job_title", "Unknown")
    job_description = session_context.get("job_description", "")
    parsed_cv = session_context.get("current_cv") or session_context.get("parsed_cv", {})
    chat_history = session_context.get("chat_history", [])
    section_content = _get_section_content(parsed_cv, section)

    system_prompt = f"""{CV_CHAT_SYSTEM_PROMPT}
CONTEXT:
- Job Title: {job_title}
- Current Section: {section}
- Section Content: {json.dumps(section_content, indent=2) if section_content else "Empty/Not available"}

JOB DESCRIPTION:
{job_description[:1500] if job_description else "Not provided"}

RULES:
1. If user is asking/brainstorming -> has_action = false
2. If user wants to change/add/remove -> has_action = true, include action with specific changes
3. Provide EXACT field paths and values that can be applied to the CV

Return ONLY a valid JSON object with keys: message, has_action, action (optional).
No markdown. No code blocks."""

    # Build conversation as single prompt (Gemini doesn't have multi-turn tool_choice)
    history_text = ""
    for msg in chat_history[-10:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        history_text += f"\n{role.upper()}: {content}"

    full_prompt = f"""{system_prompt}

CONVERSATION HISTORY:
{history_text}

USER: [Section: {section}] {message}

Respond as JSON:"""

    try:
        llm, _ = get_llm(session_id, "CVSectionChat")
        response = llm.invoke([HumanMessage(content=full_prompt)])
        clean = clean_json_response(response.content)
        result = json.loads(clean)
    except Exception as e:
        logger.error(f"Section chat failed: {e}")
        result = {"message": "I can help with that section. Could you be more specific?", "has_action": False}

    response_data = {
        "message": result.get("message", ""),
        "section": section,
        "session_id": session_id,
    }

    if result.get("has_action") and result.get("action"):
        action_data = result["action"]
        response_data["action"] = {
            "action_id": f"action_{uuid.uuid4().hex[:12]}",
            "action_type": action_data.get("action_type", "improve"),
            "section": section,
            "status": "pending",
            "description": action_data.get("description", "Apply suggested changes"),
            "changes": action_data.get("changes", []),
            "requires_confirmation": True
        }

    return response_data


# ═══════════════════════════════════════════════════════════════
# LANGGRAPH NODE — THE ORCHESTRATOR CALLS THIS
# ═══════════════════════════════════════════════════════════════

@observe(name="CVTailoringAgent")
def cv_tailoring_node(state: HirePilotState) -> HirePilotState:
    """
    LangGraph node for CV tailoring.
    Expects state to have: cv_structured, selected_job (with title + description).
    Produces: tailored_cv_content (the full analysis result).
    """
    logger.info("AGENT: CV Tailoring Agent Active")

    if "agent_logs" not in state:
        state["agent_logs"] = []

    session_id = state.get("thread_id", "default")
    parsed_cv = state.get("cv_structured")
    selected_job = state.get("selected_job")

    if not parsed_cv:
        state["agent_logs"].append({"agent": "CVTailoringAgent", "status": "error", "message": "No parsed CV in state"})
        state["final_response"] = "I need a parsed CV first. Please upload your CV before requesting tailoring."
        return state

    if not selected_job:
        state["agent_logs"].append({"agent": "CVTailoringAgent", "status": "error", "message": "No job selected"})
        state["final_response"] = "Please select a job to tailor your CV against. Search for jobs first."
        return state

    job_title = selected_job.get("title", "Unknown Position")
    job_description = selected_job.get("description", "")

    state["agent_logs"].append({
        "agent": "CVTailoringAgent",
        "status": "running",
        "message": f"Analyzing CV against '{job_title}'..."
    })

    try:
        # Run the full BowJob analysis
        result = analyze(
            session_id=session_id,
            parsed_cv=parsed_cv,
            job_title=job_title,
            job_description=job_description
        )

        # Store in state
        state["tailored_cv_content"] = result

        # Build human-readable response
        score = result.get("scores", {})
        current = score.get("current_match_score", 0)
        potential = score.get("potential_score_after_changes", 0)
        rating = score.get("rating", "Unknown")

        cv_mods = len(result.get("cv_sections", {}).get("work_experience", []))
        new_skills = len(result.get("cv_sections", {}).get("skills", []))
        feedback = result.get("overall_feedback", {})
        strengths = feedback.get("strengths", [])
        quick_wins = feedback.get("quick_wins", [])

        response_parts = [
            f"CV Analysis for **{job_title}**:",
            f"Current Match Score: {current}/100 ({rating})",
            f"Potential After Changes: {potential}/100",
            "",
        ]

        if strengths:
            response_parts.append("Strengths: " + ", ".join(strengths[:3]))
        if quick_wins:
            response_parts.append("Quick Wins: " + ", ".join(quick_wins[:3]))

        response_parts.append(f"\nI've prepared {cv_mods} work experience modifications and {new_skills} new skills to add.")
        response_parts.append("Please review the changes in the Application Prep dashboard before approving.")

        state["final_response"] = "\n".join(response_parts)

        state["agent_logs"].append({
            "agent": "CVTailoringAgent",
            "status": "completed",
            "message": f"Analysis complete. Score: {current} -> {potential}"
        })

    except Exception as e:
        logger.error(f"CV Tailoring failed: {e}", exc_info=True)
        state["agent_logs"].append({"agent": "CVTailoringAgent", "status": "error", "message": str(e)})
        state["final_response"] = f"CV tailoring encountered an error: {str(e)}"

    return state
