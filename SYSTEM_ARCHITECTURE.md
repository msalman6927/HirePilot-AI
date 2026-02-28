# SYSTEM_ARCHITECTURE.md
# HirePilot-AI — System Architecture
**Version:** 1.0.0 | **Last Updated:** 2026-02-28

---

## 1. Architectural Philosophy

HirePilot-AI follows an **Event-Driven Multi-Agent Architecture** where a central Orchestrator Agent acts as the brain, and specialized sub-agents act as the hands. The system is designed so every action is visible, every decision is traceable, and the human can interrupt at any point. This is not a pipeline that runs silently in the background — it is a transparent control tower.

The architecture uses **LangGraph StateGraph** as the backbone for agent coordination. Think of LangGraph as a directed graph where each node is an agent or a tool, and the edges between nodes are conditional — the Orchestrator decides which edge to follow based on the user's intent and the current state of execution.

---

## 2. High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    REACT FRONTEND (Vite)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │   Chat   │ │ Jobs Tab │ │ Apply Tab│ │  Dashboard Tabs  │  │
│  │Interface │ │ (results)│ │  (HITL)  │ │ (logs,prep,hist) │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────────┬─────────┘  │
│       │            │            │                 │            │
│  ─────┴────────────┴────────────┴─────────────────┴──── REST/WS│
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   FastAPI Backend   │
                    │  (main.py, port    │
                    │     8000)          │
                    └─────────┬──────────┘
                              │
              ┌───────────────▼────────────────┐
              │    LANGGRAPH ORCHESTRATOR       │
              │  (orchestrator_graph.py)        │
              │                                 │
              │  Intent Detection → Routing     │
              │  State Management (SharedState) │
              │  Agent Lifecycle Control        │
              └──┬────────┬────────┬────────┬───┘
                 │        │        │        │
    ┌────────────▼┐  ┌────▼─────┐ ┌▼──────┐ ┌▼──────────┐
    │Job Search   │  │CV Tailor │ │Apply  │ │ Job Prep  │
    │Agent        │  │Agent     │ │Agent  │ │ Agent     │
    │(apify_tool) │  │(bowjob   │ │(gmail │ │(gemini    │
    │             │  │ adapted) │ │ api)  │ │ prompts)  │
    └─────────────┘  └──────────┘ └───────┘ └───────────┘
                              │
              ┌───────────────▼────────────────┐
              │         TOOL LAYER             │
              │  apify_tool.py                 │
              │  gmail_tool.py                 │
              │  cv_parser_tool.py             │
              │  gemini_llm.py                 │
              └───────────────┬────────────────┘
                              │
              ┌───────────────▼────────────────┐
              │      PERSISTENCE LAYER         │
              │   SQLite (hirepilot_ai.db)      │
              │   SQLAlchemy ORM               │
              │   Models: Job, Application,    │
              │   CVVersion, AgentLog, Chat    │
              └────────────────────────────────┘
                              │
              ┌───────────────▼────────────────┐
              │      OBSERVABILITY LAYER       │
              │   Langfuse Cloud               │
              │   CallbackHandler on all LLMs  │
              │   @observe on all agent funcs  │
              │   HITL events as custom traces │
              └────────────────────────────────┘
