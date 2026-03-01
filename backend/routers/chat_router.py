from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import logging
import uuid
from typing import Optional, Dict, Any, List

# --- Local Imports ---
# Import the compiled graph (agent_graph)
from backend.agents.orchestrator import agent_graph
from backend.agents.state import HirePilotState
from backend.database import SessionLocal
from backend.models.agent_log import AgentLog

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class ChatRequest(BaseModel):
    message: str = Field(..., description="User's input message")
    thread_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Conversation ID")
    # context can include 'cv_data', 'job_data' etc.
    context: Dict[str, Any] = Field(default={}, description="Additional context if any")

class ChatResponse(BaseModel):
    response: str
    thread_id: str
    detected_intent: Optional[str] = None
    agent_logs: Optional[List[dict]] = None
    found_jobs: Optional[List[dict]] = None
    email_draft: Optional[str] = None

@router.post("/", response_model=ChatResponse)
async def analyze_and_chat(request: ChatRequest):
    """
    Main chat endpoint that routes user input through the HirePilot Orchestrator Graph.
    """
    try:
        # 1. Initialize State
        # We start with the user message and thread_id
        current_state = {
            "messages": [], # Can expand later to load history
            "user_message": request.message,
            "thread_id": request.thread_id,
            "agent_logs": [], # Initialize empty
            "final_response": None,
            "detected_intent": None
            # Add existing context if any (e.g., CV data already uploaded)
        }
        
        # Merge context from request into state if keys match HirePilotState
        # For simplicity, we just put it into state. Ideally filter by keys.
        current_state.update(request.context)
        
        logger.info(f"Processing chat request for thread {request.thread_id}: {request.message[:50]}...")
        
        # 2. Invoke Graph
        # This runs the 'intent_router' -> 'specific_agent' -> 'responder' flow
        final_state = agent_graph.invoke(current_state)
        
        # 3. Extract Response
        # The 'responder' node should have populated 'final_response'
        response_text = final_state.get("final_response")
        if not response_text:
            response_text = "I'm sorry, I couldn't process your request."

        detected_intent = final_state.get("detected_intent", "unknown")
        # Ensure agent_logs is a list of dicts, it might be a list of strings if legacy code remains
        agent_logs = final_state.get("agent_logs", [])

        # 4. Persist agent_logs to SQLite for Dashboard Activity Feed
        try:
            db = SessionLocal()
            for log_entry in agent_logs:
                db_log = AgentLog(
                    session_id=request.thread_id,
                    agent_name=log_entry.get("agent", log_entry.get("agent_name", "Unknown")),
                    action=log_entry.get("action", log_entry.get("message", "")),
                    status=log_entry.get("status", "completed"),
                )
                db.add(db_log)
            db.commit()
            db.close()
        except Exception as log_err:
            logger.warning(f"Failed to persist agent logs: {log_err}")

        return ChatResponse(
            response=response_text,
            thread_id=request.thread_id,
            detected_intent=detected_intent,
            agent_logs=agent_logs,
            found_jobs=final_state.get("found_jobs"),
            email_draft=final_state.get("tailored_email_draft"),
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        # Return a sanitized error message
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
