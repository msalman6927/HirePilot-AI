
import re
from typing import Tuple, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langfuse.callback import CallbackHandler
from backend.config import settings

def get_llm(session_id: str, agent_name: str, temperature: float = 0.3) -> Tuple[ChatGoogleGenerativeAI, CallbackHandler]:
    """
    Creates a Gemini LLM instance with a Langfuse callback handler already attached.
    
    Args:
        session_id: The session ID for grouping traces in Langfuse.
        agent_name: The name of the agent calling this LLM (used for metadata).
        temperature: The temperature for generation (default 0.3 for consistency).

    Returns:
        A tuple (llm, langfuse_handler).
        The llm is already configured with the callback.
    """
    
    langfuse_handler = CallbackHandler(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_HOST,
        session_id=session_id,
        metadata={"agent": agent_name},
        tags=[agent_name]
    )

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        google_api_key=settings.GEMINI_API_KEY,
        callbacks=[langfuse_handler],
        temperature=temperature,
        convert_system_message_to_human=True # Sometimes needed for older Gemini versions or specific prompts
    )

    return llm, langfuse_handler

def clean_json_response(text: str) -> str:
    """
    Removes markdown code fences (```json ... ```) from a string 
    and returns just the JSON content.
    """
    if not text:
        return ""
        
    # Remove ```json ... ``` or just ``` ... ```
    cleaned = re.sub(r'```(?:json)?\s*(.*?)\s*```', r'\1', text, flags=re.DOTALL)
    
    return cleaned.strip()
