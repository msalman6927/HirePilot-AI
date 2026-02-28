# TASK_BREAKDOWN.md
# HirePilot-AI — Granular Task Breakdown
**Version:** 1.0.0 | **Last Updated:** 2026-02-28
**Purpose:** Exact, copy-pasteable task instructions for GitHub Copilot

---

## How to Use This File

Every task below is written so you can describe it to GitHub Copilot Chat (CMD+I or CTRL+I in VS Code) and Copilot will understand exactly what to generate. Each task includes: the exact file to create or edit, the Copilot prompt to use, the acceptance test to verify it works, and the expected output. Work through these in order — each task depends on the ones before it.

---

## TASK GROUP 0: Project Setup

### TASK-001: Create Project Structure

Open a terminal in the folder where you want to create the project and run these commands exactly.

```bash
mkdir hirepilot-ai
cd hirepilot-ai
mkdir -p backend/models backend/agents backend/tools backend/schemas backend/routers
mkdir -p frontend/src/pages frontend/src/components frontend/src/hooks frontend/src/services frontend/src/store
mkdir -p data credentials
touch backend/__init__.py backend/models/__init__.py backend/agents/__init__.py
touch backend/tools/__init__.py backend/schemas/__init__.py backend/routers/__init__.py
touch .env .gitignore requirements.txt
```

**Acceptance test:** Running `ls backend/` shows: `__init__.py agents models routers schemas tools main.py` (main.py will be created in TASK-003).

### TASK-002: Create .env and .gitignore

Create `.env` with this exact content (fill in your real keys):

```
GEMINI_API_KEY=your_gemini_api_key_here
LANGFUSE_PUBLIC_KEY=pk-lf-your-key-here
LANGFUSE_SECRET_KEY=sk-lf-your-key-here
LANGFUSE_HOST=https://cloud.langfuse.com
APIFY_API_TOKEN=apify_api_your_token_here
GMAIL_CLIENT_ID=your_client_id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=GOCSPX-your_secret_here
GMAIL_REDIRECT_URI=http://localhost:8000/auth/gmail/callback
DATABASE_URL=sqlite:///./data/hirepilot_ai.db
FRONTEND_URL=http://localhost:5173
```

Create `.gitignore` with this content:

```
.env
credentials/token.json
credentials/gmail_credentials.json
data/
__pycache__/
*.pyc
.venv/
node_modules/
```

**Where to get each API key:**
- `GEMINI_API_KEY` → Go to `aistudio.google.com` → Click "Get API Key" → Create key in new project.
- `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` → Go to `cloud.langfuse.com` → Sign up free → Create new project → Settings → Copy both keys.
- `APIFY_API_TOKEN` → Go to `apify.com` → Sign up free → Settings → Integrations → API tokens → Copy token.
- `GMAIL_CLIENT_ID` and `GMAIL_CLIENT_SECRET` → See TASK-015 for the full Gmail setup walkthrough.

### TASK-003: Verify API Keys Work

Create a file called `test_keys.py` in the project root and run it to confirm every key is valid before building anything.

```python
# test_keys.py — Run with: python test_keys.py
# Delete this file after keys are verified

import os
from dotenv import load_dotenv
load_dotenv()

print("=== Testing API Keys ===\n")

# Test 1: Gemini
print("1. Testing Gemini API...")
try:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content("Say 'Gemini connected!' in exactly those words.")
    print(f"   ✓ Gemini OK: {response.text.strip()}")
except Exception as e:
    print(f"   ✗ Gemini FAILED: {e}")

# Test 2: Langfuse
print("\n2. Testing Langfuse connection...")
try:
    from langfuse import Langfuse
    lf = Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_HOST")
    )
    lf.auth_check()
    print("   ✓ Langfuse OK: Connected to cloud.langfuse.com")
except Exception as e:
    print(f"   ✗ Langfuse FAILED: {e}")

# Test 3: Apify
print("\n3. Testing Apify connection...")
try:
    from apify_client import ApifyClient
    client = ApifyClient(os.getenv("APIFY_API_TOKEN"))
    me = client.user("me").get()
    print(f"   ✓ Apify OK: Logged in as {me.get('username', 'unknown')}")
except Exception as e:
    print(f"   ✗ Apify FAILED: {e}")

print("\n=== Done ===")
```