```

---

## 3. Directory Structure

Every file path in this project is deliberate. GitHub Copilot must create files in exactly these locations.

```
hirepilot-ai/
│
├── backend/                          # Python FastAPI backend
│   ├── main.py                       # FastAPI app entry point, all routes
│   ├── config.py                     # Settings from .env (pydantic-settings)
│   ├── database.py                   # SQLAlchemy engine + session factory
│   │
│   ├── models/                       # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── job.py                    # Job listings table
│   │   ├── application.py            # Applications sent table
│   │   ├── cv_version.py             # CV versions (original + tailored)
│   │   ├── agent_log.py              # Agent activity log table
│   │   └── chat_message.py           # Chat history table
│   │
│   ├── agents/                       # LangGraph agent nodes
│   │   ├── __init__.py
│   │   ├── orchestrator.py           # Main LangGraph StateGraph + intent router
│   │   ├── job_search_agent.py       # Job scraping + dedup + matching
│   │   ├── cv_parser_agent.py        # BowJob CVParserV3 adapted for Gemini
│   │   ├── cv_tailoring_agent.py     # BowJob CVImprovementEngine adapted for Gemini
│   │   ├── apply_agent.py            # HITL gate + Gmail sending
│   │   ├── job_prep_agent.py         # Interview prep + skill gap analysis
│   │   └── memory_agent.py           # Short/long-term memory management
│   │
│   ├── tools/                        # External API integrations
│   │   ├── __init__.py
│   │   ├── apify_tool.py             # Apify LinkedIn + Indeed scrapers
│   │   ├── gmail_tool.py             # Gmail API OAuth2 + send
│   │   ├── hr_email_finder.py        # HR email discovery via Apify/search
│   │   └── gemini_llm.py             # Shared Gemini LLM factory with Langfuse CB
│   │
│   ├── schemas/                      # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── chat.py                   # ChatRequest, ChatResponse
│   │   ├── job.py                    # JobResult, JobSearchRequest
│   │   ├── cv.py                     # CVParseResult, CVTailorRequest
│   │   └── application.py            # ApplicationRecord, HITLApproval
│   │
│   └── routers/                      # FastAPI route modules
│       ├── __init__.py
│       ├── chat_router.py            # POST /chat, WebSocket /ws/chat
│       ├── cv_router.py              # POST /cv/upload, GET /cv/versions
│       ├── jobs_router.py            # GET /jobs, GET /jobs/{id}
│       ├── apply_router.py           # POST /apply/approve, POST /apply/send
│       ├── prep_router.py            # GET /prep/{job_id}
│       └── dashboard_router.py       # GET /dashboard/* endpoints
│
├── frontend/                         # React + Vite frontend
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx                   # Router + layout
│   │   ├── pages/
│   │   │   ├── CVUpload.jsx          # Page 1: drag-drop upload
│   │   │   ├── Chatbot.jsx           # Page 2: split-screen chat
│   │   │   ├── JobMatching.jsx       # Page 3: job cards grid
│   │   │   ├── ApplicationPrep.jsx   # Page 4: HITL approval
│   │   │   └── Dashboard.jsx         # Page 5: all tabs
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx        # Chat messages + input
│   │   │   ├── CVProfilePanel.jsx    # Right panel: parsed CV summary
│   │   │   ├── JobCard.jsx           # Single job card with match ring
│   │   │   ├── CVPreview.jsx         # Document-style CV renderer
│   │   │   ├── EmailEditor.jsx       # Editable email draft
│   │   │   ├── HITLApproval.jsx      # Approval checkbox + send button
│   │   │   ├── AgentActivityFeed.jsx # Real-time agent log timeline
│   │   │   └── Sidebar.jsx           # Icon navigation sidebar
│   │   ├── hooks/
│   │   │   ├── useChat.js            # Chat state + WebSocket
│   │   │   ├── useJobs.js            # Job fetch + selection state
│   │   │   └── useAgentLogs.js       # Polling agent activity
│   │   ├── services/
│   │   │   └── api.js                # Axios base URL + all API calls
│   │   └── store/
│   │       └── appStore.js           # Zustand global state
│
├── data/
│   └── hirepilot_ai.db                # SQLite database (auto-created)
│
├── credentials/
│   ├── gmail_credentials.json        # Gmail OAuth2 client credentials
│   └── token.json                    # Auto-generated after first Gmail auth
│
├── .env                              # Environment variables (never commit)
├── .env.example                      # Template for .env
├── .gitignore                        # Must include .env, credentials/, data/
├── requirements.txt                  # All Python dependencies
└── README.md                         # Setup instructions
```

---

## 4. LangGraph State & Graph Architecture

### 4.1 Shared State Schema

LangGraph passes a single shared state object between all agent nodes. Every agent reads from this state and writes its results back into it. This is defined using Python `TypedDict`.

```python
# backend/agents/orchestrator.py

from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END

class HirePilotState(TypedDict):
    # ─── Input ─────────────────────────────────────────
    user_message: str                   # Raw message from user
    session_id: str                     # Unique session identifier
    
    # ─── Intent & Routing ──────────────────────────────
    detected_intent: str                # "job_search" | "apply" | "prep" | "cv_build" | "general"
    agents_to_activate: List[str]       # Ordered list of agent names to run
    
    # ─── CV Data ───────────────────────────────────────
    cv_raw_text: Optional[str]          # Extracted text from uploaded PDF/DOCX
    cv_parsed: Optional[Dict]           # BowJob parsed CV structure
    cv_tailored: Optional[Dict]         # BowJob tailored CV for specific job
    cv_version_id: Optional[int]        # SQLite FK to cv_version table
    
    # ─── Job Search ────────────────────────────────────
    job_search_query: Optional[str]     # e.g. "Python developer Lahore"
    jobs_fetched: Optional[List[Dict]]  # Raw Apify results (deduplicated)
    jobs_matched: Optional[List[Dict]]  # Jobs with match_score added
    selected_job: Optional[Dict]        # Job user clicked "Select" on
    
    # ─── Application ───────────────────────────────────
    hr_email: Optional[str]             # Found HR contact email
    email_draft: Optional[str]          # AI-generated email body
    hitl_approved: bool                 # Has user clicked "Approve"?
    application_id: Optional[int]       # SQLite FK after successful send
    
    # ─── Prep ──────────────────────────────────────────
    interview_prep: Optional[Dict]      # Generated Q&A, skill gaps, resources
    
    # ─── System ────────────────────────────────────────
    agent_logs: List[Dict]              # Timeline of all agent actions
    error: Optional[str]                # Error message if an agent fails
    final_response: Optional[str]       # Text to show user in chat
    langfuse_trace_id: Optional[str]    # For linking frontend to Langfuse
