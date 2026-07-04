import os
import sys
import uuid
import json
import sqlite3
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

# Load configurations
from config import GEMINI_MODEL, DATABASE_URL

# Import security modules
from backend.app.security.pii_scrubber import pii_scrubber
from backend.app.security.sanitizer import sanitizer

# Import base logging
from agents.base_agent import broadcast_log

# Import MCP tools and sub-agents
from mcp_server.main import resume_parser_tool
from agents.planner import PlannerAgent
from agents.task_optimizer import TaskOptimizationAgent
from agents.scheduler import SchedulerAgent
from agents.study_coach import StudyCoachAgent


class AgentState:
    """
    Represents the shared memory state of the multi-agent graph workflow.
    """
    def __init__(
        self,
        user_id: str,
        correlation_id: str,
        target_role: str,
        timeline_months: int,
        allowed_slots: List[dict],
        resume_path: Optional[str] = None,
        client_id: Optional[str] = None
    ):
        self.user_id = user_id
        self.correlation_id = correlation_id
        self.target_role = target_role
        self.timeline_months = timeline_months
        self.allowed_slots = allowed_slots
        self.resume_path = resume_path
        self.client_id = client_id
        
        # Extracted parameters
        self.current_skills: List[str] = []
        self.scrubbed_role: str = target_role
        self.role_mapping: Dict[str, str] = {}
        
        # Outputs
        self.roadmap: Dict[str, Any] = {}
        self.all_scheduled_tasks: List[dict] = []
        self.approval_id: Optional[str] = None
        self.pipeline_result: Dict[str, Any] = {}
        
        # State execution flags
        self.next_node: Optional[str] = None
        self.is_security_compromised: bool = False
        self.security_reason: Optional[str] = None
        self.severity: str = "INFO"


class WorkflowGraph:
    """
    Graph engine designed to manage workflow execution sequentially
    with distinct nodes and unconditional/conditional edges.
    """
    def __init__(self):
        self.nodes = {}
        self.edges = []  # List of tuples (source, target)
        self.conditional_edges = {}  # Map of source -> routing function

    def add_node(self, name: str, func):
        self.nodes[name] = func

    def add_edge(self, source: str, target: str):
        """
        Adds a single directed edge. Ensures strictly no duplicate edges between source and target.
        """
        edge = (source, target)
        if edge not in self.edges:
            self.edges.append(edge)

    def set_conditional_routing(self, source: str, routing_func):
        self.conditional_edges[source] = routing_func

    def execute(self, state: AgentState) -> AgentState:
        # Start node is always the security_checkpoint
        current_node = "security_checkpoint"
        
        while current_node and current_node in self.nodes:
            print(f"[WorkflowGraph] Executing node: {current_node}")
            
            # Execute node logic
            node_func = self.nodes[current_node]
            node_func(state)
            
            # Decide next node
            if current_node in self.conditional_edges:
                routing_func = self.conditional_edges[current_node]
                next_node = routing_func(state)
            else:
                # Find the single unconditional edge target
                targets = [target for source, target in self.edges if source == current_node]
                next_node = targets[0] if targets else None
                
            current_node = next_node
            
        return state


# Initialize Sub-agents
planner_agent = PlannerAgent()
task_optimization_agent = TaskOptimizationAgent()
scheduler_agent = SchedulerAgent()
study_coach_agent = StudyCoachAgent()