**Acceptance test:** All three print `✓ OK`. Fix any failures before continuing.

---

## TASK GROUP 1: Backend Foundation

### TASK-004: Create config.py

**Copilot prompt:** "Create a file `backend/config.py` using pydantic-settings. Define a `Settings` class that reads all environment variables from the `.env` file: `GEMINI_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, `APIFY_API_TOKEN`, `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REDIRECT_URI`, `DATABASE_URL`, `FRONTEND_URL`. Create a module-level `settings` instance. Use `model_config = SettingsConfigDict(env_file='.env')`."

**Acceptance test:** `python -c "from backend.config import settings; print(settings.GEMINI_API_KEY[:5])"` prints first 5 characters of your key.

### TASK-005: Create database.py and all five SQLAlchemy models

**Copilot prompt:** "Create `backend/database.py` with a SQLite engine using `DATABASE_URL` from settings, a `SessionLocal` factory using `sessionmaker`, a `Base` declarative base, and a `create_tables()` function that calls `Base.metadata.create_all(engine)`. Also create a `get_db()` FastAPI dependency that yields a session and closes it after the request.

Then create five model files exactly as follows:

`backend/models/job.py` — Table `jobs` with columns: id (Integer PK autoincrement), session_id (String), title (String not null), company (String not null), location (String), platform (String), job_url (String), description (Text), match_score (Float), hr_email (String), fetched_at (DateTime default now). Add a UniqueConstraint on (company, title, location).

`backend/models/application.py` — Table `applications` with: id, job_id (FK jobs.id), cv_version_id (FK cv_versions.id), tailored_cv (JSON), email_draft (Text), hr_email (String), sent_at (DateTime), status (String default 'Sent').

`backend/models/cv_version.py` — Table `cv_versions` with: id, filename (String), raw_text (Text), parsed_data (JSON), created_at (DateTime default now).

`backend/models/agent_log.py` — Table `agent_logs` with: id, session_id (String), agent_name (String), action (Text), status (String), metadata (JSON), langfuse_trace_id (String), created_at (DateTime default now).

`backend/models/chat_message.py` — Table `chat_messages` with: id, session_id (String), role (String), content (Text), created_at (DateTime default now).

Import all models in `backend/models/__init__.py` so `create_tables()` can find them."

**Acceptance test:** `python -c "from backend.database import create_tables; create_tables(); print('Tables created')"` creates `data/hirepilot_ai.db` and prints "Tables created".

### TASK-006: Create Gemini LLM Factory with Langfuse

**Copilot prompt:** "Create `backend/tools/gemini_llm.py`. Import `ChatGoogleGenerativeAI` from `langchain_google_genai`, `CallbackHandler` from `langfuse.callback`, and `settings` from `backend.config`. Write a function `get_llm(session_id: str, agent_name: str)` that creates a `CallbackHandler` with the Langfuse keys from settings, the session_id, and metadata `{'agent': agent_name}`. Create and return a tuple of `(llm, langfuse_handler)` where the llm is `ChatGoogleGenerativeAI(model='gemini-1.5-flash', google_api_key=settings.GEMINI_API_KEY, callbacks=[langfuse_handler], temperature=0.3)`. Also write a utility function `clean_json_response(text: str) -> str` that removes markdown code fences (```json ... ```) from a string and returns clean JSON text."

**Acceptance test:** `python -c "from backend.tools.gemini_llm import get_llm; llm, _ = get_llm('test', 'test'); r = llm.invoke('Say hello'); print(r.content)"` — prints a greeting and a trace appears in Langfuse.

### TASK-007: Create FastAPI main.py

**Copilot prompt:** "Create `backend/main.py`. Create a FastAPI app with title 'HirePilot-AI API'. Add CORSMiddleware allowing origin `http://localhost:5173`, all methods, all headers, credentials=True. On startup event, call `create_tables()` from `backend.database`. Add a health check `GET /health` route returning `{'status': 'ok', 'service': 'HirePilot-AI API'}`. Include routers for chat, cv, jobs, apply, dashboard, prep — use prefix `/chat`, `/cv`, `/jobs`, `/apply`, `/dashboard`, `/prep`. For now, create empty router files for each in `backend/routers/` that just define an `APIRouter` and have one placeholder GET route returning `{'status': 'placeholder'}`."