```

### 4.2 Graph Definition

The Orchestrator builds a `StateGraph` and connects agent nodes with conditional edges.

```python
# backend/agents/orchestrator.py — Graph construction

def build_graph():
    graph = StateGraph(HirePilotState)

    # Register all agent nodes
    graph.add_node("intent_router", intent_router_node)
    graph.add_node("job_search", job_search_node)
    graph.add_node("cv_parser", cv_parser_node)
    graph.add_node("cv_tailor", cv_tailor_node)
    graph.add_node("hitl_gate", hitl_gate_node)       # PAUSES execution here
    graph.add_node("apply", apply_node)
    graph.add_node("job_prep", job_prep_node)
    graph.add_node("responder", responder_node)

    # Entry point
    graph.set_entry_point("intent_router")

    # Conditional routing from intent_router
    graph.add_conditional_edges(
        "intent_router",
        route_by_intent,                               # Returns node name string
        {
            "job_search": "job_search",
            "apply": "cv_tailor",                      # Apply always tailors first
            "prep": "job_prep",
            "cv_build": "cv_parser",
            "general": "responder"
        }
    )

    # Fixed edges after each agent
    graph.add_edge("job_search", "responder")
    graph.add_edge("cv_parser", "responder")
    graph.add_edge("cv_tailor", "hitl_gate")           # Always HITL before apply
    graph.add_edge("hitl_gate", "apply")               # Only reaches here after approval
    graph.add_edge("apply", "responder")
    graph.add_edge("job_prep", "responder")
    graph.add_edge("responder", END)

    # Compile with interrupt BEFORE hitl_gate
    # This is LangGraph's built-in human-in-the-loop mechanism
    return graph.compile(interrupt_before=["hitl_gate"])
```

The key insight here is `interrupt_before=["hitl_gate"]`. When LangGraph reaches the `hitl_gate` node, it **pauses the entire graph**, saves its state, and returns control to FastAPI. FastAPI then sends the tailored CV and email draft to the frontend. Only when the user clicks "Approve" does FastAPI call `graph.invoke(state, config)` again, which resumes from the saved checkpoint past the gate and proceeds to the `apply` node.

---

## 5. FastAPI Backend Architecture

### 5.1 Application Entry Point

```python
# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import create_tables
from backend.routers import chat_router, cv_router, jobs_router, apply_router

app = FastAPI(title="HirePilot-AI API", version="1.0.0")

# Allow React frontend on port 5173 to call the backend on port 8000
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
async def startup():
    create_tables()  # Create SQLite tables if they don't exist

app.include_router(chat_router.router, prefix="/chat")
app.include_router(cv_router.router, prefix="/cv")
app.include_router(jobs_router.router, prefix="/jobs")
app.include_router(apply_router.router, prefix="/apply")
```

### 5.2 Key API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Main chat endpoint — triggers Orchestrator |
| WebSocket | `/ws/chat/{session_id}` | Streaming agent status updates to UI |
| POST | `/cv/upload` | Upload PDF/DOCX, trigger CV parser |
| GET | `/cv/versions` | List all stored CV versions |
| GET | `/jobs` | Get latest fetched jobs for a session |
| POST | `/jobs/search` | Trigger Job Search Agent manually |
| GET | `/apply/preview/{job_id}` | Get tailored CV + email draft for HITL |
| POST | `/apply/approve` | User approval — resumes LangGraph graph |
| POST | `/apply/send` | Actually send email via Gmail API |
| GET | `/dashboard/applications` | All sent applications with status |
| GET | `/dashboard/logs` | Agent activity timeline |
| GET | `/prep/{job_id}` | Interview prep for a specific job |

---

## 6. Langfuse Integration Architecture

Langfuse is the observability backbone. It must be wired into every LLM call and every agent function. There are three integration patterns used in this project.

**Pattern 1: LangChain CallbackHandler** — Added to every Gemini LLM instantiation. This automatically traces every LLM call (prompt sent, tokens used, response received) without any additional code.

```python
# backend/tools/gemini_llm.py

from langfuse.callback import CallbackHandler
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.config import settings

def get_llm(session_id: str, agent_name: str):
    """Factory that returns a Gemini LLM instance pre-wired to Langfuse."""
    langfuse_handler = CallbackHandler(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_HOST,          # "https://cloud.langfuse.com"
        session_id=session_id,
        metadata={"agent": agent_name}
    )
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=settings.GEMINI_API_KEY,
        callbacks=[langfuse_handler],          # Automatic tracing
        temperature=0.3
    )
    return llm, langfuse_handler
