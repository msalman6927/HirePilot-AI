# PROJECT_REQUIREMENTS.md
# HirePilot-AI — AI-Powered Job Acquisition System
**Version:** 1.0.0 | **Last Updated:** 2026-02-28 | **Status:** Active Development

---

## 1. Project Overview

The HirePilot-AI (Digital Full-Time Employee) is a locally-deployed, single-user autonomous AI agent system that acts as a personal job acquisition employee. The user interacts with a natural language chat interface, and the system autonomously handles everything from finding jobs online to tailoring CVs, sending emails to HR, tracking applications, and preparing the user for interviews. The system is not a SaaS product — it is a personal command center running on the user's Windows machine.

The project was designed under direct guidance from a course instructor and must demonstrate complete, observable, interruptible multi-agent behavior using LangGraph orchestration and Langfuse tracing to qualify for a competitive evaluation on Sunday, February 28, 2026.

---

## 2. Functional Requirements

### FR-01: CV Upload & Parsing
The system must accept a CV file (PDF or DOCX) via a drag-and-drop upload interface. After upload, it must automatically extract all structured information from the CV using the parsing schema defined in the BowJob reference implementation (`cv_parser.py`). The parsed data must be stored in SQLite and displayed as a structured profile summary in the chat interface. The parser must be adapted from the BowJob `CVParserV3` class but powered by Gemini 1.5 Flash instead of GPT-4o-mini.

### FR-02: Natural Language Orchestration
The user must be able to type any job-related query in natural language into the chat interface (examples: "Find me Python developer jobs in Lahore", "Apply to the top 3 jobs", "Prepare me for a data science interview"). The Orchestrator Agent must read the query, detect the user's intent, decide which sub-agents to activate, determine their execution order, and route data between them — all without the user specifying which agents to use.

### FR-03: Job Search Agent
The Job Search Agent must crawl real job listings from LinkedIn and Indeed using the Apify API (free tier). It must deduplicate results where the same job is posted on multiple platforms (deduplication key: normalized company name + job title + location). It must match jobs against the user's CV profile using a match score algorithm based on the BowJob `CVImprovementEngine.calculate_match_score()` logic. Results must be displayed on the Jobs tab with match percentage rings and a "Best Match" badge on the top 3 results.

### FR-04: CV Tailoring Agent (Resume & Profile Builder)
For each job the user selects, the agent must generate a tailored version of the CV using the BowJob `CVImprovementEngine.analyze()` logic adapted for Gemini. The agent must produce ATS-optimized keyword alignment, inject relevant project keywords naturally, suggest new skills to add, and rewrite experience bullet points. The agent must distinguish between modifying existing CV content (`cv_sections`) and adding entirely new content (`non_cv_sections`) — exactly as implemented in the BowJob reference code.

### FR-05: Human-in-the-Loop (HITL) Approval
Before the Apply Agent sends any email, the system must pause execution and present the user with: the tailored CV (rendered as a document preview), the AI-generated cover letter/email draft, and a checkbox labeled "I have reviewed and approve this application." The "Send Email" button must remain disabled until this checkbox is checked. The user must also be able to click an "Edit" button to make inline modifications before approving. This is a non-negotiable requirement — no email is ever sent without explicit user approval.

### FR-06: Apply Agent
After user approval, the Apply Agent must compose a professional job application email, attach or embed the tailored CV content, and send it via the user's Gmail account using the Gmail API. It must log the application to SQLite with: job title, company, date sent, email address contacted, and initial status "Sent." The agent must also fetch the HR contact email for each target company using Apify or a web search fallback.

### FR-07: Job Preparation Agent
For any applied-to job, the user must be able to request interview preparation. The agent must generate: role-specific technical interview questions and model answers, behavioral questions using the STAR method, a skill gap analysis comparing the user's CV to the job description, and learning resource recommendations for missing skills. This data must appear in the Interview Prep tab as expandable accordion cards.

### FR-08: Dashboard & Tracking Tabs
The system must maintain five tracking tabs: Uploaded CVs (all CV versions with parsed skill tags), Job Search History (past searches with criteria and result counts), Applications Sent (table with job title, company, date, and color-coded status: Sent / Opened / Interview / Rejected), Interview Prep (per-job prep cards), and Agent Activity Logs (a real-time timeline of every agent action, tool call, and handoff with timestamps).