**How to start the server:** `uvicorn backend.main:app --reload --port 8000`

**Acceptance test:** Open `http://localhost:8000/health` in browser — see `{"status":"ok","service":"HirePilot-AI API"}`. Open `http://localhost:8000/docs` — see the interactive FastAPI docs page.

---

## TASK GROUP 2: CV Parsing Pipeline

### TASK-008: Port BowJob CV Schema

**Copilot prompt:** "Create `backend/agents/_cv_schema.py`. This file stores the CV extraction schema ported from the BowJob project. Define a string constant `CV_SYSTEM_PROMPT` with this exact text: [paste the SYSTEM_PROMPT string from BowJob cv_parser.py here]. Define a dict constant `CV_EXTRACTION_SCHEMA` with the JSON schema from the `parameters` field of `CV_FUNCTION[0]['function']` in BowJob cv_parser.py [paste it here]. Do not modify either of these — they are production-tested prompts."

**IMPORTANT:** Open the BowJob `cv_parser.py` file. Copy the `SYSTEM_PROMPT` string (lines starting with `"""You are an expert CV/Resume parser...`). Copy the `"parameters"` dict from `CV_FUNCTION`. Paste them into this file. Do not rewrite them.

**Acceptance test:** `python -c "from backend.agents._cv_schema import CV_SYSTEM_PROMPT; print(CV_SYSTEM_PROMPT[:50])"` prints the first 50 characters of the prompt.

### TASK-009: Create CV Parser Agent

**Copilot prompt:** "Create `backend/agents/cv_parser_agent.py`. Import `HirePilotState` from `backend.agents.orchestrator` (we will create this next), `get_llm` from `backend.tools.gemini_llm`, `CV_SYSTEM_PROMPT` and `CV_EXTRACTION_SCHEMA` from `backend.agents._cv_schema`, and the Langfuse `observe` decorator.

Write `extract_text_from_pdf(filepath: str) -> str` using `fitz.open()` (PyMuPDF) — iterate pages, call `page.get_text('text')`, concatenate all text.

Write `extract_text_from_docx(filepath: str) -> str` using `python-docx` — open document, join all paragraph texts.

Write the LangGraph node function `cv_parser_node(state: HirePilotState) -> HirePilotState` decorated with `@observe(name='CVParserAgent')`. Inside: call `get_llm(state['session_id'], 'CVParserAgent')`, build a prompt string that includes CV_SYSTEM_PROMPT, tells Gemini to return ONLY valid JSON matching CV_EXTRACTION_SCHEMA, and appends `state['cv_raw_text']`. Call `llm.invoke([HumanMessage(content=prompt)])`. Clean the response with `clean_json_response()`. Parse JSON. Return updated state with `cv_parsed` set to the parsed dict and an agent_log entry added."

**Acceptance test:** Pass a simple CV text through the node and confirm the output is a dict with keys like `contact_info`, `skills`, `work_experience`.

### TASK-010: Create CV Upload Endpoint

**Copilot prompt:** "Fill in `backend/routers/cv_router.py`. Create `POST /cv/upload` that accepts a file upload (use `UploadFile` from FastAPI). Save the file to `./data/uploads/{filename}`. Detect if it's PDF or DOCX by file extension. Call the appropriate extraction function from `cv_parser_agent.py`. Call `cv_parser_node` with the extracted text in a minimal state dict. Save the result to the SQLite `cv_versions` table. Return a JSON response with: `cv_id` (the new SQLite row ID), `filename`, `parsed_cv` (the full parsed dict), and `skills_count`. Also create `GET /cv/versions` that returns all rows from `cv_versions` table ordered by created_at descending."

**Acceptance test:** Use the FastAPI `/docs` page to upload a real CV PDF. The response should contain the parsed CV dict with real skills and experience extracted.

---

## TASK GROUP 3: Orchestrator + Intent Routing

### TASK-011: Create HirePilotState and Orchestrator Graph

**Copilot prompt:** "Create `backend/agents/orchestrator.py`. Define the `HirePilotState` TypedDict with all fields from `SYSTEM_ARCHITECTURE.md` Section 4.1. Import `StateGraph` and `END` from `langgraph.graph`. 

