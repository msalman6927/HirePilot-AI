# DEVELOPMENT_ROADMAP.md
# HirePilot-AI — Development Roadmap
**Version:** 1.0.0 | **Last Updated:** 2026-02-28 | **Deadline:** Sunday Demo

---

## 1. Roadmap Overview

Given that you have approximately 12 hours remaining and are using GitHub Copilot as your primary coding assistant, this roadmap is structured as a series of time-boxed phases. Each phase produces a **runnable, demonstrable checkpoint** — meaning if you run out of time, what you have built is still presentable rather than broken. Think of this as building a house: foundation first, then walls, then roof — each step is livable even if incomplete.

The guiding principle is **depth over breadth**. A working end-to-end pipeline for one use case (search → tailor → HITL → send) impresses more than five half-working features. Langfuse observability is woven into every phase because your instructor specifically mentioned it.

---

## 2. Phase 0: Project Scaffolding (45 minutes)

This phase creates the complete folder structure, installs all dependencies, and verifies that every API key is working before a single line of agent code is written. Skipping this phase causes debugging hell later.

**Tasks:** Create the project root folder `hirepilot-ai/`. Copy the exact directory structure from `SYSTEM_ARCHITECTURE.md` Section 3. Create `requirements.txt` with all dependencies listed in Section 4 of this roadmap. Create `.env` from `.env.example` and fill in your real API keys. Run `pip install -r requirements.txt`. Verify each API key with a one-line test script (detailed in `TASK_BREAKDOWN.md`). Initialize SQLite by running the database setup script.

**Completion Signal:** Running `python -c "from backend.config import settings; print(settings.GEMINI_API_KEY[:10])"` prints the first 10 characters of your Gemini key without error.

---

## 3. Phase 1: Backend Foundation (2 hours)

Build the FastAPI server, SQLAlchemy database models, and the shared LangGraph state without any agent logic yet. This gives Copilot a stable foundation to build on.

**Sub-phase 1A — Database (30 min):** Create all five SQLAlchemy models (Job, Application, CVVersion, AgentLog, ChatMessage) exactly matching the SQL schema in `SYSTEM_ARCHITECTURE.md` Section 7. Create `database.py` with the SQLite engine and session factory. Create `backend/main.py` with a basic FastAPI app that creates tables on startup.

**Sub-phase 1B — Gemini + Langfuse (30 min):** Create `backend/tools/gemini_llm.py` with the `get_llm()` factory function that returns a Gemini 1.5 Flash instance pre-wired to Langfuse. Test it by sending a simple "Hello" message and confirming the trace appears in the Langfuse cloud dashboard at `cloud.langfuse.com`.

**Sub-phase 1C — LangGraph State + Empty Graph (30 min):** Create `backend/agents/orchestrator.py` with the `HirePilotState` TypedDict and an empty `StateGraph` that just has a `responder` node returning "Hello from the orchestrator!" Wire this to `POST /chat` in FastAPI. Test with Postman or curl.

**Sub-phase 1D — CV Parser Port from BowJob (30 min):** Create `backend/agents/_cv_schema.py` by copying the `SYSTEM_PROMPT` and `CV_FUNCTION` schema from BowJob's `cv_parser.py` verbatim. Create `cv_parser_agent.py` with the `cv_parser_node` function. Test on a sample CV text.

**Completion Signal:** `POST /chat` with `{"message": "hello", "session_id": "test"}` returns a response and a trace appears in Langfuse.

---

## 4. Phase 2: CV Upload + Job Search (2.5 hours)

This phase delivers the first two visible features: uploading a CV and seeing real jobs. This is what makes your demo feel alive.

**Sub-phase 2A — CV Upload Endpoint (45 min):** Create `POST /cv/upload` that accepts a file upload (PDF or DOCX), saves it to `./data/uploads/`, extracts text using PyMuPDF, calls `cv_parser_node`, stores the parsed result in SQLite `cv_versions` table, and returns the parsed CV as JSON. Connect this to the `intent_router` in the LangGraph graph.

