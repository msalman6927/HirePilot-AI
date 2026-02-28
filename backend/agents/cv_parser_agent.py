import fitz  # PyMuPDF
import docx
import json
import logging
import os
from langchain_core.messages import HumanMessage
from langfuse.decorators import observe
from typing import Dict, Any, Optional

from backend.agents.state import HirePilotState
from backend.tools.gemini_llm import get_llm, clean_json_response
from backend.agents._cv_schema import CV_SYSTEM_PROMPT, CV_EXTRACTION_SCHEMA

# Configure logging
logger = logging.getLogger(__name__)

def extract_text_from_pdf(filepath: str) -> str:
    """Extract text content from a PDF file using PyMuPDF."""
    try:
        text = ""
        with fitz.open(filepath) as doc:
            for page in doc:
                text += page.get_text()
        return text
    except Exception as e:
        logger.error(f"Error reading PDF {filepath}: {str(e)}")
        raise

def extract_text_from_docx(filepath: str) -> str:
    """Extract text content from a DOCX file using python-docx."""
    try:
        doc = docx.Document(filepath)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    except Exception as e:
        logger.error(f"Error reading DOCX {filepath}: {str(e)}")
        raise

@observe(name="CVParserAgent")
def cv_parser_node(state: HirePilotState) -> HirePilotState:
    """
    LangGraph node that parses CV text into structured JSON using the BowJob schema.
    """
    logger.info("Starting CV parsing...")
    
    # 1. Get raw text from state
    # Note: State definition uses `cv_text` (from backend/agents/state.py check)
    cv_text = state.get("cv_text")
    
    if not cv_text:
        logger.warning("No CV text found in state.")
        return state

    # 2. Initialize LLM
    # Use session_id if available, otherwise default
    session_id = state.get("thread_id", "default_session")
    llm, _ = get_llm(session_id, "CVParserAgent")

    # 3. Construct Prompt
    # We use the system prompt + user message approach
    # Since specific system prompt usage might vary by LLM, we'll prepend it or use SystemMessage if supported.
    # Given get_llm returns a ChatGoogleGenerativeAI, we can use SystemMessage.
    # However, the prompt instructions say "build a prompt string that includes CV_SYSTEM_PROMPT...".
    
    # Let's construct a direct prompt string for simplicity and robustness with Gemini 2.5
    prompt_content = f"""{CV_SYSTEM_PROMPT}

You must return a valid JSON object matching the schema below. 
Do not assume any schema. Use the one provided here:

{json.dumps(CV_EXTRACTION_SCHEMA, indent=2)}

Ensure the output is pure JSON.

Here is the CV text to parse:
{cv_text}
"""

    # 4. Invoke LLM
    try:
        response = llm.invoke([HumanMessage(content=prompt_content)])
        
        # 5. Parse Response
        cleaned_json = clean_json_response(response.content)
        parsed_data = json.loads(cleaned_json)
        
        # 6. Update State
        # In backend/agents/state.py, the field is `cv_structured`
        state["cv_structured"] = parsed_data
        
        # Log success
        if hasattr(state, "agent_logs"): # Check if agent_logs exists in state schema, otherwise skip or add
             # state.py showed: user_message, thread_id, cv_text, cv_structured, job_search_criteria, found_jobs.
             # It did NOT show agent_logs. I will check state.py again if I need to add it.
             pass

        logger.info("CV parsing completed successfully.")
        
    except Exception as e:
        logger.error(f"Error during CV parsing: {e}")
        # Optionally handle error state
        
    return state