Write the `intent_router_node(state: HirePilotState) -> HirePilotState` function. Inside, use `get_llm()` to get a Gemini instance. Build a prompt that describes the 5 available intents (job_search, cv_build, apply, job_prep, general) and asks Gemini to classify `state['user_message']` and return a JSON object with `primary_intent`, `agents_to_activate`, `job_search_query`, and `reasoning`. Parse the JSON. Update `state['detected_intent']`, `state['agents_to_activate']`, and `state['job_search_query']`.

Write `route_by_intent(state: HirePilotState) -> str` that reads `state['agents_to_activate'][0]` and returns it. If the list is empty, return `'general'`.

Write `responder_node(state: HirePilotState) -> HirePilotState` that builds a final human-readable message based on what agents ran.

Write `build_graph()` that creates a StateGraph, adds all agent nodes (use placeholder lambda functions for agents not yet built), sets the entry point to `intent_router`, adds conditional edges from intent_router using `route_by_intent`, adds regular edges from each agent to `responder`, adds edge from `responder` to END, and compiles with `interrupt_before=['hitl_gate']`. Return the compiled graph."

**Acceptance test:** `python -c "from backend.agents.orchestrator import build_graph; g = build_graph(); print('Graph built successfully')"` — no errors.

### TASK-012: Wire Chat Endpoint to Orchestrator

**Copilot prompt:** "Fill in `backend/routers/chat_router.py`. Create a Pydantic model `ChatRequest` with fields: `message: str`, `session_id: str`. Create `POST /chat` that accepts `ChatRequest`. Initialize a `HirePilotState` dict with default empty values, set `user_message` and `session_id` from the request, and set `agent_logs` to an empty list, `hitl_approved` to False. Call `build_graph().invoke(initial_state)`. Save the user message and assistant response to `chat_messages` table in SQLite. Return a `ChatResponse` with: `response` (the final_response from state), `session_id`, `agents_activated` (list of agent names), `langfuse_trace_id`, and any `jobs` or `cv` data in the state."

**Acceptance test:** `curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message":"hello","session_id":"test1"}'` returns a JSON response and Langfuse shows a trace.

---

## TASK GROUP 4: Job Search

### TASK-013: Create Apify Tool

**Copilot prompt:** "Create `backend/tools/apify_tool.py`. Import `ApifyClient` from `apify_client` and `settings` from `backend.config`.

Write `scrape_linkedin_jobs(query: str, location: str, max_results: int = 10) -> list`. Use `ApifyClient(settings.APIFY_API_TOKEN)`. Run actor `'curious_coder/linkedin-jobs-scraper'` with run_input `{'keywords': query, 'location': location, 'maxResults': max_results}`. Use `client.actor(ACTOR_ID).call(run_input=run_input)`. Get results with `client.dataset(run['defaultDatasetId']).iterate_items()`. Each item should have keys: title, company, location, url, description. Normalize these into a consistent dict format with those exact keys.

Write `scrape_indeed_jobs(query: str, location: str, max_results: int = 10) -> list` similarly using actor `'misceres/indeed-scraper'` with run_input `{'position': query, 'country': 'PK', 'maxItems': max_results}`.

Write `normalize_company_name(name: str) -> str` using regex to remove legal suffixes (Inc, Ltd, Pvt, LLC, Corp, Co) and strip whitespace.

Write `deduplicate_jobs(linkedin_jobs: list, indeed_jobs: list) -> list` using a set of `f'{company}|{title}|{city}'` keys where each part is normalized and lowercased.

IMPORTANT NOTE FOR COPILOT: Before using these actor IDs, go to `https://apify.com/store` and search for 'LinkedIn jobs' and 'Indeed jobs' to confirm the current actor IDs. The actor IDs used here are best-known values but may have changed. Use the actor with the most reviews."

**Acceptance test:** `python -c "from backend.tools.apify_tool import scrape_linkedin_jobs; jobs = scrape_linkedin_jobs('Python developer', 'Lahore', 3); print(len(jobs), 'jobs found')"` — prints a number greater than 0.

### TASK-014: Create Job Search Agent Node

