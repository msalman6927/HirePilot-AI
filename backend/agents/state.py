# filepath: backend/agents/state.py
from typing import TypedDict, List, Dict, Any, Optional

class HirePilotState(TypedDict):
    """
    The shared state object for the LangGraph workflow.
    """
    # User Input
    user_message: str
    
    # Session / Context
    thread_id: str
    
    # CV Data (Parsed from BowJob logic)
    cv_text: Optional[str]
    cv_structured: Optional[Dict[str, Any]]  # The JSON schema
    
    # Job Data
    job_search_criteria: Optional[Dict[str, Any]]
    found_jobs: List[Dict[str, Any]]
    selected_job: Optional[Dict[str, Any]]
    
    # Tailoring Artifacts
    tailored_cv_content: Optional[Dict[str, Any]] # cv_sections
    tailored_email_draft: Optional[str]           # non_cv_sections (email)
    
    # HITL Control
    hitl_approved: bool
    feedback_comments: Optional[str]
    
    # Execution & Routing
    detected_intent: str
    agents_to_activate: List[str]
    final_response: str
    agent_logs: List[Dict[str, Any]]  # Runtime logs for frontend + observability
