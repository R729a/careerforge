# CareerForge AI
An AI-Powered Multi-Agent Career Growth Platform

CareerForge AI is a multi-agent system designed to help students and professionals build personalized career roadmaps, decompose and optimize daily learning tasks, schedule study blocks, generate mock practice quizzes, and track learning progress—all within a highly secured, audit-logged environment.

---

## Key Features

1. **Multi-Agent Orchestration (ADK):** Exposes specialized agents (Planner, Task Optimization, Study Coach, and Life Scheduler) structured under a Master Orchestrator coordinating lifecycle requests.
2. **Model Context Protocol (MCP):** Connects reasoning agents to systems and tools (Course DB, Skills DB, Resume Parser, Calendar scheduling, and Job market statistics).
3. **Advanced Security Layers:** Incorporates local regex-based input validation, Cross-Site Scripting (XSS) input sanitization, PII masking/re-hydration, and correlation-linked security audit logging.
4. **Interactive Dashboard:** Premium glassmorphic web interface showing active roadmaps, task pipelines, live test taking, and audit trace logs.

---

## Directory Structure

```text
careerforge-ai/
│
├── agents/                     # ADK Agent Definitions
│   ├── base_agent.py           # Base agent class with LLM configuration & local fallback
│   ├── orchestrator.py         # Master Orchestrator coordinating pipelines
│   ├── planner.py              # Advisor Agent creating milestones & courses
│   ├── task_optimizer.py       # Tactical Agent decomposing goals to hourly tasks
│   ├── study_coach.py          # Academic Coach creating summaries & quizzes
│   └── scheduler.py            # Calendar Agent blocking study hours
│
├── mcp_server/                 # Model Context Protocol
│   └── main.py                 # FastMCP stdio server exposing database and file tools
│
├── backend/                    # FastAPI Web Server
│   └── app/
│       ├── main.py             # Server endpoints & static file serving router
│       └── security/           # Token Auth, HTML Sanitization, and PII Masking
│           ├── auth_handler.py
│           ├── pii_scrubber.py
│           └── sanitizer.py
│
├── db/                         # Database schema scripts
│   └── schema.sql
│
├── frontend/                   # Client interface
│   └── static/
│       └── index.html          # Glassmorphic single page dashboard mockup
│
├── scripts/                    # Platform control utilities
│   ├── bootstrap_db.py         # Database initializer and course/skill seeder
│   └── test_integration.py     # Multi-agent end-to-end integration test runner
│
├── requirements.txt            # Python dependencies list
└── docker-compose.yml          # Containerized deployment settings
```

---

## Quick Start Guide

Follow these steps to run the platform locally:

### 1. Environment Setup
Clone the repository, create a virtual environment, and install dependencies:
```bash
# Create python virtual env
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install requirements
python -m pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your Gemini API key (optional—runs in safe mock mode otherwise):
```bash
cp .env.example .env
```

### 3. Bootstrap Local Database
Create database tables and seed them with skills and course catalogs:
```bash
python scripts/bootstrap_db.py
```

### 4. Run System Integration Test
Programmatically verify auth flows, agent reasoning, PII scrubbing, database writes, and audit logs:
```bash
python scripts/test_integration.py
```

### 5. Launch FastAPI Web Server
Start the backend web app, which also hosts the frontend interface:
```bash
python -m uvicorn backend.app.main:app --reload
```
Open [http://localhost:8000](http://localhost:8000) in your web browser to access the CareerForge AI Dashboard.

---

## Multi-Agent Workflow

```text
[User Request] ──> [Security Sanitizer] ──> [PII Masker] ──> [Master Orchestrator]
                                                                     │
               ┌───────────────────────┬─────────────────────────────┼────────────────────────┐
               ▼                       ▼                             ▼                        ▼
       [Planner Agent]        [Task Opt. Agent]             [Scheduler Agent]         [Study Coach Agent]
   - Generates Roadmap     - Decomposes Milestones        - Reads user Calendar       - Generates notes
   - Selects Courses       - Estimates Task Hours         - Syncs study slots         - Formulates quizzes
               │                       │                             │                        │
               └───────────────────────┴──────────────┬──────────────┴────────────────────────┘
                                                      ▼
                                           [MCP Tools Execution Gate]
                                                      │
                       ┌───────────────────────┬──────┴────────────────┬──────────────────────┐
                       ▼                       ▼                       ▼                      ▼
                [Course DB Tool]        [Skill DB Tool]       [Calendar Tool Tool]     [Resume Parser]
```

---

## Security Protocols

*   **PII Masking Filter:** Raw text is scanned locally for standard identifiers (emails, phone numbers, zip codes) and replaced with token identifiers (e.g., `[EMAIL_1]`) before reaching the LLM API. Results are rehydrated before UI output.
*   **Prompt Injection Protection:** The Input Sanitizer inspects all input fields using heuristic indicators to detect instructions trying to bypass system safety parameters.
*   **Immutable Transaction Log:** An audit log records every agent routing call, tool usage metadata, and session tokens under a shared correlation ID (`x-correlation-id`) to maintain historical validation.