**Copilot prompt:** "Create `backend/agents/job_search_agent.py`. Import the Apify tools, `calculate_match_score` from `backend.agents._cv_improvement_schema`, the `observe` decorator, and SQLAlchemy session utilities.

Write `job_search_node(state: HirePilotState) -> HirePilotState` decorated with `@observe(name='JobSearchAgent')`. Inside: log to `agent_logs` that search is starting. Extract the query from `state['job_search_query']`. Parse the query to extract job title and location (use a simple split or a quick Gemini call). Run `scrape_linkedin_jobs()` and `scrape_indeed_jobs()` in sequence (sequential is fine for demo). Call `deduplicate_jobs()`. For each unique job, if `state['cv_parsed']` exists, call `calculate_match_score(state['cv_parsed'], job['description'])` and add the result to the job dict as `match_score`. Sort jobs by match_score descending. Mark jobs at index 0, 1, 2 with `is_best_match: True`. Save all jobs to SQLite `jobs` table (use INSERT OR IGNORE to avoid duplicate constraint errors). Update `state['jobs_matched']`. Add log entry. Update `state['final_response']` with a human-readable summary."

**Acceptance test:** Send `POST /chat` with `{"message": "Find Python developer jobs in Lahore", "session_id": "test2"}`. The response should contain a list of real job results. SQLite `jobs` table should have rows.

---

## TASK GROUP 5: Gmail Setup

### TASK-015: Gmail API Setup (Manual Steps)

This task cannot be done by Copilot — you must do it manually. Follow these steps precisely.

Step 1: Go to `console.cloud.google.com`. If you don't have a Google account, create one. If you do, sign in.

Step 2: Click "Select a project" at the top → "New Project" → Name it "hirepilot-ai" → Create.

Step 3: In the search bar at the top, search "Gmail API" → Click it → Click "Enable".

Step 4: In the left menu, click "APIs & Services" → "OAuth consent screen". Choose "External". Fill in App name "HirePilot-AI", your email for support and developer contact. Click Save and Continue through all steps without adding scopes or test users yet. At the end, click "Back to Dashboard".

Step 5: Click "Credentials" in the left menu → "+ Create Credentials" → "OAuth 2.0 Client ID". Choose Application type "Desktop app". Name it "HirePilot-AI Desktop". Click Create. Click "Download JSON". Save the downloaded file as `credentials/gmail_credentials.json` in your project.

Step 6: Go back to "OAuth consent screen" → "Test users" → Add your Gmail address as a test user.

Step 7: Run the Gmail auth script to get the initial token:

```python
# Run once: python setup_gmail.py
from google_auth_oauthlib.flow import InstalledAppFlow
import os

SCOPES = ['https://www.googleapis.com/auth/gmail.send',
          'https://www.googleapis.com/auth/gmail.readonly']

flow = InstalledAppFlow.from_client_secrets_file('credentials/gmail_credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

os.makedirs('credentials', exist_ok=True)
with open('credentials/token.json', 'w') as f:
    f.write(creds.to_json())

print("Gmail authenticated! token.json saved.")
```

A browser will open. Log in with your Gmail. Allow access. The token is saved. You won't need to do this again.

**Acceptance test:** `python -c "from backend.tools.gmail_tool import get_gmail_service; svc = get_gmail_service(); print('Gmail connected')"` prints "Gmail connected".

### TASK-016: Create Gmail Tool

**Copilot prompt:** "Create `backend/tools/gmail_tool.py`. Implement `get_gmail_service()` exactly as shown in `AGENT_DESIGN.md` Section 7 — use `Credentials.from_authorized_user_file('credentials/token.json', SCOPES)`, refresh if expired, return `build('gmail', 'v1', credentials=creds)`.

Implement `send_email(to: str, subject: str, body: str) -> dict` that creates a MIMEMultipart email, base64-encodes it, and calls `service.users().messages().send(userId='me', body={'raw': raw}).execute()`.

Implement `send_test_email(to: str) -> bool` that sends a test message and returns True on success, False on failure. This is used to verify Gmail works before the demo."

---

## TASK GROUP 6: CV Tailoring + HITL

### TASK-017: Port BowJob CV Improvement Schema

**Copilot prompt:** "Create `backend/agents/_cv_improvement_schema.py`. Copy these items verbatim from BowJob `cv_improvement.py` (the file content was provided in full):

