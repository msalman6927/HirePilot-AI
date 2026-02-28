# AI_CONTEXT.md
# HirePilot-AI — AI Development Context File
**Purpose:** This file exists so GitHub Copilot can understand the entire project state at any point in time and continue development without losing context. Read this file first before touching any code.
**Version:** 1.0.0 | **Last Updated:** 2026-02-28

---

## 1. Project Overview (For Copilot)

You are helping build **HirePilot-AI** — a locally-deployed, single-user AI agent system that automates the entire job acquisition process for one person. It is not a SaaS product. It is a personal command center.

The system works like this: the user types a job-related request in a chat window. A central Orchestrator Agent (built with LangGraph) reads the request, detects what the user wants, and activates the right combination of specialized sub-agents. These agents can search for real jobs (using Apify to scrape LinkedIn and Indeed), parse and tailor a CV (using logic from the BowJob open-source project, adapted for Gemini), find HR email addresses, and send real job application emails via Gmail. Before any email is sent, the system pauses and asks the user to review and approve the tailored CV and email draft — this is the Human-in-the-Loop (HITL) gate. Every agent action is traced in Langfuse so the user can see exactly what is happening at all times.

The frontend is a React application with a dark "command center" aesthetic (dark navy background, neon electric blue/green accents), designed in Lovable and approved by the project instructor. It has five main pages: CV Upload, AI Chatbot, Job Matching, Application Prep (HITL), and a Dashboard with five tabs. The frontend communicates with a FastAPI Python backend. All data is stored in a local SQLite database. The LLM is Gemini 1.5 Flash (free tier).

---

## 2. Technology Stack (Do Not Change These)

The backend uses Python with FastAPI as the web framework and LangGraph for the multi-agent orchestration graph. The LLM is Google Gemini 1.5 Flash accessed via the `langchain-google-genai` package. Observability uses Langfuse with both the `CallbackHandler` for automatic LLM tracing and the `@observe` decorator for agent-level spans. The database is SQLite accessed via SQLAlchemy ORM. Job scraping uses the Apify Python client (`apify-client`). Email sending uses the Gmail API via `google-api-python-client`. PDF extraction uses PyMuPDF (`fitz`). DOCX extraction uses `python-docx`.

The frontend uses React 18 with Vite as the build tool, Tailwind CSS for styling, Zustand for global state management, and Axios for API calls.

---

## 3. BowJob Reference Code (Critical Context)

The BowJob project (`https://github.com/rurahim/BowJob`) provides two production-tested Python classes that form the intellectual core of the CV-related agents. You must treat these classes as authoritative. Do not rewrite their logic from scratch — port them.

`CVParserV3` from `cv_parser.py` contains: a 300-line JSON schema defining every field to extract from a CV (contact_info, work_experience, education, projects, skills, certifications, etc.), a detailed system prompt instructing the LLM to map all CV content to the schema, and the full extraction pipeline. Originally uses OpenAI — replace with Gemini via LangChain's `ChatGoogleGenerativeAI`.

`CVImprovementEngine` from `cv_improvement.py` contains: a deterministic `calculate_match_score()` function that scores a CV against a job description using keyword matching across five weighted dimensions (skills 35%, experience 25%, education 15%, projects 15%, keywords 10%), an `analyze()` function that uses the LLM to generate specific modifications to make the CV more relevant to a job, a `_apply_project_guardrail()` function ensuring at least 3 projects always appear, and an `_add_field_paths()` function that generates JSON path strings so the frontend knows exactly which field in the CV to update. Originally uses OpenAI — replace with Gemini via LangChain.

The critical design pattern from BowJob is the `cv_sections` vs `non_cv_sections` distinction: modifications to content that already exists in the CV go into `cv_sections`, and entirely new content for sections that were empty or missing in the original CV goes into `non_cv_sections`. The frontend uses this distinction to show "modified" vs "new" badges on each suggestion.

---

## 4. LangGraph Architecture (Critical Context)

The entire agent system is built as a LangGraph `StateGraph`. Understanding this architecture is essential for continuing development correctly.

A `StateGraph` is a directed graph where each node is a Python function and the edges between nodes define execution flow. All nodes share a single `HirePilotState` TypedDict object that gets passed from node to node, with each node reading what it needs and writing its results back. Think of it like a baton in a relay race — the state is the baton.

