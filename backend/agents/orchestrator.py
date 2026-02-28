from typing import Dict, Any, List
import json
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from langfuse.decorators import observe
from langgraph.graph import StateGraph, END

# Use correct LangChain integration for Gemini
from backend.config import settings
from backend.tools.gemini_llm import get_llm, clean_json_response
from backend.agents.state import HirePilotState
from backend.agents.cv_parser_agent import cv_parser_node
from backend.agents.job_search_agent import job_search_node
from backend.agents.cv_tailoring_agent import cv_tailoring_node
from backend.agents.apply_agent import hitl_gate_node, apply_node

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. INTENT ROUTER NODE ---
@observe(name="IntentRouter")
def intent_router_node(state: HirePilotState) -> HirePilotState:
    """Classify user intent and route to appropriate agents."""
    logger.info("ROUTER: Analyzing user input...")
    
    # Initialize "agent_logs" if not present
    if "agent_logs" not in state:
        state["agent_logs"] = []

    session_id = state.get("thread_id", "default")
    llm, _ = get_llm(session_id, "IntentRouter")
    
    user_msg = state.get("user_message", "")
    
    system_prompt = """You are the Orchestrator for HirePilot-AI.
Your job is to read the user's message and decide which specialized agent needs to run.

AVAILABLE AGENTS:
1. "job_search_agent": User wants to find jobs (e.g., "Find Python jobs in Lahore").
2. "cv_parser_agent": User wants to analyze or parse a CV (usually triggered by upload, but can be explicit).
3. "cv_tailoring_agent": User wants to improve/tailor their CV for a specific job description.
4. "apply_agent": User wants to send an application email.
5. "interview_prep_agent": User wants interview questions or prep.
6. "general_responder": General chat, greetings, or questions about the system itself.

OUTPUT FORMAT:
Return a JSON object with:
{
    "primary_intent": "one of the agent names above",
    "agents_to_activate": ["list", "of", "agent", "names"],
    "reasoning": "Brief reason for this choice",
    "job_search_params": {"query": "extracted query", "location": "extracted location"} (only if job_search intent)
}

Ensure the "primary_intent" matches one of the exact names listed above.
Example: {"primary_intent": "job_search_agent", "agents_to_activate": ["job_search_agent"], "reasoning": "User asked for jobs", "job_search_params": ...}
"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_msg)
        ])
        
        cleaned_json = clean_json_response(response.content)
        parsed = json.loads(cleaned_json)
        
        state["detected_intent"] = parsed.get("primary_intent", "general_responder")
        state["agents_to_activate"] = parsed.get("agents_to_activate", ["general_responder"])
        
        # If job search, store parameters in state
        if parsed.get("job_search_params"):
             state["job_search_criteria"] = parsed["job_search_params"]

        logger.info(f"ROUTER: Detected intent '{state['detected_intent']}'")
        
    except Exception as e:
        logger.error(f"ROUTER: Parsing failed: {e}. Defaulting to general_responder.")
        state["detected_intent"] = "general_responder"
        state["agents_to_activate"] = ["general_responder"]
        
    return state

# --- 2. CONDITION LOGIC ---
def route_by_intent(state: HirePilotState) -> str:
    """Conditional edge logic based on detected intent."""
    intent = state.get("detected_intent", "general_responder")
    logger.info(f"ROUTING to: {intent}")
    return intent

# --- 3. AGENTS (Mock & Real) ---

@observe(name="InterviewPrepAgent")
def interview_prep_node(state: HirePilotState) -> HirePilotState:
    logger.info("AGENT: Interview Prep (Mock)")
    state.setdefault("agent_logs", []).append({"agent": "InterviewPrep", "message": "Exec mock prep"})
    return state

@observe(name="GeneralResponder")
def general_responder_node(state: HirePilotState) -> HirePilotState:
    """Handles general chit-chat using Gemini."""
    logger.info("AGENT: General Responder")
    
    session_id = state.get("thread_id", "default")
    llm, _ = get_llm(session_id, "GeneralResponder")
    
    user_msg = state.get("user_message", "")
    
    response = llm.invoke([
        SystemMessage(content="You are a helpful AI career assistant named HirePilot."),
        HumanMessage(content=user_msg)
    ])
    
    state["final_response"] = response.content
    state.setdefault("agent_logs", []).append({"agent": "GeneralResponder", "message": "Responded to user"})
    return state


# --- 4. RESPONDER / AGGREGATOR ---
@observe(name="FinalResponder")
def responder_node(state: HirePilotState) -> HirePilotState:
    """
    Aggregates results from whatever agents ran and formulates the final answer.
    """
    logger.info("RESPONDER: Formatting final answer...")
    
    intent = state.get("detected_intent")
    
    # If general responder ran, we already have final_response
    if intent == "general_responder":
        pass # already set
        
    elif intent == "job_search_agent":
        jobs = state.get("found_jobs", [])
        count = len(jobs)
        # Summarize jobs
        if count > 0:
            job_list_str = "\n".join([f"- {j['title']} at {j['company']}" for j in jobs[:3]])
            state["final_response"] = f"I found {count} jobs for you. Here are the top ones:\n{job_list_str}"
        else:
            state["final_response"] = "I searched for jobs but found none matching your criteria."

    elif intent == "cv_parser_agent":
        cv = state.get("cv_structured")
        name = cv.get("contact_info", {}).get("full_name", "Unknown") if cv else "Unknown"
        # Accessing nested dict safely for logging
        try:
            skills_count = len(cv.get("skills", []))
        except:
            skills_count = 0
        state["final_response"] = f"I successfully parsed the CV for {name}. Extracted {skills_count} skills."
        
    elif intent == "cv_tailoring_agent":
         state["final_response"] = "I have tailored your CV based on the job description. Please review the changes in the dashboard."
    
    elif intent == "apply_agent":
         state["final_response"] = "I have drafted an application email for you. Please approve it to send."

    elif intent == "interview_prep_agent":
         state["final_response"] = "Here are some interview questions to help you prepare..."
         
    else:
         if not state.get("final_response"):
            state["final_response"] = f"Processed request with {intent}."
         
    return state


# --- 5. BUILD GRAPH ---
def build_graph() -> StateGraph:
    """Constructs the LangGraph state machine."""
    workflow = StateGraph(HirePilotState)
    
    # Add Nodes
    workflow.add_node("intent_router", intent_router_node)
    
    # Placeholders/Mock Agents for now
    workflow.add_node("job_search_agent", job_search_node)
    
    # Use Wrapper for existing cv_parser_node to add logging if needed, or use directly
    # Since cv_parser_node is already decorated, we can use it.
    workflow.add_node("cv_parser_agent", cv_parser_node)
    
    workflow.add_node("cv_tailoring_agent", cv_tailoring_node)
    workflow.add_node("hitl_gate", hitl_gate_node)
    workflow.add_node("apply_agent", apply_node)
    workflow.add_node("interview_prep_agent", interview_prep_node)
    
    workflow.add_node("general_responder", general_responder_node)
    workflow.add_node("responder", responder_node)
    
    # Set Entry Point
    workflow.set_entry_point("intent_router")
    
    # Add Conditional Edges from Router
    workflow.add_conditional_edges(
        "intent_router",
        route_by_intent,
        {
            "job_search_agent": "job_search_agent",
            "cv_parser_agent": "cv_parser_agent",
            "cv_tailoring_agent": "cv_tailoring_agent",
            "apply_agent": "hitl_gate",
            "interview_prep_agent": "interview_prep_agent",
            "general_responder": "general_responder"
        }
    )
    
    # Add Edges to Responder
    workflow.add_edge("job_search_agent", "responder")
    workflow.add_edge("cv_parser_agent", "responder")
    workflow.add_edge("cv_tailoring_agent", "responder")
    workflow.add_edge("hitl_gate", "apply_agent")
    workflow.add_edge("apply_agent", "responder")
    workflow.add_edge("interview_prep_agent", "responder")
    workflow.add_edge("general_responder", "responder")
    
    # Add Edge to End
    workflow.add_edge("responder", END)
    
    # Compile
    app = workflow.compile()
    return app

# Expose the compiled graph
agent_graph = build_graph()