1. The `SYSTEM_PROMPT` string — rename it to `CV_IMPROVEMENT_SYSTEM_PROMPT`.
2. The `ANALYSIS_FUNCTION[0]['function']['parameters']` dict — rename to `CV_IMPROVEMENT_SCHEMA`.
3. The `calculate_match_score()` method — make it a standalone function `calculate_match_score(parsed_cv: dict, job_description: str) -> dict`. Remove `self.` references.
4. The `_apply_project_guardrail()` method — make it standalone `apply_project_guardrail(result, parsed_cv, job_title, job_description, llm) -> dict`. Replace the `self.client.chat.completions.create()` inside `_generate_missing_projects()` with a call to `llm.invoke()` using the same prompt content.
5. The `_count_projects()` method — standalone.
6. The `_generate_missing_projects()` method — standalone, adapted for Gemini LangChain.
7. The `_inject_projects_to_work_exp()` method — standalone.
8. The `_add_field_paths()` method — standalone.

DO NOT modify the logic — only remove `self.` and replace OpenAI client calls with LangChain Gemini calls."

### TASK-018: Create CV Tailoring Agent and HITL Gate

**Copilot prompt:** "Create `backend/agents/cv_tailoring_agent.py`. Implement `cv_tailor_node(state: HirePilotState) -> HirePilotState` with `@observe(name='CVTailoringAgent')`. Follow the pattern in `AGENT_DESIGN.md` Section 5: Step 1 calls `calculate_match_score()` with no LLM. Step 2 builds a Gemini prompt using `CV_IMPROVEMENT_SYSTEM_PROMPT`, the job title, job description, and JSON-serialized CV. Parse the Gemini response. Apply project guardrail. Add field paths. Override scores with deterministic calculation. Also call `generate_email_draft(llm, parsed_cv, job, tailored) -> str` which generates a professional application email using a simple Gemini prompt.

In `backend/agents/apply_agent.py`, implement:
1. `PAUSED_STATES: dict = {}` — module-level in-memory store for paused graph states.
2. `hitl_gate_node(state: HirePilotState) -> HirePilotState` — checks if `state['hitl_approved']` is True. If True, passes through. If False, sets error message.
3. `apply_node(state: HirePilotState) -> HirePilotState` — calls `send_email()` from gmail_tool, saves to SQLite applications table, updates state with application_id and final_response.
4. `log_hitl_decision(trace_id: str, approved: bool)` — creates a Langfuse score event."

### TASK-019: Create Apply Router with HITL Endpoints

**Copilot prompt:** "Fill in `backend/routers/apply_router.py`. Create Pydantic model `HITLApproval` with: `session_id: str`, `edited_email_draft: str`, `approved: bool`.

Create `GET /apply/preview/{job_id}` that looks up the job in SQLite, looks up the latest cv_version, runs `cv_tailor_node()` with a minimal state (or retrieves from session if already computed), saves the paused state to `PAUSED_STATES[session_id]`, and returns: `tailored_cv`, `email_draft`, `hr_email`, `job_title`, `company`, `match_score`.

Create `POST /apply/approve` that reads the saved state from `PAUSED_STATES[session_id]`, updates `hitl_approved=True` and `email_draft=approval.edited_email_draft`, calls `build_graph().invoke(saved_state)` to resume execution, logs the HITL decision to Langfuse, and returns the application record."

---

## TASK GROUP 7: Dashboard + Observability

### TASK-020: Create Dashboard Router

**Copilot prompt:** "Fill in `backend/routers/dashboard_router.py`. Create these endpoints, all reading from SQLite via SQLAlchemy:

`GET /dashboard/cv-versions` — all cv_versions ordered by created_at desc.
`GET /dashboard/job-history` — all unique session_id + job_search_query combinations with result counts.
`GET /dashboard/applications` — all applications joined with jobs table, returning: job_title, company, sent_at, status, hr_email. Color-code status as: Sent=blue, Opened=yellow, Interview=green, Rejected=red (add a `status_color` field to response).
`GET /dashboard/logs` — all agent_logs for a given `session_id` query param, ordered by created_at asc. This powers the real-time Agent Activity Feed.
`GET /dashboard/logs/stream` — WebSocket endpoint that sends new agent_log rows as they are inserted, using SQLite polling every 2 seconds."