The most important LangGraph concept in this project is `interrupt_before=["hitl_gate"]` in the `graph.compile()` call. This tells LangGraph: when you reach the node named `hitl_gate`, stop everything, save the entire state to a checkpoint, and return control to the caller (FastAPI). The graph is effectively "frozen" at this point. When the user approves the application, FastAPI calls `graph.invoke(saved_state)` again with the updated state (now with `hitl_approved=True`), and LangGraph resumes from exactly where it left off, executing the `hitl_gate` node and proceeding to `apply`.

The `PAUSED_STATES` dictionary in `apply_agent.py` serves as the temporary storage for these frozen graph states between the pause and the resume. This is an in-memory solution appropriate for local single-user deployment.

---

## 5. Langfuse Integration (Critical Context)

Langfuse provides full observability — every LLM call, agent action, and user decision is recorded and visible in the Langfuse web dashboard. There are three integration levels used in this project.

The first level is the `CallbackHandler` from `langfuse.callback`. It is passed to the `ChatGoogleGenerativeAI` constructor's `callbacks=[]` parameter. This automatically records every LLM call — the prompt sent, the response received, the token count, and the latency — without any additional code.

The second level is the `@observe` decorator from `langfuse.decorators`. This is placed on each agent node function. It creates a "span" in Langfuse that wraps the entire agent execution. Child LLM calls made inside the agent appear as nested spans under the agent span. Combined with `langfuse_context.update_current_observation(input={...}, output={...})`, you can record what data went into the agent and what came out.

The third level is manual `Langfuse().score()` calls for HITL events. When the user approves or rejects an application, this is logged as a score event in Langfuse, creating a human feedback loop that is visible alongside the trace data.

The Langfuse dashboard is at `cloud.langfuse.com`. After running the application, navigate there to see traces under the "Traces" tab. Each trace represents one user message. Clicking a trace shows the full hierarchy of spans — orchestrator → agent → LLM calls → tool calls — with timing and data at each level.

---

## 6. Completed Decisions

These architectural decisions are final. Do not reopen or relitigate them.

The LLM provider is Gemini 1.5 Flash via `langchain-google-genai`. It is free tier. Do not switch to OpenAI, Claude, or any other provider.

The CV parsing and tailoring logic comes from BowJob. Port it — do not write it from scratch.

The database is SQLite, stored at `./data/hirepilot_ai.db`. No cloud database. No Docker. No Redis.

The HITL mechanism uses `interrupt_before` in LangGraph compile plus `PAUSED_STATES` dict in FastAPI memory.

The frontend design is locked — it was designed in Lovable and approved by the project instructor. Change no visual design decisions. Only wire existing components to real backend data.

Agent logs are stored in both SQLite (for persistence) and forwarded to Langfuse (for observability). Both channels must be updated simultaneously by every agent.

---

## 7. Pending Decisions

These are open questions that the developer must resolve before or during implementation.

The exact Apify actor IDs for LinkedIn and Indeed scrapers must be verified on `apify.com/store` before use — the IDs in `TASK_BREAKDOWN.md` are best-known values but may have changed since this documentation was written. Always verify the actor ID and its `run_input` schema on the Apify marketplace before coding the tool.

The strategy for finding HR email addresses is not fully implemented. The current plan is: check if Apify's job data includes an email, and if not, allow the user to enter the email manually in the HITL approval screen. A more sophisticated email-finding flow can be added after the core pipeline works.

LangGraph checkpoint persistence uses an in-memory dictionary (`PAUSED_STATES`) for the demo. This is sufficient for a local single-user demo where FastAPI stays running. If the server restarts between HITL pause and resume, the state is lost. A file-based fallback (serialize to JSON on disk) should be added as a safety measure before the demo.

---

## 8. Development Phases Summary

Phase 0 is project scaffolding: create the directory structure, install dependencies, verify all API keys work, and run the database setup. Estimated time: 45 minutes.

Phase 1 is the backend foundation: create SQLAlchemy models, the Gemini+Langfuse factory, the empty LangGraph graph, and the FastAPI main app. Estimated time: 2 hours.