def security_checkpoint(state: AgentState):
    """
    Dedicated security checkpoint node. Performs:
    1. Input sanitization.
    2. PII Scrubbing (Email, Phone, ZIP regex check).
    3. Prompt Injection Detection (Keyword matching).
    4. Custom Validation Rules (Rate Limiting check and Length Limit validation).
    5. Structured Audit Logging with Severity Levels (INFO, WARNING, CRITICAL).
    """
    broadcast_log(state.client_id, "SecurityCheckpoint", "security_eval", "running", "Evaluating safety constraints at Security Checkpoint...")
    
    # Init log details
    log_details = {
        "timestamp": datetime.now().isoformat(),
        "input_role_length": len(state.target_role),
        "user_id": state.user_id,
        "evaluation_rule": "input_validation_check"
    }

    # 1. Custom Domain-Specific Rule: Input length filter
    if len(state.target_role) > 100:
        state.is_security_compromised = True
        state.security_reason = "Input length exceeds 100 characters limit."
        state.severity = "WARNING"
        log_details["reason"] = state.security_reason
        write_structured_audit_log(state, "input_length_violation", "SecurityCheckpoint", state.severity, log_details)
        return

    # 2. Custom Domain-Specific Rule: Rate Limit Check (Query DB)
    try:
        conn = sqlite3.connect("careerforge.db")
        cur = conn.cursor()
        one_minute_ago = (datetime.now() - timedelta(minutes=1)).isoformat()
        cur.execute(
            "SELECT COUNT(*) FROM audit_logs WHERE user_id = ? AND timestamp > ? AND action = 'onboarding_started'",
            (state.user_id, one_minute_ago)
        )
        request_count = cur.fetchone()[0]
        conn.close()
        
        if request_count > 5:
            state.is_security_compromised = True
            state.security_reason = "Rate limit exceeded (Max 5 requests/min)."
            state.severity = "WARNING"
            log_details["reason"] = state.security_reason
            write_structured_audit_log(state, "rate_limit_exceeded", "SecurityCheckpoint", state.severity, log_details)
            return
    except Exception as e:
        # Fallback if DB not bootstrapped yet
        print(f"[SecurityCheckpoint] Rate limiter check error: {e}")

    # 3. Prompt Injection Detection (Keyword-matching)
    if sanitizer.detect_prompt_injection(state.target_role):
        state.is_security_compromised = True
        state.security_reason = "Potential prompt injection attempt detected."
        state.severity = "CRITICAL"
        log_details["reason"] = state.security_reason
        log_details["raw_payload"] = state.target_role
        write_structured_audit_log(state, "prompt_injection_detected", "SecurityCheckpoint", state.severity, log_details)
        broadcast_log(state.client_id, "SecurityCheckpoint", "input_validation", "failed", "Security violation: Prompt injection attempt blocked!")
        return

    # 4. PII Scrubbing (Regex search email, phone, zip)
    # The pii_scrubber uses standard Email, Phone, and Zip regexes to scrub PII.
    cleaned_role = sanitizer.sanitize_string(state.target_role)
    scrubbed, mapping = pii_scrubber.scrub(cleaned_role)
    state.scrubbed_role = scrubbed
    state.role_mapping = mapping
    
    if mapping:
        log_details["pii_detected_count"] = len(mapping)
        log_details["pii_keys"] = list(mapping.keys())
        state.severity = "WARNING"
        write_structured_audit_log(state, "pii_masked", "SecurityCheckpoint", "WARNING", log_details)
    else:
        state.severity = "INFO"
        write_structured_audit_log(state, "input_validation_passed", "SecurityCheckpoint", "INFO", log_details)


def write_structured_audit_log(state: AgentState, action: str, agent: str, severity: str, details: dict):
    """
    Writes a structured log payload to the audit logs table, explicitly configuring the severity.
    """
    conn = sqlite3.connect("careerforge.db")
    cur = conn.cursor()
    log_id = str(uuid.uuid4())
    
    # Store severity explicitly inside the details JSON payload
    log_payload = {
        "severity": severity,
        "action": action,
        "agent": agent,
        "details": details
    }
    
    cur.execute(
        "INSERT INTO audit_logs (id, user_id, correlation_id, action, target_agent, timestamp, details) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (log_id, state.user_id, state.correlation_id, action, agent, datetime.now().isoformat(), json.dumps(log_payload))
    )
    conn.commit()
    conn.close()


def security_event_node(state: AgentState):
    """
    Node that handles security violations by raising ValueErrors or updating status.
    """
    print(f"[SECURITY_EVENT Node] Handling security compromise: {state.security_reason} (Severity: {state.severity})")
    raise ValueError(f"Security Policy Violation: {state.security_reason}")


def orchestrator_node(state: AgentState):
    """
    Master Orchestration Node coordinating pipeline parameters.
    """
    broadcast_log(state.client_id, "MasterOrchestrator", "onboarding_started", "running", "Orchestrator node starting sub-agent pipeline execution...")
    
    # Parse Resume if provided
    current_skills = []
    if state.resume_path and os.path.exists(state.resume_path):
        broadcast_log(state.client_id, "MasterOrchestrator", "parse_resume", "running", f"Parsing resume at {os.path.basename(state.resume_path)}...")
        resume_data_str = resume_parser_tool(state.resume_path)
        resume_data = json.loads(resume_data_str)
        if "error" not in resume_data:
            current_skills = resume_data.get("parsed_skills", [])
            broadcast_log(state.client_id, "MasterOrchestrator", "parse_resume", "success", f"Extracted skills from resume: {', '.join(current_skills)}")
        else:
            broadcast_log(state.client_id, "MasterOrchestrator", "parse_resume", "warning", f"Resume parse error: {resume_data['error']}")
            
    if not current_skills:
        current_skills = ["Python", "SQL"]  # Fallback defaults
        
    state.current_skills = current_skills


