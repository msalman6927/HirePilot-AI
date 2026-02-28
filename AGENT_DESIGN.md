# AGENT_DESIGN.md
# HirePilot-AI — Agent Design Specification
**Version:** 1.0.0 | **Last Updated:** 2026-02-28

---

## 1. Agent Design Philosophy

Every agent in this system is a **single-responsibility unit** — it does exactly one thing well and hands off its result to the next agent via the shared LangGraph state. Think of each agent like a specialized department in a company: the Job Search department finds vacancies, the CV department tailors applications, the HR department sends emails. The Orchestrator is the manager who decides which departments to activate based on the employee's (user's) request.

Agents are implemented as **LangGraph node functions** — plain Python functions that take a `HirePilotState` dict, do their work, and return an updated `HirePilotState` dict. This makes them individually testable, replaceable, and easily understood by GitHub Copilot.

---

## 2. Agent 0: Orchestrator / Intent Router

**File:** `backend/agents/orchestrator.py`

The Orchestrator is not really a separate "agent" in the way the others are — it is the LangGraph `StateGraph` itself plus an Intent Router node that uses Gemini to classify the user's message.

The intent detection is a simple Gemini call with a structured output. Given a user message like "Find me data science jobs in Karachi and prepare me for interviews," Gemini must return a JSON object specifying which agents to activate and in what order.

```python
# Gemini prompt for intent detection
INTENT_PROMPT = """
You are an intent router for a job acquisition system.
Given the user's message, identify which agents should be activated.

Available agents:
- job_search: When user wants to find/search for jobs
- cv_build: When user uploads a CV or wants to update their profile  
- apply: When user wants to apply to a specific job
- job_prep: When user wants interview preparation or skill analysis
- general: Casual questions, greetings, status checks

Return a JSON object:
{
  "primary_intent": "job_search",
  "agents_to_activate": ["job_search"],        // ordered list
  "job_search_query": "data science Karachi",  // extracted query, or null
  "reasoning": "User wants to find jobs"       // for Langfuse logging
}

User message: "{user_message}"
"""
```

The `route_by_intent` function then reads `state["agents_to_activate"][0]` to determine which node to jump to first. For complex requests like "find jobs and apply," the graph will route to `job_search`, which edges to `cv_tailor`, which edges to `hitl_gate`, creating a chained pipeline automatically.

**Langfuse Tracing:** The Orchestrator creates the root Langfuse trace for every user interaction. All child agent spans attach to this root trace, making the entire interaction visible as a single timeline in Langfuse's UI.

---

## 3. Agent 1: Job Search Agent

**File:** `backend/agents/job_search_agent.py`
**Tool Used:** `backend/tools/apify_tool.py`

### What It Does

The Job Search Agent accepts a search query from the state (e.g., "Python developer Lahore remote") and uses the Apify Python client to run LinkedIn and Indeed job scraper actors in parallel. It then deduplicates results, calculates a match score for each job against the user's parsed CV, and writes results to the `jobs` SQLite table.

### Apify Integration

Apify provides pre-built "actors" (scraper bots) for job boards. You run them via the Apify API by specifying the actor ID and input parameters. The free tier allows a limited number of actor runs per month, so results must be cached in SQLite to avoid re-running scrapers for identical queries.

