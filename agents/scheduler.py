import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from agents.base_agent import BaseAgent, broadcast_log
from mcp_server.main import calendar_tool


class SchedulerAgent(BaseAgent):
    def __init__(self):
        system_instruction = (
            "You are the CareerForge AI Life Scheduler Agent. Your job is to schedule study hours, "
            "review sessions, and tasks on the user's calendar based on their weekly availability. "
            "You interface with the calendar_tool to book slots and resolve timing conflicts. "
            "You MUST return your schedule actions as structured JSON arrays."
        )
        super().__init__(name="Scheduler", system_instruction=system_instruction)

    def schedule_tasks(self, tasks: list, allowed_slots: list, client_id: str = None) -> list:
        """
        Schedules a list of tasks into the allowed weekly slots.
        allowed_slots format: [{"day": "Monday", "start": "18:00", "end": "20:00"}]
        """
        # If tasks already have valid start/end times, just write them to the calendar and return them!
        pre_scheduled = True
        for task in tasks:
            if not task.get("start") or not task.get("end"):
                pre_scheduled = False
                break
        
        if pre_scheduled and len(tasks) > 0:
            print("[SchedulerAgent] Tasks are pre-scheduled. Syncing to calendar...")
            scheduled_actions = []
            for task in tasks:
                task_id = task.get("id") or task.get("task_id")
                title = task.get("title")
                start_iso = task.get("start")
                end_iso = task.get("end")
                calendar_tool(
                    action="write",
                    task_id=task_id,
                    start_time=start_iso,
                    end_time=end_iso,
                    title=title
                )
                scheduled_actions.append({
                    "task_id": task_id,
                    "title": title,
                    "start": start_iso,
                    "end": end_iso
                })
            return scheduled_actions

        broadcast_log(client_id, "SchedulerAgent", "read_calendar", "running", "Reading active commitments via Calendar tool...")
        # Read current schedules
        current_schedule_str = calendar_tool("read")
        current_schedules = json.loads(current_schedule_str)
        
        broadcast_log(client_id, "SchedulerAgent", "write_calendar", "running", f"Writing {len(tasks)} target task blocks to calendar workspace...")

        # Try AI-based Scheduling first
        try:
            broadcast_log(client_id, "SchedulerAgent", "ai_schedule", "running", "Invoking Gemini model to map calendar blocks...")
            prompt = (
                "You are the Life Scheduler Agent. Your job is to schedule the following list of tasks:\n"
                f"{json.dumps(tasks, indent=2)}\n\n"
                "into these allowed weekly availability blocks:\n"
                f"{json.dumps(allowed_slots, indent=2)}\n\n"
                "avoiding conflicts with these existing scheduled events:\n"
                f"{json.dumps(current_schedules, indent=2)}\n\n"
                "Rules:\n"
                "1. Output a raw JSON array matching this structure:\n"
                "[\n"
                "  {\n"
                "    \"task_id\": \"task_id_here\",\n"
                "    \"title\": \"task_title_here\",\n"
                "    \"start\": \"YYYY-MM-DDTHH:MM:SS\",\n"
                "    \"end\": \"YYYY-MM-DDTHH:MM:SS\"\n"
                "  }\n"
                "]\n"
                f"2. Every start time must be after the current time ({datetime.now().isoformat()}).\n"
                "3. The difference between end and start times must match the task's duration requirements.\n"
                "4. Distribute the tasks appropriately over the coming days, checking that start and end dates fall on the correct days of the week matching the user's availability."
            )
            response_text = self.run_llm(prompt, response_json=True)
            cleaned = response_text.replace("```json", "").replace("```", "").strip()
            ai_schedules = json.loads(cleaned)
            
            if isinstance(ai_schedules, list) and len(ai_schedules) > 0:
                scheduled_actions = []
                for sched in ai_schedules:
                    task_id = sched.get("task_id")
                    title = sched.get("title")
                    start_iso = sched.get("start")
                    end_iso = sched.get("end")
                    
                    if not start_iso or "undefined" in str(start_iso).lower() or "none" in str(start_iso).lower():
                        raise ValueError("Gemini returned undefined schedule timestamps.")
                    
                    calendar_tool(
                        action="write",
                        task_id=task_id,
                        start_time=start_iso,
                        end_time=end_iso,
                        title=title
                    )
                    scheduled_actions.append({
                        "task_id": task_id,
                        "title": title,
                        "start": start_iso,
                        "end": end_iso
                    })
                broadcast_log(client_id, "SchedulerAgent", "ai_schedule", "success", "Gemini successfully planned and committed task blocks.")
                return scheduled_actions
        except Exception as e:
            print(f"[SchedulerAgent] AI Scheduling failed: {e}. Executing rule-based fallback.")
            broadcast_log(client_id, "SchedulerAgent", "ai_schedule", "warning", "AI schedule mapping failed. Falling back to local rules...")

        # Rule-based fallback logic
        scheduled_actions = []
        base_date = datetime.now() + timedelta(days=1) # start tomorrow
        
        days_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }
        
        # Keep track of concrete slots to fit multiple tasks.
        active_allocations = []
        for week_idx in range(8):
            week_start = base_date + timedelta(weeks=week_idx)
            for slot in allowed_slots:
                day_str = slot.get("day", "").lower()
                start_str = slot.get("start", "18:00")
                end_str = slot.get("end", "20:00")
                
                if day_str not in days_map:
                    continue
                
                target_day_val = days_map[day_str]
                days_ahead = target_day_val - week_start.weekday()
                if days_ahead < 0:
                    days_ahead += 7
                
                target_date = week_start + timedelta(days=days_ahead)
                
                try:
                    start_h, start_m = map(int, start_str.split(":"))
                    end_h, end_m = map(int, end_str.split(":"))
                except Exception:
                    start_h, start_m = 18, 0
                    end_h, end_m = 20, 0
                
                start_dt = target_date.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
                end_dt = target_date.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
                capacity_hours = (end_dt - start_dt).total_seconds() / 3600.0
                
                active_allocations.append({
                    "date": target_date,
                    "start_dt": start_dt,
                    "end_dt": end_dt,
                    "current_available_start": start_dt,
                    "remaining_hours": capacity_hours
                })
        
        active_allocations.sort(key=lambda x: x["start_dt"])
        
        for task in tasks:
            task_id = task.get("id") or task.get("task_id")
            title = task.get("title")
            est_hours = task.get("estimated_hours", 2.0)
            
            scheduled = False
            for alloc in active_allocations:
                if alloc["remaining_hours"] >= est_hours:
                    task_start_dt = alloc["current_available_start"]
                    task_end_dt = task_start_dt + timedelta(hours=est_hours)
                    
                    start_iso = task_start_dt.isoformat()
                    end_iso = task_end_dt.isoformat()
                    
                    calendar_tool(
                        action="write",
                        task_id=task_id,
                        start_time=start_iso,
                        end_time=end_iso,
                        title=title
                    )
                    
                    scheduled_actions.append({
                        "task_id": task_id,
                        "title": title,
                        "start": start_iso,
                        "end": end_iso
                    })
                    
                    alloc["current_available_start"] = task_end_dt
                    alloc["remaining_hours"] -= est_hours
                    scheduled = True
                    break
            
            if not scheduled:
                fallback_start = base_date.replace(hour=19, minute=0, second=0, microsecond=0)
                fallback_end = fallback_start + timedelta(hours=est_hours)
                start_iso = fallback_start.isoformat()
                end_iso = fallback_end.isoformat()
                
                calendar_tool(
                    action="write",
                    task_id=task_id,
                    start_time=start_iso,
                    end_time=end_iso,
                    title=title
                )
                scheduled_actions.append({
                    "task_id": task_id,
                    "title": title,
                    "start": start_iso,
                    "end": end_iso
                })
                base_date += timedelta(days=1)

        broadcast_log(client_id, "SchedulerAgent", "ai_schedule", "success", "Calendar blocks mapped and synced successfully via local rules.")
        return scheduled_actions

    def propose_schedule(self, user_id: str, tasks: list, allowed_slots: list, client_id: str = None) -> str:
        approval_id = str(uuid.uuid4())
        conn = sqlite3.connect("careerforge.db", timeout=30.0)
        cur = conn.cursor()
        
        # Calculate total task hours
        total_task_hours = sum(task.get("estimated_hours", 2.0) for task in tasks)
        
        # Calculate weekly capacity
        weekly_capacity = 0
        expanded_slots = []
        for slot in allowed_slots:
            start_str = slot.get("start", "18:00")
            end_str = slot.get("end", "20:00")
            try:
                start_h, start_m = map(int, start_str.split(":"))
                end_h, end_m = map(int, end_str.split(":"))
                dur = (end_h * 60 + end_m) - (start_h * 60 + start_m)
                weekly_capacity += dur / 60.0
            except Exception:
                weekly_capacity += 2.0
            expanded_slots.append(slot.copy())

        # Automatically expand Mon from 2h to 3h, and Sat from 5h to 7h if overload detected
        if total_task_hours > weekly_capacity:
            print(f"[SchedulerAgent] High task load ({total_task_hours}h) vs capacity ({weekly_capacity}h). Expanding slots.")
            for slot in expanded_slots:
                if slot.get("day").lower() == "monday":
                    slot["start"] = "18:00"
                    slot["end"] = "21:00"
                elif slot.get("day").lower() == "saturday":
                    slot["start"] = "09:00"
                    slot["end"] = "16:00"

        # Pre-populate exact start/end dates
        scheduled_tasks = self.schedule_tasks(tasks, expanded_slots, client_id=client_id)
        
        payload_str = json.dumps({
            "tasks": scheduled_tasks,
            "allowed_slots": expanded_slots
        })
        
        cur.execute(
            "INSERT INTO approvals (id, user_id, agent, action, payload, status) VALUES (?, ?, ?, ?, ?, ?)",
            (approval_id, user_id, "SchedulerAgent", "create_schedule", payload_str, "pending")
        )
        conn.commit()
        conn.close()
        
        # Broadcast the WebSocket approval request
        broadcast_log(
            client_id,
            "SchedulerAgent",
            "approval_requested",
            "pending",
            "Proposed study schedule generated. Awaiting user approval...",
            extra={
                "type": "approval_request",
                "approval_id": approval_id,
                "data": {
                    "tasks": scheduled_tasks,
                    "allowed_slots": expanded_slots
                }
            }
        )
        return approval_id

    def commit_schedule(self, tasks: list, allowed_slots: list, client_id: str = None) -> list:
        # Commit the schedule using standard schedule_tasks method
        return self.schedule_tasks(tasks, allowed_slots, client_id=client_id)