Phase 2 is CV upload and job search: implement the CV upload endpoint with BowJob parsing, the Apify scraper tool, the deduplication logic, and the job search agent node. Estimated time: 2.5 hours.

Phase 3 is CV tailoring and HITL: port the BowJob improvement engine, implement the tailoring agent, implement the HITL gate with LangGraph interrupts, and implement the Gmail send agent. Estimated time: 2.5 hours.

Phase 4 is frontend integration: create the API service layer, Zustand store, and wire each of the five pages to real backend calls. Estimated time: 2 hours.

Phase 5 is observability and polish: ensure all agents have `@observe` decorators, verify the Langfuse trace hierarchy is complete and meaningful, and wire the Agent Activity Logs tab to real data. Estimated time: 1 hour.

Phase 6 (if time permits) is the interview prep agent. Estimated time: 30 minutes.

---

## 9. Current Implementation State

**Update this section every time you complete a task.**

As of the creation of this documentation file (2026-02-28), nothing has been implemented yet. The markdown documentation files are the only deliverables. Implementation has not started.

```
PHASE 0 - SCAFFOLDING:         [ 0 tasks are complete. The implementation has not started, and the first step is Phase 0 - Scaffolding (TASK-001).] 
PHASE 1 - BACKEND FOUNDATION:  [ ] Not started
  ├── config.py                 [ ]
  ├── database.py + models      [ ]
  ├── gemini_llm.py             [ ]
  ├── main.py                   [ ]
  └── orchestrator.py (empty)   [ ]

PHASE 2 - CV + JOB SEARCH:     [ ] Not started
  ├── _cv_schema.py (BowJob)    [ ]
  ├── cv_parser_agent.py        [ ]
  ├── CV upload endpoint        [ ]
  ├── apify_tool.py             [ ]
  └── job_search_agent.py       [ ]

PHASE 3 - TAILOR + HITL:       [ ] Not started
  ├── _cv_improvement_schema.py [ ]
  ├── cv_tailoring_agent.py     [ ]
  ├── hitl_gate_node            [ ]
  ├── gmail_tool.py             [ ]
  └── apply_agent.py            [ ]

PHASE 4 - FRONTEND:            [ ] Not started
  ├── api.js (service layer)    [ ]
  ├── appStore.js (Zustand)     [ ]
  ├── CVUpload.jsx wired        [ ]
  ├── Chatbot.jsx wired         [ ]
  ├── JobMatching.jsx wired     [ ]
  ├── ApplicationPrep.jsx wired [ ]
  └── Dashboard.jsx wired       [ ]

PHASE 5 - OBSERVABILITY:       [ ] Not started
  ├── @observe on all agents    [ ]
  ├── Langfuse trace verified   [ ]
  └── Activity Logs tab wired   [ ]

PHASE 6 - INTERVIEW PREP:      [ ] Not started (optional)
```

---

## 10. Resume Markers for Copilot

When you return to this project after a break, look at the implementation state table above. Find the first `[ ] Not started` item. That is where you continue. The task reference in `TASK_BREAKDOWN.md` is the primary guide — find the task corresponding to that item and execute it.

**If you are resuming after Phase 1 is complete:** The backend server is running at `http://localhost:8000`. `POST /chat` returns a response. A trace appears in Langfuse. Begin TASK-008 (port BowJob CV schema to `_cv_schema.py`).

**If you are resuming after Phase 2 is complete:** Job search works end-to-end. `POST /chat` with a job search query returns real jobs. Begin TASK-017 (port BowJob CV improvement schema).

**If you are resuming after Phase 3 is complete:** The full backend pipeline works — upload CV → search jobs → tailor CV → HITL approval → send email. All traces appear in Langfuse. Begin TASK-022 (create frontend API service layer).

**If you are resuming after Phase 4 is complete:** The entire application works through the UI. Begin Phase 5 — add `@observe` decorators to all agents and verify Langfuse traces are complete.

---

## 11. Instructions for GitHub Copilot

Read these instructions carefully every time you start a new Copilot session.

**Rule 1 — Always check this file first.** Before generating any code, read the "Current Implementation State" section to understand what already exists. Never regenerate code for completed items.