```python
# backend/tools/apify_tool.py

from apify_client import ApifyClient
from backend.config import settings

# LinkedIn Jobs Scraper actor ID (verified on Apify marketplace)
LINKEDIN_ACTOR_ID = "curious_coder/linkedin-jobs-scraper"

# Indeed Jobs Scraper actor ID
INDEED_ACTOR_ID = "misceres/indeed-scraper"

def scrape_linkedin_jobs(query: str, location: str, max_results: int = 10) -> list:
    """
    Run the LinkedIn jobs scraper actor on Apify.
    Returns a list of raw job dicts from Apify's dataset.
    
    IMPORTANT: Check https://apify.com/curious_coder/linkedin-jobs-scraper
    for the exact 'run_input' schema — it changes. As of early 2026:
    - 'keywords': search query string
    - 'location': location string  
    - 'maxResults': integer
    """
    client = ApifyClient(settings.APIFY_API_TOKEN)
    run_input = {
        "keywords": query,
        "location": location,
        "maxResults": max_results
    }
    run = client.actor(LINKEDIN_ACTOR_ID).call(run_input=run_input)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    return items

def scrape_indeed_jobs(query: str, location: str, max_results: int = 10) -> list:
    """
    Run the Indeed jobs scraper actor on Apify.
    Returns a list of raw job dicts.
    
    IMPORTANT: Check https://apify.com/misceres/indeed-scraper
    for the exact 'run_input' schema. As of early 2026:
    - 'position': job title/keyword
    - 'country': country code (e.g., 'PK' for Pakistan, 'US', 'GB')
    - 'maxItems': integer
    """
    client = ApifyClient(settings.APIFY_API_TOKEN)
    run_input = {
        "position": query,
        "country": "PK",
        "maxItems": max_results
    }
    run = client.actor(INDEED_ACTOR_ID).call(run_input=run_input)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    return items
```

### Deduplication Logic

The same job posting appears on LinkedIn, Indeed, and the company's own career page. The deduplication key is the combination of: normalized company name (lowercase, stripped of "Inc.", "Ltd.", "Pvt." etc.), normalized job title (lowercase), and city. If two results match on all three keys, keep the LinkedIn result and discard the Indeed result, since LinkedIn typically has more contact information.

```python
def deduplicate_jobs(linkedin_jobs: list, indeed_jobs: list) -> list:
    """
    Remove duplicate job postings across platforms.
    Prefers LinkedIn results over Indeed when duplicates are found.
    """
    seen = set()
    unique_jobs = []
    
    # Process LinkedIn first (preferred source)
    for job in linkedin_jobs + indeed_jobs:
        # Normalize the dedup key
        company = normalize_company_name(job.get("company", ""))
        title = normalize_job_title(job.get("title", ""))
        location = job.get("location", "").lower().split(",")[0].strip()
        
        key = f"{company}|{title}|{location}"
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)
    
    return unique_jobs

def normalize_company_name(name: str) -> str:
    """Remove legal suffixes and normalize whitespace."""
    import re
    # Remove common company suffixes
    suffixes = r'\b(inc|ltd|pvt|llc|corp|co|company|limited|private)\b\.?'
    name = re.sub(suffixes, '', name.lower(), flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', name).strip()
```

### Match Score Calculation

After deduplication, the agent calls `CVImprovementEngine.calculate_match_score(parsed_cv, job_description)` for each job. This is the deterministic scoring method from the BowJob reference — no LLM call needed, just keyword matching and structured analysis. Results are sorted descending by match score. The top 3 receive a `is_best_match: True` flag for the frontend to display the glowing border.

---

## 4. Agent 2: CV Parser Agent

**File:** `backend/agents/cv_parser_agent.py`

### What It Does

This agent is triggered when the user uploads a CV file. It extracts raw text from the file and then uses Gemini 1.5 Flash with structured output to extract all CV fields into the BowJob schema.

### PDF/DOCX Text Extraction

```python
import fitz  # PyMuPDF — best PDF text extractor available in Python

def extract_text_from_pdf(filepath: str) -> str:
    """
    Extract all text from a PDF using PyMuPDF.
    Superior to PyPDF2 for complex layouts and multi-column CVs.
    """
    doc = fitz.open(filepath)
    full_text = ""
    for page in doc:
        full_text += page.get_text("text")
    return full_text

def extract_text_from_docx(filepath: str) -> str:
    """Extract text from a Word document using python-docx."""
    from docx import Document
    doc = Document(filepath)
    return "\n".join([para.text for para in doc.paragraphs])
```

### Gemini Structured Output Approach

The BowJob reference uses OpenAI function calling. For Gemini via LangChain, the equivalent approach is `with_structured_output()` using a Pydantic model, or passing the schema directly. Since the BowJob CV schema is large and complex, the recommended approach is to pass the JSON schema directly to Gemini as a system instruction and parse the JSON response.

