import os
import sys
import sqlite3
import uuid
import json
from typing import List, Optional

# Add project root to sys.path to resolve absolute imports from anywhere
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from backend.app.security.auth_handler import auth_handler
from backend.app.security.sanitizer import sanitizer
from agents.orchestrator import MasterOrchestrator
from agents.base_agent import manager



# Initialize FastAPI App
app = FastAPI(
    title="CareerForge AI API",
    description="Multi-Agent Career Growth Platform API",
    version="1.0.0"
)

# Enable CORS for local cross-origin frontend queries if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import asyncio
import agents.base_agent

@app.on_event("startup")
async def startup_event():
    agents.base_agent.main_loop = asyncio.get_running_loop()
    print("[FastAPI Startup] Captured main event loop for thread-safe WebSocket broadcasts.")

security_bearer = HTTPBearer()
orchestrator = MasterOrchestrator()
DB_PATH = "careerforge.db"

# Database Connection Helper
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# JWT Token Validation Dependency
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_bearer)):
    token = credentials.credentials
    payload = auth_handler.decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload  # returns dictionary with "sub" (user_id) and "email"

# Pydantic Schemas
class UserRegister(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class RoadmapRequest(BaseModel):
    target_role: str
    timeline_months: int
    allowed_slots: List[dict]  # e.g., [{"day": "Monday", "start": "18:00", "end": "20:00"}]
    client_id: Optional[str] = None


class QuizSubmitRequest(BaseModel):
    subject: str
    score: float
    total_questions: int

# WebSocket Logging Endpoint
@app.websocket("/ws/logs/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(client_id, websocket)
    try:
        while True:
            # Keep connection open and receive ping/messages if any
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(client_id)

# Auth Endpoints

@app.post("/api/v1/auth/register", status_code=status.HTTP_201_CREATED)
def register(user: UserRegister):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if user exists
    cur.execute("SELECT id FROM users WHERE email = ?", (user.email,))
    if cur.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email is already registered.")
        
    hashed = auth_handler.hash_password(user.password)
    user_id = str(uuid.uuid4())
    
    cur.execute(
        "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
        (user_id, user.email, hashed)
    )
    conn.commit()
    conn.close()
    
    return {"status": "success", "msg": "User registered successfully.", "user_id": user_id}

@app.post("/api/v1/auth/login")
def login(user: UserLogin):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("SELECT id, password_hash FROM users WHERE email = ?", (user.email,))
    row = cur.fetchone()
    conn.close()
    
    if not row or not auth_handler.verify_password(user.password, row[1]):
        raise HTTPException(status_code=400, detail="Invalid email or password.")
        
    token = auth_handler.create_access_token(row[0], user.email)
    return {"access_token": token, "token_type": "bearer"}

# Resume Parsing Endpoint
@app.post("/api/v1/resume/parse")
def parse_resume(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    # Save the file temporarily
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{file.filename}")
    
    try:
        with open(temp_path, "wb") as f:
            f.write(file.file.read())
            
        # Parse it using the resume parsing tool (safe local call via MCP)
        from mcp_server.main import resume_parser_tool
        result_str = resume_parser_tool(temp_path)
        result = json.loads(result_str)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed parsing resume: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# Multi-Agent Orchestration Pipeline Endpoint
@app.post("/api/v1/roadmap/generate")
def generate_roadmap(
    req: RoadmapRequest, 
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["sub"]
    
    # Validation & Sanitization Gateway check
    target_role = req.target_role.strip()
    if not target_role:
        raise HTTPException(status_code=400, detail="Target role cannot be empty.")
    if len(target_role) > 100:
        raise HTTPException(status_code=400, detail="Target role must be 100 characters or less.")
        
    # Block vague goals (e.g., generic keywords or greetings)
    vague_words = {"hi", "hello", "hey", "test", "demo", "xyz", "abc", "dummy", "nothing", "please", "help"}
    if target_role.lower() in vague_words or len(target_role) < 3:
        raise HTTPException(status_code=400, detail="Please specify a valid career path or skill gap.")
    
    from backend.app.security.sanitizer import sanitizer
    if sanitizer.detect_prompt_injection(target_role):
        raise HTTPException(status_code=400, detail="Potential prompt injection detected in target role.")
        
    cleaned_role = sanitizer.sanitize_string(target_role)
    
    # We will look for an uploaded resume in a temporary location or use a default
    # For onboarding, we can optionally parse dynamic resumes if submitted.
    # For this endpoint, we'll run the multi-agent pipeline:
    try:
        result = orchestrator.run_onboarding_pipeline(
            user_id=user_id,
            resume_path=None, # Passed if uploaded
            target_role=cleaned_role,
            timeline_months=req.timeline_months,
            allowed_slots=req.allowed_slots,
            client_id=req.client_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# User-in-the-Loop Approvals Endpoints
@app.get("/api/v1/approvals")
def get_approvals(current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, agent, action, payload, status, created_at FROM approvals WHERE user_id = ? AND status = 'pending'", (user_id,))
    rows = cur.fetchall()
    conn.close()
    
    approvals = []
    for r in rows:
        approvals.append({
            "id": r[0],
            "agent": r[1],
            "action": r[2],
            "payload": json.loads(r[3]),
            "status": r[4],
            "created_at": r[5]
        })
    return {"approvals": approvals}

@app.post("/api/v1/approvals/{approval_id}/approve")
def approve_request(
    approval_id: str,
    client_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["sub"]
    try:
        result = orchestrator.complete_onboarding_pipeline(
            user_id=user_id,
            approval_id=approval_id,
            client_id=client_id
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/approvals/{approval_id}/reject")
def reject_request(
    approval_id: str,
    client_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["sub"]
    try:
        result = orchestrator.reject_onboarding_pipeline(
            user_id=user_id,
            approval_id=approval_id,
            client_id=client_id
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Study Coaching: Fetch Roadmap & Tasks Data

@app.get("/api/v1/roadmap/active")
def get_active_roadmap(current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("SELECT id, target_role, duration_months FROM roadmaps WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (user_id,))
    roadmap_row = cur.fetchone()
    if not roadmap_row:
        conn.close()
        return {"roadmap": None}
        
    roadmap_id = roadmap_row["id"]
    
    # Fetch milestones
    cur.execute("SELECT id, title, description, sequence_order, status FROM milestones WHERE roadmap_id = ? ORDER BY sequence_order", (roadmap_id,))
    milestone_rows = cur.fetchall()
    
    milestones = []
    for m in milestone_rows:
        cur.execute("SELECT id, title, priority, estimated_hours, status, scheduled_start, scheduled_end FROM tasks WHERE milestone_id = ?", (m["id"],))
        task_rows = cur.fetchall()
        tasks = [dict(t) for t in task_rows]
        
        m_dict = dict(m)
        m_dict["tasks"] = tasks
        milestones.append(m_dict)
        
    conn.close()
    return {
        "roadmap": {
            "id": roadmap_id,
            "target_role": roadmap_row["target_role"],
            "duration_months": roadmap_row["duration_months"],
            "milestones": milestones
        }
    }

# Quizzes Endpoint
@app.get("/api/v1/study/quiz")
def get_quiz(subject: str, current_user: dict = Depends(get_current_user)):
    try:
        from agents.study_coach import StudyCoachAgent
        coach = StudyCoachAgent()
        quiz = coach.generate_quiz(subject)
        return {"subject": subject, "questions": quiz}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/study/quiz/submit")
def submit_quiz(req: QuizSubmitRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    session_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO quiz_sessions (id, user_id, subject, score, total_questions) VALUES (?, ?, ?, ?, ?)",
        (session_id, user_id, req.subject, req.score, req.total_questions)
    )
    conn.commit()
    conn.close()
    
    return {"status": "success", "session_id": session_id, "score": req.score}

class TaskStatusUpdate(BaseModel):
    status: str

@app.post("/api/v1/tasks/{task_id}/status")
def update_task_status(task_id: str, req: TaskStatusUpdate, current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Verify task ownership through milestone and roadmap
    cur.execute(
        "SELECT tasks.id FROM tasks "
        "JOIN milestones ON tasks.milestone_id = milestones.id "
        "JOIN roadmaps ON milestones.roadmap_id = roadmaps.id "
        "WHERE tasks.id = ? AND roadmaps.user_id = ?",
        (task_id, user_id)
    )
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found or unauthorized.")
        
    cur.execute("UPDATE tasks SET status = ? WHERE id = ?", (req.status, task_id))
    conn.commit()
    conn.close()
    return {"status": "success", "task_id": task_id, "new_status": req.status}

# Security Audit Logs Viewer (For demonstration & validation purposes)
@app.get("/api/v1/audit/logs")
def get_audit_logs(current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("SELECT id, user_id, correlation_id, action, target_agent, timestamp, details FROM audit_logs ORDER BY timestamp DESC LIMIT 50")
    rows = cur.fetchall()
    conn.close()
    
    logs = []
    for r in rows:
        r_dict = dict(r)
        # Parse details JSON string
        try:
            r_dict["details"] = json.loads(r_dict["details"])
        except Exception:
            pass
        logs.append(r_dict)
        
    return logs

# Serve static frontend dashboard from the "/static" folder and root
os.makedirs("frontend/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

@app.get("/")
def read_root():
    # Return index.html from static files if it exists, or simple JSON redirect description
    index_path = "frontend/static/index.html"
    if os.path.exists(index_path):
        from fastapi.responses import FileResponse
        return FileResponse(index_path)
    return {
        "msg": "Welcome to CareerForge AI API.",
        "frontend": "Please build the frontend in frontend/static/index.html to display dashboard UI."
    }

if __name__ == "__main__":
    import uvicorn
    # In development, run uvicorn on port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