**Sub-phase 2B — Apify Job Scraper (1 hour):** Create `backend/tools/apify_tool.py` with `scrape_linkedin_jobs()` and `scrape_indeed_jobs()`. Add the deduplication logic. Important: on the Apify platform at `apify.com`, go to the Store tab, search for the LinkedIn and Indeed scrapers, and verify the exact actor IDs and run_input schemas — these may have changed since this documentation was written. Create `backend/agents/job_search_agent.py` with `job_search_node()` that calls both scrapers, deduplicates, and calculates match scores.

**Sub-phase 2C — Intent Router (45 min):** Implement the `intent_router_node` in `orchestrator.py` using a Gemini call with the `INTENT_PROMPT`. Add conditional edges to the LangGraph graph that route to `job_search` when intent is detected.

**Completion Signal:** User types "Find Python jobs in Lahore" in the chat. FastAPI triggers the Orchestrator. Apify runs. Real jobs appear in the SQLite `jobs` table. `GET /jobs` returns them as JSON.

---

## 5. Phase 3: CV Tailoring + HITL (2.5 hours)

This is the most impressive part of the demo. When a user selects a job and the system produces a tailored CV and then asks for approval before doing anything — that is the moment that separates this project from everyone else's.

**Sub-phase 3A — CV Improvement Schema Port (45 min):** Create `backend/agents/_cv_improvement_schema.py`. Copy verbatim from BowJob `cv_improvement.py`: `SYSTEM_PROMPT`, `ANALYSIS_FUNCTION` schema, `calculate_match_score()`, `_apply_project_guardrail()`, `_generate_missing_projects()`, `_inject_projects_to_work_exp()`, and `_add_field_paths()`. Adapt `_generate_missing_projects()` to use Gemini via LangChain.

**Sub-phase 3B — CV Tailoring Agent (45 min):** Implement `cv_tailor_node()` in `cv_tailoring_agent.py`. Add the email draft generator function that creates a professional job application email using the tailored CV highlights and job details.

**Sub-phase 3C — HITL Gate + Apply Agent (1 hour):** Implement the `PAUSED_STATES` in-memory store. Compile the LangGraph graph with `interrupt_before=["hitl_gate"]`. Create `GET /apply/preview/{job_id}` that returns tailored CV + email draft to frontend. Create `POST /apply/approve` that resumes the graph with `hitl_approved=True`. Implement `backend/tools/gmail_tool.py` with the full OAuth2 setup. Implement `apply_node()` that calls Gmail API.

**Completion Signal:** User selects a job. System shows tailored CV. User clicks approve. An email is actually sent to a test email address. SQLite `applications` table has a new row.

---

## 6. Phase 4: Frontend Integration (2 hours)

Connect the Lovable-designed React frontend to the real FastAPI backend. Since the frontend design is already built (approved by your instructor), this phase is primarily about replacing mock data with real API calls.

**Sub-phase 4A — API Service Layer (30 min):** Create `frontend/src/services/api.js` with Axios configured to point to `http://localhost:8000`. Define functions for every endpoint: `uploadCV()`, `sendMessage()`, `getJobs()`, `getApplicationPreview()`, `approveApplication()`, `getDashboard()`.

**Sub-phase 4B — State Management (30 min):** Set up Zustand store in `frontend/src/store/appStore.js` with global state for: current CV (parsed), current jobs list, current application (tailored CV + email), agent logs, and chat history.

**Sub-phase 4C — Wire Each Page (1 hour):** In each page component (CVUpload, Chatbot, JobMatching, ApplicationPrep, Dashboard), replace mock data with real `api.js` calls. The Chatbot page's WebSocket connection should update agent logs in real time. The ApplicationPrep page's Send button must be wired to `POST /apply/approve`.

**Completion Signal:** The entire flow works through the UI end-to-end without using Postman.

---