```python
# backend/agents/cv_parser_agent.py

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from backend.tools.gemini_llm import get_llm
import json

# Use the EXACT same SYSTEM_PROMPT from BowJob CVParserV3
# Use the EXACT same CV_FUNCTION schema from BowJob CVParserV3
# The schema is production-tested and must not be modified
from backend.agents._cv_schema import CV_SYSTEM_PROMPT, CV_EXTRACTION_SCHEMA

def cv_parser_node(state: HirePilotState) -> HirePilotState:
    """
    LangGraph node: Parse raw CV text into structured BowJob schema.
    
    Reads: state["cv_raw_text"]
    Writes: state["cv_parsed"]
    """
    llm, langfuse_handler = get_llm(state["session_id"], "CVParserAgent")
    
    prompt = f"""
    {CV_SYSTEM_PROMPT}
    
    Extract information from this CV. Return ONLY valid JSON matching the schema.
    Do not include markdown code blocks or any text outside the JSON.
    
    CV TEXT:
    {state["cv_raw_text"]}
    
    SCHEMA TO FOLLOW:
    {json.dumps(CV_EXTRACTION_SCHEMA, indent=2)}
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    
    # Parse the JSON response
    raw_json = response.content.strip()
    # Remove markdown code blocks if Gemini adds them
    if raw_json.startswith("```"):
        raw_json = raw_json.split("```")[1]
        if raw_json.startswith("json"):
            raw_json = raw_json[4:]
    
    parsed_cv = json.loads(raw_json.strip())
    
    return {
        **state,
        "cv_parsed": parsed_cv,
        "agent_logs": state["agent_logs"] + [{
            "agent": "CVParserAgent",
            "action": "CV parsed successfully",
            "skills_found": len(parsed_cv.get("skills", []) or []),
            "experience_years": parsed_cv.get("total_years_of_experience", 0)
        }]
    }
```

**IMPORTANT NOTE FOR COPILOT:** Create `backend/agents/_cv_schema.py` and copy the `SYSTEM_PROMPT` string and `CV_FUNCTION[0]["function"]["parameters"]` object verbatim from the BowJob `cv_parser.py` file. Do not rewrite or simplify these — they represent hours of prompt engineering work.

---

## 5. Agent 3: CV Tailoring Agent

**File:** `backend/agents/cv_tailoring_agent.py`

### What It Does

For a selected job, this agent generates a tailored CV by analyzing the gap between the user's current CV and the job description. It uses the BowJob `CVImprovementEngine` logic adapted for Gemini.

### Key Design Decision: Two-Step Approach

The BowJob `analyze()` method is one large function call. For Gemini free tier (which has rate limits and context limits), split this into two steps to avoid timeouts:

**Step 1 — Deterministic Scoring (no LLM):** Call `calculate_match_score(cv_parsed, job_description)` immediately. This returns the current match score without any API call. Store this in state and show it to the user instantly.

**Step 2 — AI Tailoring (Gemini call):** Run the full analysis prompt to get the `cv_sections` and `non_cv_sections` modifications. Use the BowJob `SYSTEM_PROMPT` and `ANALYSIS_FUNCTION` schema adapted for Gemini.

```python
# backend/agents/cv_tailoring_agent.py

from backend.agents._cv_improvement_schema import (
    CV_IMPROVEMENT_SYSTEM_PROMPT,
    CV_IMPROVEMENT_SCHEMA,
    calculate_match_score           # Pure Python, no LLM needed
)