### TASK-021: Add @observe to All Agent Nodes

**Copilot prompt:** "Add the Langfuse `@observe` decorator with a meaningful `name` parameter to all five agent node functions: `intent_router_node` → name='IntentRouter', `job_search_node` → name='JobSearchAgent', `cv_parser_node` → name='CVParserAgent', `cv_tailor_node` → name='CVTailoringAgent', `apply_node` → name='ApplyAgent'. Inside each, add `langfuse_context.update_current_observation(input={...}, output={...})` calls at the start and end with meaningful data. Also add an `agent_logs` entry to the SQLite table at the start and completion of each agent. This is what populates the real-time Activity Feed tab."

**Acceptance test:** Run the full chat pipeline. Open `cloud.langfuse.com` → Traces. See a trace with nested spans for each agent that ran, showing input/output data.

---

## TASK GROUP 8: Frontend Integration

### TASK-022: Create API Service Layer

**Copilot prompt:** "Create `frontend/src/services/api.js`. Import axios and set the baseURL to `http://localhost:8000`. Define and export async functions for every backend endpoint: `uploadCV(file)` using FormData, `sendMessage(message, sessionId)`, `getJobs(sessionId)`, `getApplicationPreview(jobId, sessionId)`, `approveApplication(sessionId, editedEmailDraft)`, `getApplications()`, `getAgentLogs(sessionId)`, `getInterviewPrep(jobId)`. Each function should handle errors and return the `response.data` from axios."

### TASK-023: Create Zustand Store

**Copilot prompt:** "Create `frontend/src/store/appStore.js` using Zustand. The store should hold: `parsedCV` (object, starts null), `cvId` (string), `sessionId` (auto-generated UUID on first load, persisted in localStorage), `jobs` (array), `selectedJob` (object), `applicationPreview` (object with tailored_cv and email_draft), `agentLogs` (array), `chatMessages` (array), `isAgentRunning` (boolean). Define setter actions for each. Export the store as `useAppStore`."

### TASK-024: Wire Pages to Backend

**Copilot prompt (repeat for each page):** "In `frontend/src/pages/CVUpload.jsx`, replace the mock upload handler with a real call to `api.uploadCV(file)`. On success, store the result in `useAppStore`'s `parsedCV` and `cvId`. Then navigate to the Chatbot page.

In `frontend/src/pages/Chatbot.jsx`, wire the chat input form to `api.sendMessage()`. Display the response in the chat window. Show the parsed CV profile in the right panel using `parsedCV` from the store.

In `frontend/src/pages/JobMatching.jsx`, on page load call `api.getJobs(sessionId)`. Render real job data in the job cards with actual match scores. Wire the 'Select' button to set `selectedJob` in the store and navigate to ApplicationPrep.

In `frontend/src/pages/ApplicationPrep.jsx`, on page load call `api.getApplicationPreview(selectedJob.id, sessionId)`. Render the tailored CV preview and the email editor with real data. Wire the approval checkbox and Send button to `api.approveApplication()`.

In `frontend/src/pages/Dashboard.jsx`, wire each of the 5 tabs to their respective API calls. Poll `api.getAgentLogs(sessionId)` every 3 seconds and update the Activity Feed tab in real time."

---

## TASK GROUP 9: Final Testing

### TASK-025: End-to-End Demo Test Script

Run this manual test sequence before the demo to confirm everything works.

1. Start backend: `uvicorn backend.main:app --reload --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Open `http://localhost:5173` in browser.
4. Upload your CV PDF. Confirm the profile summary appears on the right panel.
5. Type "Find Python developer jobs in Lahore" in the chat. Confirm real jobs appear in the Jobs tab.
6. Click "Select" on the top match. Confirm the tailored CV preview appears.
7. Read the tailored CV. Check the approval box. Click Send. Confirm an email arrives in the target inbox.
8. Open `cloud.langfuse.com`. Confirm a trace appears with all agent spans.
9. Open the Agent Activity Logs tab. Confirm a timeline of actions is visible.
10. Open the Applications Sent tab. Confirm the sent application appears with status "Sent".

If all 10 steps succeed, your demo is ready.