def planner_node(state: AgentState):
    """
    Sub-agent Node: Planner Agent. Generates roadmap milestones.
    """
    broadcast_log(state.client_id, "PlannerAgent", "generate_roadmap", "running", f"Planner Agent generating roadmap for target path: {state.scrubbed_role}...")
    
    raw_roadmap = planner_agent.generate_roadmap(state.scrubbed_role, state.timeline_months, state.current_skills, client_id=state.client_id)
    
    # Rehydrate output
    roadmap_str = json.dumps(raw_roadmap)
    rehydrated_str = pii_scrubber.rehydrate(roadmap_str, state.role_mapping)
    state.roadmap = json.loads(rehydrated_str)
    
    broadcast_log(state.client_id, "PlannerAgent", "generate_roadmap", "success", f"Roadmap generated successfully: {len(state.roadmap.get('milestones', []))} milestones.")


def task_optimizer_node(state: AgentState):
    """
    Sub-agent Node: Task Optimization Agent. Decomposes milestones into actionable tasks.
    """
    # Write Roadmap to Database first
    conn = sqlite3.connect("careerforge.db")
    cur = conn.cursor()
    
    roadmap_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO roadmaps (id, user_id, target_role, duration_months, created_at) VALUES (?, ?, ?, ?, ?)",
        (roadmap_id, state.user_id, state.roadmap["target_role"], state.roadmap["duration_months"], datetime.now().isoformat())
    )
    
    all_scheduled_tasks = []
    
    for m_idx, milestone in enumerate(state.roadmap.get("milestones", [])):
        m_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO milestones (id, roadmap_id, title, description, sequence_order, status) VALUES (?, ?, ?, ?, ?, ?)",
            (m_id, roadmap_id, milestone["title"], milestone["description"], milestone.get("sequence_order", m_idx+1), "pending")
        )
        
        # Run Task Optimization
        broadcast_log(state.client_id, "TaskOptimizationAgent", "optimize_tasks", "running", f"Task Optimizer Agent breaking down: '{milestone['title']}'...")
        tasks_list = task_optimization_agent.optimize_tasks(milestone["title"], milestone["description"], client_id=state.client_id)
        
        for t_idx, task in enumerate(tasks_list):
            t_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO tasks (id, milestone_id, title, priority, estimated_hours, status) VALUES (?, ?, ?, ?, ?, ?)",
                (t_id, m_id, task["title"], task.get("priority", "medium"), task.get("estimated_hours", 2.0), "pending")
            )
            
            all_scheduled_tasks.append({
                "id": t_id,
                "title": task["title"],
                "estimated_hours": task.get("estimated_hours", 2.0)
            })

    conn.commit()
    conn.close()
    
    state.roadmap_id = roadmap_id
    state.all_scheduled_tasks = all_scheduled_tasks


def scheduler_node(state: AgentState):
    """
    Sub-agent Node: Scheduler Agent. Proposes protected slots.
    """
    broadcast_log(state.client_id, "SchedulerAgent", "propose_schedule", "running", "Scheduler Agent constructing schedule layout for user approval...")
    approval_id = scheduler_agent.propose_schedule(state.user_id, state.all_scheduled_tasks, state.allowed_slots, client_id=state.client_id)
    
    state.approval_id = approval_id
    state.pipeline_result = {
        "status": "pending_approval",
        "approval_id": approval_id,
        "roadmap_id": state.roadmap_id,
        "target_role": state.roadmap["target_role"],
        "skills_detected": state.current_skills,
        "roadmap": state.roadmap
    }


# Construct the Graph Workflow
workflow = WorkflowGraph()

# Add Nodes
workflow.add_node("security_checkpoint", security_checkpoint)
workflow.add_node("SECURITY_EVENT", security_event_node)
workflow.add_node("orchestrator_node", orchestrator_node)
workflow.add_node("planner_node", planner_node)
workflow.add_node("task_optimizer_node", task_optimizer_node)
workflow.add_node("scheduler_node", scheduler_node)

# Add Edges (strictly one edge per source-target transition to prevent duplicate edge errors)
workflow.add_edge("orchestrator_node", "planner_node")
workflow.add_edge("planner_node", "task_optimizer_node")
workflow.add_edge("task_optimizer_node", "scheduler_node")

# Setup Conditional Edge Routing from security_checkpoint
def route_security(state: AgentState) -> str:
    if state.is_security_compromised:
        return "SECURITY_EVENT"
    return "orchestrator_node"

workflow.set_conditional_routing("security_checkpoint", route_security)
# Register the potential targets for the visual graph representation
workflow.add_edge("security_checkpoint", "SECURITY_EVENT")
workflow.add_edge("security_checkpoint", "orchestrator_node")