@observe(name="CVTailoringAgent")
def cv_tailor_node(state: HirePilotState) -> HirePilotState:
    """
    LangGraph node: Tailor the CV to the selected job.
    
    Reads: state["cv_parsed"], state["selected_job"]
    Writes: state["cv_tailored"], state["email_draft"]
    """
    job = state["selected_job"]
    parsed_cv = state["cv_parsed"]
    
    # Step 1: Deterministic score (instant, no API call)
    score_result = calculate_match_score(parsed_cv, job["description"])
    
    # Step 2: AI tailoring via Gemini
    llm, _ = get_llm(state["session_id"], "CVTailoringAgent")
    
    tailor_prompt = f"""
    {CV_IMPROVEMENT_SYSTEM_PROMPT}
    
    JOB TITLE: {job["title"]}
    COMPANY: {job["company"]}
    
    JOB DESCRIPTION:
    {job["description"]}
    
    CURRENT PARSED CV:
    {json.dumps(parsed_cv, indent=2)}
    
    Return ONLY valid JSON. Follow the schema exactly.
    Ensure MINIMUM 3 projects in the output.
    """
    
    response = llm.invoke([HumanMessage(content=tailor_prompt)])
    tailored = json.loads(clean_json_response(response.content))
    
    # Apply project guardrail (from BowJob)
    tailored = apply_project_guardrail(tailored, parsed_cv, job["title"], job["description"], llm)
    
    # Add field paths for frontend to apply changes (from BowJob)
    tailored = add_field_paths(tailored, parsed_cv)
    
    # Override scores with deterministic calculation (from BowJob)
    tailored["scores"] = {
        "current_match_score": score_result["current_match_score"],
        "potential_score_after_changes": min(95, score_result["current_match_score"] + 20),
        "rating": score_result["rating"],
        "breakdown": score_result["breakdown"]
    }
    
    # Also generate email draft
    email_draft = generate_email_draft(llm, parsed_cv, job, tailored)
    
    return {
        **state,
        "cv_tailored": tailored,
        "email_draft": email_draft
    }
```

**IMPORTANT NOTE FOR COPILOT:** Create `backend/agents/_cv_improvement_schema.py`. Copy the following verbatim from BowJob `cv_improvement.py`: the `SYSTEM_PROMPT` string (rename to `CV_IMPROVEMENT_SYSTEM_PROMPT`), the `ANALYSIS_FUNCTION[0]["function"]["parameters"]` object (as `CV_IMPROVEMENT_SCHEMA`), the entire `calculate_match_score()` method, the `_apply_project_guardrail()` method, the `_generate_missing_projects()` method, the `_inject_projects_to_work_exp()` method, and the `_add_field_paths()` method. Replace all `self.client.chat.completions.create(...)` calls in `_generate_missing_projects()` with equivalent Gemini LangChain calls.

---

## 6. Agent 4: HITL Gate (Human-in-the-Loop)

**File:** `backend/agents/apply_agent.py` (the gate function lives here)

The HITL Gate is the most important safety feature of the entire system. It is not really an agent — it is a **LangGraph interrupt point**. When the graph reaches this node, execution pauses completely. The state is serialized and saved. The FastAPI endpoint that called `graph.invoke()` returns immediately with the tailored CV and email draft, sending them to the frontend.

The frontend shows the HITL approval UI. The user reads the tailored CV, optionally edits the email, checks the approval checkbox, and clicks Send. React then sends `POST /apply/approve` to FastAPI. FastAPI calls `graph.invoke(saved_state, config)` again, which resumes from the checkpoint after the hitl_gate and continues to the `apply` node.

```python
def hitl_gate_node(state: HirePilotState) -> HirePilotState:
    """
    This node runs AFTER LangGraph resumes from interrupt.
    By the time this runs, hitl_approved must be True.
    If it is False (which shouldn't happen normally), block the send.
    """
    if not state.get("hitl_approved", False):
        return {
            **state,
            "error": "Application not approved by user.",
            "final_response": "I haven't sent the email yet. Please approve the application first."
        }
    return state  # Proceed to apply node
```

The approval flow in FastAPI looks like this:

```python
# backend/routers/apply_router.py

# Store for paused graph states (in production, use Redis; for local use, in-memory dict)
PAUSED_STATES: dict = {}

@router.post("/approve")
async def approve_application(approval: HITLApproval, db: Session = Depends(get_db)):
    """
    Called when user clicks 'I approve' in the frontend.
    Resumes the paused LangGraph graph execution.
    """
    session_id = approval.session_id
    saved_state = PAUSED_STATES.get(session_id)
    
    if not saved_state:
        raise HTTPException(status_code=404, detail="No pending application found")
    
    # Update state with user's approval and any edits they made
    saved_state["hitl_approved"] = True
    saved_state["email_draft"] = approval.edited_email_draft  # User may have edited it
    
    # Log HITL approval to Langfuse
    log_hitl_decision(saved_state.get("langfuse_trace_id"), approved=True)
    
    # Resume the LangGraph graph from where it paused
    compiled_graph = build_graph()
    result = compiled_graph.invoke(saved_state)
    
    # Clean up saved state
    del PAUSED_STATES[session_id]
    
    return {"status": "sent", "application_id": result.get("application_id")}
