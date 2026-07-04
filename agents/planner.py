import json
import uuid
from agents.base_agent import BaseAgent, broadcast_log
from mcp_server.main import skill_database_tool, course_database_tool

class PlannerAgent(BaseAgent):
    def __init__(self):
        system_instruction = (
            "You are the CareerForge AI Planner Agent. Your job is to create a structured, "
            "long-term milestone roadmap for users based on their target career, timeframe, "
            "and existing skills. You recommend courses and skills for each milestone. "
            "You MUST output raw JSON matching this structure:\n"
            "{\n"
            "  \"target_role\": \"title\",\n"
            "  \"duration_months\": 6,\n"
            "  \"milestones\": [\n"
            "    {\n"
            "      \"title\": \"Milestone Title\",\n"
            "      \"description\": \"Description of milestones and target skill gaps addressed\",\n"
            "      \"sequence_order\": 1,\n"
            "      \"recommended_courses\": [\"Course 1\", \"Course 2\"]\n"
            "    }\n"
            "  ]\n"
            "}"
        )
        super().__init__(name="Planner", system_instruction=system_instruction)

    def generate_roadmap(self, target_role: str, duration_months: int, current_skills: list, client_id: str = None) -> dict:
        broadcast_log(client_id, "PlannerAgent", "gap_analysis", "running", "Assessing core skill gaps using Skill DB tool...")
        prompt = (
            f"Generate a {duration_months}-month career roadmap for becoming a {target_role}. "
            f"The user current skills are: {', '.join(current_skills)}. "
            "Integrate details about relevant technical skill gaps."
        )
        
        # In a real environment, we'd query the MCP tool to extract gaps first
        gap_json = skill_database_tool("get_gaps", user_skills=current_skills, target_job=target_role)
        gap_info = json.loads(gap_json)
        
        prompt += f"\nThe gap analysis from Skill DB: {json.dumps(gap_info)}"
        
        broadcast_log(client_id, "PlannerAgent", "llm_roadmap", "running", "Requesting roadmap milestone sequence from Gemini model...")
        response_text = self.run_llm(prompt, response_json=True)

        
        try:
            # Clean up JSON wrappers if the model includes markdown formatting
            cleaned = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except Exception:
            # Fallback mock schema
            return self._mock_roadmap(target_role, duration_months, gap_info)

    def _mock_roadmap(self, target_role: str, duration_months: int, gap_info: dict) -> dict:
        missing_skills = gap_info.get("missing_skills", ["Machine Learning", "PyTorch"])
        
        milestones = []
        # Create 3 milestones
        for i, skill in enumerate(missing_skills[:3]):
            # Try to query courses for this missing skill
            courses_json = course_database_tool(skill, limit=2)
            courses = json.loads(courses_json)
            course_titles = [c["title"] for c in courses] if courses else [f"Introduction to {skill}"]
            
            milestones.append({
                "title": f"Mastery of {skill}",
                "description": f"Learn foundational concepts, complete practical code assessments, and close the gap on {skill}.",
                "sequence_order": i + 1,
                "recommended_courses": course_titles
            })
            
        if not milestones:
            milestones.append({
                "title": f"Core Competency Training",
                "description": f"Develop foundational tech stack for a {target_role}.",
                "sequence_order": 1,
                "recommended_courses": [f"Complete {target_role} bootcamp"]
            })

        return {
            "target_role": target_role,
            "duration_months": duration_months,
            "milestones": milestones
        }