### FR-09: Full Observability with Langfuse
Every agent action, LLM call, tool invocation, and agent-to-agent handoff must be traced in Langfuse. The user must be able to see all traces in real time. The Agent Activity Logs tab must display a human-readable version of Langfuse trace data. The user must be able to interrupt any running agent from the UI. No agent action should happen invisibly.

### FR-10: Persistent Local Storage
All data (parsed CVs, job results, applications, agent logs, chat history) must be persisted in a local SQLite database. Data must survive application restarts. The database file must be stored at `./data/hirepilot_ai.db`.

---

## 3. Non-Functional Requirements

**Performance:** Job scraping results must appear within 30 seconds for a query of up to 15 results. LLM responses (CV tailoring, email drafting) must complete within 20 seconds using Gemini 1.5 Flash free tier. The application must be responsive on a Windows local machine.

**Reliability:** The Orchestrator must handle partial agent failures gracefully — if the Job Search Agent fails, it must return a clear error message and allow the user to retry rather than crashing the entire pipeline.

**Security:** Gmail OAuth2 tokens must be stored locally in `./credentials/token.json` and never hardcoded. The `.env` file must never be committed to git. A `.gitignore` template must be included in the project.

**Observability:** Langfuse must receive traces for 100% of LLM calls. Every agent must log its start, progress, and completion. The system must never perform an action that is not visible in the Agent Activity Logs tab.

**Maintainability:** All agent logic must be in separate Python modules under `backend/agents/`. All API integrations must be in `backend/tools/`. All database models must be in `backend/models/`. This separation ensures GitHub Copilot can continue development in any module without losing context.

---

## 4. Tech Stack (Locked — Do Not Change)

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Frontend | React + Vite | React 18 | Chat interface, tabs, CV preview |
| Styling | Tailwind CSS | 3.x | Dark theme, neon accents |
| Backend | FastAPI | 0.111+ | REST API, WebSocket for streaming |
| Agent Framework | LangGraph | 0.2+ | Multi-agent orchestration, state management |
| LLM | Gemini 1.5 Flash | via langchain-google-genai | All LLM calls (free tier) |
| Observability | Langfuse | 2.x | Full tracing, HITL visibility |
| Job Scraping | Apify Python Client | 1.x | LinkedIn, Indeed scrapers |
| Email | Gmail API | v1 | Sending job application emails |
| Database | SQLite + SQLAlchemy | 2.x | Local persistent storage |
| PDF Parsing | PyMuPDF (fitz) | 1.24+ | Extract text from uploaded CVs |
| DOCX Parsing | python-docx | 1.x | Extract text from Word files |
| CV Logic | BowJob (adapted) | N/A | CV parsing schema + JD matching engine |

---

## 5. BowJob Reference Implementation

The project must incorporate logic from `https://github.com/rurahim/BowJob` (made public temporarily). Two files are critical:

**`cv_parser.py` → Adapt as `backend/agents/cv_parser_agent.py`**
The `CVParserV3` class defines the complete CV extraction schema (contact info, work experience, education, skills, projects, certifications, etc.) and the system prompt for extraction. Replace the `OpenAI` client with `langchain_google_genai.ChatGoogleGenerativeAI` and use `with_structured_output()` or a Gemini-compatible function calling approach. Keep the schema identical — it is production-tested and comprehensive.

**`cv_improvement.py` → Adapt as `backend/agents/cv_tailoring_agent.py`**
The `CVImprovementEngine` class defines: the deterministic `calculate_match_score()` method (use as-is, no LLM needed), the `analyze()` method for JD-driven CV tailoring (adapt for Gemini), the project guardrail ensuring minimum 3 projects, and the `_add_field_paths()` method for frontend patch targeting. Keep the `cv_sections` vs `non_cv_sections` distinction exactly as designed.

---

## 6. Constraints

The system must run entirely on a Windows local machine. All API calls use free tiers (Gemini free, Apify free, Langfuse cloud free). No Docker is required for MVP. No user authentication is needed (single user). The frontend was designed in Lovable and already approved by the instructor — its visual design must not be changed, only wired to the real backend.

---

## 7. Evaluation Criteria (Demo Day)

The instructor will evaluate: whether all 5 agents are working end-to-end, whether Langfuse traces are visible and complete, whether HITL approval gates are working before email sends, whether the UI matches the approved Lovable design, and whether the student can explain every component confidently. Two to three top performers will receive direct mentorship, monthly pocket money, and a Claude Pro subscription.