**Rule 2 — Never change the tech stack.** The LLM is Gemini, the graph framework is LangGraph, the database is SQLite, and the frontend is React+Vite+Tailwind. Do not suggest alternatives, even if you think another approach is better.

**Rule 3 — Port BowJob, don't rewrite it.** When implementing anything CV-related, the logic comes from the BowJob files. Copy the schemas, prompts, and algorithms. Replace only `OpenAI(api_key=...)` with `ChatGoogleGenerativeAI(model='gemini-1.5-flash', google_api_key=...)`. Replace `client.chat.completions.create(...)` with `llm.invoke([HumanMessage(content=prompt)])`.

**Rule 4 — Wrap every LLM call in Langfuse tracing.** Every function that calls `llm.invoke()` must use `get_llm()` from `backend/tools/gemini_llm.py` (which pre-wires Langfuse). Every agent node function must have `@observe(name="AgentName")`. The instructor will check Langfuse during the demo.

**Rule 5 — Follow the exact file structure.** All agent logic goes in `backend/agents/`. All external API integrations go in `backend/tools/`. All FastAPI route definitions go in `backend/routers/`. All SQLAlchemy models go in `backend/models/`. Never put business logic in `main.py`.

**Rule 6 — The HITL gate is non-negotiable.** No email is ever sent without `state['hitl_approved'] == True`. The LangGraph graph must be compiled with `interrupt_before=['hitl_gate']`. The `POST /apply/approve` endpoint is the only way to set `hitl_approved=True` and resume execution.

**Rule 7 — Test each phase before moving to the next.** Use the acceptance test described in each task to confirm the feature works before starting the next task. A solid Phase 1 foundation prevents 80% of debugging time in later phases.

**Rule 8 — Add an agent_log entry at the start and end of every agent node.** Every node function must append to `state['agent_logs']` with at minimum: `agent_name`, `action` (human-readable description of what it's doing), `status` ("running" at start, "completed" or "failed" at end). Also save these to the SQLite `agent_logs` table. This powers the real-time Activity Feed tab in the dashboard.

**Rule 9 — Handle Gemini JSON responses carefully.** Gemini sometimes wraps JSON responses in markdown code fences (` ```json ... ``` `). Always use the `clean_json_response()` utility from `gemini_llm.py` before calling `json.loads()` on any Gemini output. Wrap all `json.loads()` calls in try/except.

**Rule 10 — This is a demo build.** When choosing between a simple solution and a complete solution, choose the simpler one that still demonstrates the feature correctly. The goal is a working, impressive demo by Sunday. Perfect code architecture can come later.

---

## 12. Key Concepts Explained for Copilot

**LangGraph StateGraph:** A directed graph where Python functions are nodes and the state dict flows between them. `graph.compile(interrupt_before=["node_name"])` makes the graph pauseable at that node. `graph.invoke(state)` runs the graph until it either finishes or hits an interrupt. After an interrupt, `graph.invoke(updated_state)` resumes from the checkpoint.

**Langfuse `@observe`:** A decorator from `langfuse.decorators` that automatically creates a trace span for the decorated function. All LLM calls made inside the decorated function are automatically nested under it in the Langfuse dashboard. Use `langfuse_context.update_current_observation(input=..., output=...)` inside to add data to the span.

**BowJob `cv_sections` vs `non_cv_sections`:** When tailoring a CV, modifications to sections that already have content (like rewriting an existing work experience bullet) go into `cv_sections`. Entirely new content for sections that were empty or missing (like adding a certifications section when the user had none) goes into `non_cv_sections`. The frontend uses these two buckets to render "modified" (yellow badge) vs "new" (green badge) content.

**Apify Actors:** Pre-built web scrapers deployed on Apify's cloud. You run them via `client.actor("actor-id").call(run_input={...})`. They return results as a "dataset" that you iterate with `client.dataset(run["defaultDatasetId"]).iterate_items()`. The free tier has limited monthly compute units, so always cache results in SQLite.

**Gmail OAuth2 Token Flow:** The first time you run, a browser window opens for the user to log into Gmail and grant permission. This creates `credentials/token.json`. All subsequent runs load credentials from this file automatically. The `InstalledAppFlow` handles all this. Never hardcode Gmail passwords — only use OAuth2.