```

---

## 7. Agent 5: Apply Agent

**File:** `backend/agents/apply_agent.py`
**Tool Used:** `backend/tools/gmail_tool.py`, `backend/tools/hr_email_finder.py`

### Gmail API Integration

Gmail API requires OAuth2. On first run, the user must complete a browser-based consent flow. After that, tokens are cached in `credentials/token.json` and reused automatically.

```python
# backend/tools/gmail_tool.py

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import base64, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SCOPES = ['https://www.googleapis.com/auth/gmail.send',
          'https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """
    Returns an authenticated Gmail API service object.
    On first run, opens browser for OAuth2 consent.
    Subsequent runs use cached credentials/token.json.
    
    SETUP REQUIRED:
    1. Go to console.cloud.google.com
    2. Create a new project → Enable Gmail API
    3. OAuth consent screen → External → Add your Gmail as test user
    4. Create credentials → OAuth 2.0 Client ID → Desktop app
    5. Download JSON → Save as credentials/gmail_credentials.json
    """
    creds = None
    token_path = "credentials/token.json"
    creds_path = "credentials/gmail_credentials.json"
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)  # Opens browser
        
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)

def send_email(to: str, subject: str, body: str, sender_name: str = "Job Applicant") -> dict:
    """
    Send an email via Gmail API.
    Returns the sent message object with its ID.
    """
    service = get_gmail_service()
    
    message = MIMEMultipart('alternative')
    message['to'] = to
    message['subject'] = subject
    message.attach(MIMEText(body, 'plain'))
    
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = service.users().messages().send(
        userId='me',
        body={'raw': raw}
    ).execute()
    
    return sent
```

### HR Email Finder

Finding the HR contact email is a best-effort operation. The strategy is: first check if Apify's LinkedIn scraper returned a company contact email in the job posting data. If not, use a secondary Apify actor (`apify/web-scraper`) to search for the HR email on the company's careers page. If still not found, use a search query fallback: `"{company_name}" HR email site:linkedin.com`.

```python
# backend/tools/hr_email_finder.py

def find_hr_email(company: str, job_url: str = None) -> str | None:
    """
    Attempt to find an HR contact email for a company.
    Returns email string if found, None otherwise.
    Strategy: job_posting_data → apify_web_scraper → search_fallback
    """
    # Strategy 1: Check if the job URL returns contact info directly
    # (implemented via Apify website content actor)
    
    # Strategy 2: Search fallback using Gemini to parse search results
    # Use query: f'site:linkedin.com "{company}" recruiter email'
    
    # Return None if not found — Apply Agent will ask user to provide email manually
    pass
```

---

## 8. Agent 6: Job Preparation Agent

**File:** `backend/agents/job_prep_agent.py`

This agent takes a selected job and the user's parsed CV and generates comprehensive interview preparation material. It runs entirely through Gemini with a structured prompt.

```python
JOB_PREP_PROMPT = """
You are an expert interview coach and career advisor.

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
    "company_research": {{"what_to_know": [...], "questions_to_ask": [...]}},
    "salary_guidance": {{"range": "...", "negotiation_tips": [...]}},
    "day_one_tips": [...]
}}

JOB TITLE: {job_title}
COMPANY: {company}
JOB DESCRIPTION: {job_description}
CANDIDATE CV: {cv_summary}
"""
```

---

## 9. Memory Agent

**File:** `backend/agents/memory_agent.py`

The Memory Agent maintains two types of memory for the system to learn from past interactions.

**Short-term memory** is the current conversation's chat history, stored in the LangGraph state as a list of `(role, content)` pairs. This is included in every Orchestrator call so the system understands context like "apply to that last job we discussed."

**Long-term memory** is stored in SQLite. After each session, key facts are persisted — which jobs the user liked (high match scores + selected), which applications were approved vs rejected by the user in HITL, and which interview questions the user found useful. The Orchestrator reads this on startup to personalize future job searches automatically.