```

**Pattern 2: `@observe` Decorator** — Used on top-level agent functions to create a parent span that groups all child LLM calls made within that agent under one trace.

```python
# backend/agents/job_search_agent.py

from langfuse.decorators import observe, langfuse_context

@observe(name="JobSearchAgent")
def run_job_search(state: HirePilotState) -> HirePilotState:
    langfuse_context.update_current_observation(
        input={"query": state["job_search_query"]},
        metadata={"session_id": state["session_id"]}
    )
    # ... agent logic ...
    langfuse_context.update_current_observation(
        output={"jobs_found": len(state["jobs_fetched"])}
    )
    return state
```

**Pattern 3: Manual Score Events** — When the user approves or rejects an application in the HITL gate, log this as a Langfuse score event, creating a feedback loop.

```python
# backend/agents/apply_agent.py

from langfuse import Langfuse
langfuse = Langfuse()

def log_hitl_decision(trace_id: str, approved: bool):
    langfuse.score(
        trace_id=trace_id,
        name="hitl_approval",
        value=1 if approved else 0,
        comment="User approved" if approved else "User rejected"
    )
```

---

## 7. Database Schema (SQLite via SQLAlchemy)

```sql
-- Auto-created by SQLAlchemy from models/

CREATE TABLE cv_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    raw_text TEXT,
    parsed_data JSON,           -- Full BowJob parsed CV dict
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    platform TEXT,              -- "linkedin" | "indeed"
    job_url TEXT,
    description TEXT,
    match_score REAL,           -- 0-100 from calculate_match_score()
    hr_email TEXT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company, title, location)  -- Deduplication constraint
);

CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER REFERENCES jobs(id),
    cv_version_id INTEGER REFERENCES cv_versions(id),
    tailored_cv JSON,           -- The specific tailored CV sent
    email_draft TEXT,
    hr_email TEXT,
    sent_at TIMESTAMP,
    status TEXT DEFAULT 'Sent'  -- Sent / Opened / Interview / Rejected
);

CREATE TABLE agent_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    agent_name TEXT NOT NULL,
    action TEXT NOT NULL,       -- e.g. "Fetching jobs from LinkedIn via Apify"
    status TEXT,                -- "running" | "completed" | "failed"
    metadata JSON,
    langfuse_trace_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    role TEXT NOT NULL,         -- "user" | "assistant"
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 8. Environment Variables (.env)

```bash
# .env — Never commit this file

# Gemini (Google AI Studio — free tier)
GEMINI_API_KEY=your_gemini_api_key_here

# Langfuse (cloud.langfuse.com — free tier)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# Apify (apify.com — free tier)
APIFY_API_TOKEN=apify_api_...

# Gmail OAuth2 (Google Cloud Console)
GMAIL_CLIENT_ID=....apps.googleusercontent.com
GMAIL_CLIENT_SECRET=GOCSPX-...
GMAIL_REDIRECT_URI=http://localhost:8000/auth/gmail/callback

# App settings
DATABASE_URL=sqlite:///./data/hirepilot_ai.db
FRONTEND_URL=http://localhost:5173
```

---

## 9. Data Flow for the Primary Use Case

To make the architecture concrete, here is the complete data flow when a user types "Find Python developer jobs in Lahore and apply to the best one":

1. React sends `POST /chat` with the message and session_id.
2. FastAPI calls `orchestrator.run(message, session_id)`.
3. LangGraph enters the `intent_router` node. Gemini detects dual intent: `job_search` + `apply`.
4. Graph routes to `job_search` node. Apify scraper runs LinkedIn + Indeed actors. Results deduplicated. Match scores calculated against parsed CV. Results stored in SQLite `jobs` table.
5. FastAPI returns job results to React. Jobs tab updates with match percentage rings.
6. User clicks "Select" on the best job. React sends `POST /apply/preview/{job_id}`.
7. FastAPI resumes graph at `cv_tailor` node. BowJob `CVImprovementEngine.analyze()` runs with the job's description. Returns `cv_sections` + `non_cv_sections` changes.
8. Graph reaches `hitl_gate`. **Graph pauses.** State saved.
9. FastAPI sends tailored CV + email draft to React. Application Prep page renders.
10. User reviews, optionally edits, checks "I approve," clicks Send.
11. React sends `POST /apply/approve` with session_id and any edits.
12. FastAPI resumes LangGraph from checkpoint. `apply` node runs Gmail API to send email.
13. Application logged to SQLite. Langfuse receives complete trace.
14. React Applications tab updates with new row showing status "Sent."
