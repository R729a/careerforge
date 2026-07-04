# 🚀 CareerForge AI

### **An AI-Powered Multi-Agent Career Growth Platform**

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Protocol](https://img.shields.io/badge/protocol-Model%20Context%20Protocol%20%28MCP%29-orange)](https://modelcontextprotocol.io/)
[![Orchestration](https://img.shields.io/badge/orchestration-Google%20ADK-red)](https://github.com/google/ai-edge-developer-kit)
[![Security](https://img.shields.io/badge/security-PII%20Masking%20%26%20Sanitization-green.svg)](https://github.com/R729a/careerforge)

---

## 🎯 Overview

**CareerForge AI** is an advanced multi-agent orchestrator designed to empower students and professionals in charting their career paths. The platform seamlessly generates personalized career roadmaps, breaks down daily milestones into structured hourly tasks, schedules focused study blocks directly into your calendar, and spins up interactive practice quizzes to test your knowledge.

Built with an enterprise-first mindset, the entire system operates within a highly secure framework featuring runtime **PII Masking**, strict **XSS Input Sanitization**, and a tamper-proof **Immutable Audit Logging** pipeline to guarantee absolute data privacy.

---

## 🌟 Key Features

### 1. 🤖 Multi-Agent Orchestration (Google ADK)
*   **Master Orchestrator:** Coordinates the lifecycle, states, and handoffs between multiple specialized agents.
*   **Planner Agent:** Acts as a career advisor to map out macro-milestones, relevant skill sets, and tailored learning paths.
*   **Tactical Task Optimizer:** Decomposes complex daily milestones into realistic, bite-sized hourly tasks.
*   **Study Coach:** Dynamically generates concise revision summaries and interactive practice quizzes based on your roadmap.
*   **Life Scheduler:** A specialized calendar agent that maps and blocks out study hours seamlessly.

### 🔌 2. Model Context Protocol (MCP) Integration
*   Employs a **FastMCP Server** to safely expose external tools, enterprise databases, and system utilities directly to reasoning agents.
*   Provides native tools for interacting with the **Course DB, Skills DB, Resume Parser**, and **Job Market Statistics** to ground LLM responses with real-time data.

### 🛡️ 3. Advanced Security & Privacy Layers
*   **Runtime PII Masking:** Automatically detects and masks sensitive personal identifiers before data hits external LLMs, with secure re-hydration on the client side.
*   **XSS Input Sanitization:** Strict regex-based and HTML sanitization filters targeting malicious scripts to defend against injection attacks.
*   **Immutable Audit Logging:** Generates clear, tamper-proof correlation-linked security audit traces for every agent transaction.

### 💻 4. Premium Interactive Dashboard
*   A sleek, modern user interface featuring real-time visualization of active roadmaps, structured task pipelines, and live test-taking modules.
*   Includes a transparent security center displaying active audit logs and PII filter status.
---

## Directory Structure

```text
careerforge-ai/
│
├── agents/                 # Google ADK Agent Specifications
│   ├── base_agent.py       # Core LLM config and local fallback mechanics
│   ├── orchestrator.py     # Master routing logic for agent communication
│   ├── planner.py          # Career pathing & milestone advisor
│   ├── task_optimizer.py   # Daily-to-hourly task micro-scheduler
│   ├── study_coach.py      # Quiz & summary generation engine
│   └── scheduler.py        # Calendar integration and .ics generation
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
## 📂 Directory Structure

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

## 🛠️ System API Endpoints

The platform exposes structured REST endpoints managed with FastAPI token authentication:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Registers a new student or professional profile. |
| `POST` | `/api/v1/auth/login` | Authenticates sessions and provisions secure bearer tokens. |
| `POST` | `/api/v1/roadmap/generate`| Triggers the Google ADK Orchestrator to compile career milestones. |
| `GET` | `/api/v1/roadmap/active` | Retrieves the active user-specific career roadmap tracks. |
| `GET` | `/api/v1/study/quiz` | Dynamically streams custom quizzes created by the Study Coach. |
| `GET` | `/api/v1/audit/logs` | Exposes local immutable interaction logs to the security panel. |

---

## 🗺️ Project Milestones Checklist

- [x] **Multi-Agent System Implementation** (Google ADK Engine Integration)
- [x] **Production Backend Gateway** (Asynchronous FastAPI Web Framework)
- [x] **Model Context Protocol Core** (Decoupled FastMCP Tools Server)
- [x] **Data Compliance Architecture** (Regex XSS Sanitizers & Token PII Masking)
- [x] **Immutable Audit Trail Execution** (Tamper-Proof Verification Logging)
- [ ] **Google Calendar OAuth 2.0 Ingress** *(Planned Roadmap Update)*

Author
Rudraksh Sahu (R729a)
License
MIT License 

## Security Protocols

*   **PII Masking Filter:** Raw text is scanned locally for standard identifiers (emails, phone numbers, zip codes) and replaced with token identifiers (e.g., `[EMAIL_1]`) before reaching the LLM API. Results are rehydrated before UI output.
*   **Prompt Injection Protection:** The Input Sanitizer inspects all input fields using heuristic indicators to detect instructions trying to bypass system safety parameters.
