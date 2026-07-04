import os
import sqlite3
import uuid
import json
from datetime import datetime
from typing import Optional, List
from backend.app.security.pii_scrubber import pii_scrubber
from backend.app.security.sanitizer import sanitizer

from agents.planner import PlannerAgent
from agents.task_optimizer import TaskOptimizationAgent
from agents.study_coach import StudyCoachAgent
from agents.scheduler import SchedulerAgent
from mcp_server.main import resume_parser_tool
from agents.base_agent import broadcast_log

DB_PATH = "careerforge.db"


class MasterOrchestrator:
    def __init__(self):
        self.planner = PlannerAgent()
        self.task_optimizer = TaskOptimizationAgent()
        self.study_coach = StudyCoachAgent()
        self.scheduler = SchedulerAgent()

    def get_db_conn(self):
        return sqlite3.connect(DB_PATH)

    def write_audit_log(self, user_id: str, correlation_id: str, action: str, agent: str, details: dict):
        conn = self.get_db_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO audit_logs (id, user_id, correlation_id, action, target_agent, timestamp, details) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, correlation_id, action, agent, datetime.now().isoformat(), json.dumps(details))
        )
        conn.commit()
        conn.close()

    def run_onboarding_pipeline(self, user_id: str, resume_path: Optional[str], target_role: str, timeline_months: int, allowed_slots: list, client_id: Optional[str] = None) -> dict:
        """
        Executes the complete multi-agent onboarding flow via the WorkflowGraph:
        1. security_checkpoint node (sanitizes input, scrubs PII, detects injections, rate-limits, logs structured audit).
        2. orchestrator_node (determines skills and handles parsing).
        3. planner_node (Planner Agent milestone generation).
        4. task_optimizer_node (Task Optimizer Agent task generation).
        5. scheduler_node (Scheduler Agent proposed slots).
        """
        import sys
        import os
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        from agent import workflow, AgentState
        
        correlation_id = str(uuid.uuid4())
        print(f"[Orchestrator] Executing graph-based onboarding pipeline. Correlation ID: {correlation_id}")
        
        state = AgentState(
            user_id=user_id,
            correlation_id=correlation_id,
            target_role=target_role,
            timeline_months=timeline_months,
            allowed_slots=allowed_slots,
            resume_path=resume_path,
            client_id=client_id
        )
        
        # Execute the workflow starting at security_checkpoint node
        workflow.execute(state)
        
        return state.pipeline_result

    def complete_onboarding_pipeline(self, user_id: str, approval_id: str, client_id: Optional[str] = None) -> dict:
        correlation_id = str(uuid.uuid4())
        
        # 1. Fetch approval from database
        conn = self.get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT payload, status FROM approvals WHERE id = ?", (approval_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            raise ValueError("Approval request not found.")
        
        payload_str, status = row
        if status != "pending":
            conn.close()
            raise ValueError(f"Approval request is already in status: {status}")
            
        payload = json.loads(payload_str)
        tasks = payload.get("tasks", [])
        allowed_slots = payload.get("allowed_slots", [])
        
        # 2. Mark approval as approved
        cur.execute("UPDATE approvals SET status = 'approved' WHERE id = ?", (approval_id,))
        conn.commit()
        conn.close()
        
        broadcast_log(client_id, "MasterOrchestrator", "approval_approved", "success", "Proposed schedule approved by user. Processing final layout...")
        
        self.write_audit_log(
            user_id=user_id,
            correlation_id=correlation_id,
            action="approval_approved",
            agent="MasterOrchestrator",
            details={"approval_id": approval_id}
        )
        
        # 3. Schedule the tasks on calendar (Scheduler Agent commit)
        broadcast_log(client_id, "SchedulerAgent", "schedule_tasks", "running", "Scheduler Agent booking protected study times on calendar...")
        schedules = self.scheduler.commit_schedule(tasks, allowed_slots, client_id=client_id)
        
        self.write_audit_log(
            user_id=user_id,
            correlation_id=correlation_id,
            action="tasks_scheduled",
            agent="Scheduler",
            details={"events_created": len(schedules)}
        )
        
        # 4. Update scheduled times in tasks database
        conn = self.get_db_conn()
        cur = conn.cursor()
        for sched in schedules:
            cur.execute(
                "UPDATE tasks SET scheduled_start = ?, scheduled_end = ?, status = 'scheduled' WHERE id = ?",
                (sched["start"], sched["end"], sched["task_id"])
            )
        
        # Get active roadmap and first milestone subject to query Study Coach
        cur.execute("SELECT id FROM roadmaps WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (user_id,))
        roadmap_row = cur.fetchone()
        roadmap_id = roadmap_row[0] if roadmap_row else None
        
        first_title = "Core Skills"
        if roadmap_id:
            cur.execute("SELECT title, id FROM milestones WHERE roadmap_id = ? ORDER BY sequence_order ASC LIMIT 1", (roadmap_id,))
            milestone_row = cur.fetchone()
            if milestone_row:
                first_title = milestone_row[0]
                first_milestone_id = milestone_row[1]
                # Mark first milestone status as active
                cur.execute("UPDATE milestones SET status = 'active' WHERE id = ?", (first_milestone_id,))
                
        conn.commit()
        conn.close()
        
        # 5. Generate first milestone Study notes and Quiz (Study Coach Agent)
        broadcast_log(client_id, "StudyCoachAgent", "initialize_study", "running", f"Study Coach Agent compiling training guides for: '{first_title}'...")
        notes = self.study_coach.generate_study_notes(first_title, client_id=client_id)
        quiz = self.study_coach.generate_quiz(first_title, client_id=client_id)
        
        self.write_audit_log(
            user_id=user_id,
            correlation_id=correlation_id,
            action="study_coach_initialized",
            agent="StudyCoach",
            details={"first_topic": first_title}
        )
        
        self.write_audit_log(
            user_id=user_id,
            correlation_id=correlation_id,
            action="onboarding_completed",
            agent="MasterOrchestrator",
            details={"roadmap_id": roadmap_id}
        )
        
        broadcast_log(client_id, "MasterOrchestrator", "onboarding_completed", "success", "Onboarding pipeline completed successfully. Welcome to your workspace!")
        
        return {
            "status": "success",
            "roadmap_id": roadmap_id,
            "scheduled_sessions": schedules,
            "diagnostic_quiz": quiz,
            "first_milestone_notes": notes
        }

    def reject_onboarding_pipeline(self, user_id: str, approval_id: str, client_id: Optional[str] = None) -> dict:
        correlation_id = str(uuid.uuid4())
        
        conn = self.get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT status FROM approvals WHERE id = ?", (approval_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            raise ValueError("Approval request not found.")
            
        status = row[0]
        if status != "pending":
            conn.close()
            raise ValueError(f"Approval request is already in status: {status}")
            
        cur.execute("UPDATE approvals SET status = 'rejected' WHERE id = ?", (approval_id,))
        
        # Delete the pending roadmap to allow clean re-planning
        cur.execute("SELECT id FROM roadmaps WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (user_id,))
        roadmap_row = cur.fetchone()
        if roadmap_row:
            roadmap_id = roadmap_row[0]
            cur.execute("DELETE FROM roadmaps WHERE id = ?", (roadmap_id,))
            
        conn.commit()
        conn.close()
        
        broadcast_log(client_id, "MasterOrchestrator", "approval_rejected", "failed", "Proposed study schedule was rejected. Re-planning required.")
        
        self.write_audit_log(
            user_id=user_id,
            correlation_id=correlation_id,
            action="approval_rejected",
            agent="MasterOrchestrator",
            details={"approval_id": approval_id}
        )
        
        return {
            "status": "rejected",
            "message": "Onboarding pipeline proposal rejected. You can now re-configure your goals."
        }