## 7. Phase 5: Observability + Polish (1 hour)

This phase makes your demo look professional and ensures Langfuse tracing is complete — the two things your instructor will specifically check.

**Sub-phase 5A — Langfuse Completeness (30 min):** Add `@observe` decorator to all five agent node functions. Verify in the Langfuse dashboard that each trace shows the correct hierarchy: root trace (user message) → intent router span → agent span → LLM call span → tool call span. Add `langfuse_context.update_current_observation(input=..., output=...)` to each `@observe` function so the Langfuse dashboard shows meaningful data, not just function names.

**Sub-phase 5B — Agent Activity Feed (30 min):** Create `GET /dashboard/logs` that returns all `AgentLog` rows for a session in chronological order. Wire the Dashboard's "Agent Activity Logs" tab to poll this endpoint every 3 seconds and display a real-time timeline of what agents are doing. This is the "mission control" visual that will impress the instructor.

**Completion Signal:** Opening Langfuse dashboard at `cloud.langfuse.com` shows a complete trace tree for each user interaction. The Agent Activity Logs tab in the UI shows a live timeline.

---

## 8. Phase 6 (If Time Permits): Interview Prep + Job Preparation Agent (30 min)

Implement `job_prep_agent.py` with the structured Gemini prompt from `AGENT_DESIGN.md` Section 8. Wire `GET /prep/{job_id}` to return the prep material. Wire the Dashboard's Interview Prep tab to display it as expandable accordion cards.

---

## 9. Python Requirements File

Create this file at `requirements.txt` in the project root. Every package below is required for the project to run.

```
# Core Framework
fastapi==0.111.1
uvicorn[standard]==0.30.1
python-multipart==0.0.9        # For file upload endpoints

# LangGraph + LangChain
langgraph==0.2.14
langchain==0.2.12
langchain-core==0.2.29
langchain-google-genai==1.0.8  # Gemini via LangChain

# Observability
langfuse==2.36.1               # Tracing + HITL visibility

# Database
sqlalchemy==2.0.31
aiosqlite==0.20.0              # Async SQLite support

# PDF / DOCX Parsing
PyMuPDF==1.24.7                # fitz — best PDF text extractor
python-docx==1.1.2

# Job Scraping
apify-client==1.7.1

# Gmail API
google-auth==2.32.0
google-auth-oauthlib==1.2.1
google-auth-httplib2==0.2.0
google-api-python-client==2.139.0

# Utilities
python-dotenv==1.0.1           # Load .env file
pydantic==2.8.2                # Data validation (FastAPI uses this)
pydantic-settings==2.4.0       # Settings from .env
httpx==0.27.0                  # Async HTTP client for tests
```

---

## 10. Risk Management

These are the most likely failure points and how to handle each one during your 12-hour build.

**Apify free tier rate limits.** The free tier has limited actor compute units. Always check Apify results from the first run are cached in SQLite. If you hit limits during the demo, have a pre-populated SQLite database with real job results ready as a fallback.

**Gemini rate limits.** The free tier has per-minute token limits. If you hit rate limits during CV tailoring, add a `time.sleep(2)` between calls. Use `gemini-1.5-flash` not `gemini-1.5-pro` — Flash has higher free tier limits.

**Gmail OAuth2 on first run.** The first time Gmail is used, a browser window will open asking for consent. Do this during setup (Phase 0), not during the demo. After the token is saved to `credentials/token.json`, subsequent runs are automatic.

**LangGraph checkpoint storage.** By default, LangGraph uses in-memory checkpointing. If FastAPI restarts between the user submitting an application and approving it (unlikely in 12 hours but possible), the paused state is lost. For demo safety, add a simple file-based checkpoint: serialize `PAUSED_STATES` to a JSON file after each pause.

**Lovable frontend code quality.** Lovable generates functional React code but may use patterns that conflict with the real API. Always test each page's API integration in isolation using the browser's Network tab to confirm the correct data is flowing.
