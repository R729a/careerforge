import os
import sqlite3
import json
import uuid
import re
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("CareerForge-Server")

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./careerforge.db").replace("sqlite:///", "")

def get_db_conn():
    return sqlite3.connect(DB_PATH, timeout=30.0)


# Helper function to query database
def query_db(query: str, args=(), one=False):
    conn = get_db_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv

# Helper to execute modifications
def execute_db(query: str, args=()):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(query, args)
    conn.commit()
    conn.close()

# Tool 1: Course Database Tool
@mcp.tool(name="course_database_tool")
def course_database_tool(query: str, limit: int = 5) -> str:
    """
    Search courses from the course catalog based on skills taught or keywords.
    :param query: Search string (e.g. 'Python', 'ML')
    :param limit: Maximum number of courses to return.
    """
    rows = query_db(
        "SELECT title, description, provider, url, skills_taught FROM courses WHERE title LIKE ? OR description LIKE ? OR skills_taught LIKE ?",
        (f"%{query}%", f"%{query}%", f"%{query}%")
    )
    
    results = []
    for row in rows[:limit]:
        results.append({
            "title": row["title"],
            "description": row["description"],
            "provider": row["provider"],
            "url": row["url"],
            "skills_taught": row["skills_taught"].split(",")
        })
        
    return json.dumps(results, indent=2)

# Tool 2: Job Market Tool
@mcp.tool(name="job_market_tool")
def job_market_tool(job_title: str) -> str:
    """
    Lookup job market intelligence: required skills, salary averages, and current hiring trends.
    :param job_title: Target career title (e.g., 'Machine Learning Engineer', 'Data Engineer')
    """
    market_data = {
        "machine learning engineer": {
            "average_salary": "$145,000",
            "demand_level": "High",
            "growth_rate": "+24% YoY",
            "top_skills": ["Python", "PyTorch", "Machine Learning", "TensorFlow", "SQL", "Docker"],
            "common_requirements": "Experience with deep learning frameworks, model serving, and ETL pipelines."
        },
        "data scientist": {
            "average_salary": "$135,000",
            "demand_level": "High",
            "growth_rate": "+16% YoY",
            "top_skills": ["Python", "SQL", "Machine Learning", "Deep Learning"],
            "common_requirements": "Experience with predictive modeling, statistical analysis, and ML algorithms."
        },
        "data analyst": {
            "average_salary": "$85,000",
            "demand_level": "Medium-High",
            "growth_rate": "+10% YoY",
            "top_skills": ["SQL", "Python", "Git & GitHub"],
            "common_requirements": "Experience with relational databases, data visualization, and reporting."
        },
        "data engineer": {
            "average_salary": "$130,000",
            "demand_level": "High",
            "growth_rate": "+18% YoY",
            "top_skills": ["SQL", "Python", "Data Engineering", "Docker", "Git & GitHub"],
            "common_requirements": "Experience building stable data pipelines, workflow orchestration, and warehousing."
        },
        "ai engineer": {
            "average_salary": "$150,000",
            "demand_level": "High",
            "growth_rate": "+38% YoY",
            "top_skills": ["Python", "Machine Learning", "Deep Learning", "PyTorch"],
            "common_requirements": "Experience implementing ML models, deep neural networks, and NLP systems."
        },
        "mlops engineer": {
            "average_salary": "$148,000",
            "demand_level": "High",
            "growth_rate": "+30% YoY",
            "top_skills": ["Python", "Docker", "Machine Learning", "Git & GitHub"],
            "common_requirements": "Experience with CI/CD for machine learning, model registry, and infrastructure automation."
        },
        "business intelligence analyst": {
            "average_salary": "$92,000",
            "demand_level": "Medium",
            "growth_rate": "+7% YoY",
            "top_skills": ["SQL", "Python"],
            "common_requirements": "Experience designing BI dashboards, data warehouse integration, and business reporting."
        },
        "software engineer": {
            "average_salary": "$115,000",
            "demand_level": "Medium-High",
            "growth_rate": "+12% YoY",
            "top_skills": ["Python", "FastAPI", "Docker", "Git & GitHub", "SQL"],
            "common_requirements": "Full-stack development experience, API design, version control, and unit testing."
        },
        "full stack developer": {
            "average_salary": "$112,000",
            "demand_level": "Medium-High",
            "growth_rate": "+14% YoY",
            "top_skills": ["Python", "FastAPI", "SQL", "Git & GitHub"],
            "common_requirements": "Experience building end-to-end web applications, frontend integration, and APIs."
        },
        "frontend developer": {
            "average_salary": "$105,000",
            "demand_level": "Medium",
            "growth_rate": "+11% YoY",
            "top_skills": ["Git & GitHub", "Python"],
            "common_requirements": "Experience building interactive interfaces, responsive design, and state management."
        },
        "backend developer": {
            "average_salary": "$118,000",
            "demand_level": "High",
            "growth_rate": "+13% YoY",
            "top_skills": ["Python", "FastAPI", "SQL", "Git & GitHub", "Docker"],
            "common_requirements": "Experience building scalable REST APIs, relational databases, and server-side caching."
        },
        "devops engineer": {
            "average_salary": "$125,000",
            "demand_level": "High",
            "growth_rate": "+19% YoY",
            "top_skills": ["Docker", "Git & GitHub", "Python"],
            "common_requirements": "Experience managing infrastructure as code, CI/CD automation, and cloud deployments."
        },
        "cloud engineer": {
            "average_salary": "$128,000",
            "demand_level": "High",
            "growth_rate": "+21% YoY",
            "top_skills": ["Docker", "Git & GitHub", "Python"],
            "common_requirements": "Experience building and maintaining secure, fault-tolerant cloud architecture."
        },
        "cybersecurity analyst": {
            "average_salary": "$102,000",
            "demand_level": "High",
            "growth_rate": "+25% YoY",
            "top_skills": ["SQL", "Git & GitHub", "Python"],
            "common_requirements": "Experience with network threat detection, security audits, and access controls."
        },
        "security engineer": {
            "average_salary": "$126,000",
            "demand_level": "High",
            "growth_rate": "+22% YoY",
            "top_skills": ["Docker", "Git & GitHub", "Python"],
            "common_requirements": "Experience designing secure software pipelines, encryption, and threat modeling."
        },
        "soc analyst": {
            "average_salary": "$88,000",
            "demand_level": "Medium-High",
            "growth_rate": "+18% YoY",
            "top_skills": ["SQL", "Git & GitHub"],
            "common_requirements": "Experience monitoring log analytics, incident response, and alert triaging."
        },
        "product manager": {
            "average_salary": "$120,000",
            "demand_level": "Medium-High",
            "growth_rate": "+9% YoY",
            "top_skills": ["Git & GitHub", "SQL"],
            "common_requirements": "Experience defining product roadmaps, requirements gathering, and feature prioritization."
        },
        "business analyst": {
            "average_salary": "$87,000",
            "demand_level": "Medium",
            "growth_rate": "+8% YoY",
            "top_skills": ["SQL", "Python"],
            "common_requirements": "Experience mapping business processes, data-driven analysis, and stakeholder alignment."
        },
        "technical program manager": {
            "average_salary": "$138,000",
            "demand_level": "Medium-High",
            "growth_rate": "+10% YoY",
            "top_skills": ["Git & GitHub", "Python"],
            "common_requirements": "Experience coordinating multi-team technical projects, agile delivery, and risk management."
        },
        "generative ai engineer": {
            "average_salary": "$165,000",
            "demand_level": "High",
            "growth_rate": "+60% YoY",
            "top_skills": ["Python", "Deep Learning", "PyTorch", "Machine Learning", "Git & GitHub"],
            "common_requirements": "Experience fine-tuning LLMs, model distillation, prompt optimization, and vector DBs."
        },
        "ai product engineer": {
            "average_salary": "$142,000",
            "demand_level": "High",
            "growth_rate": "+45% YoY",
            "top_skills": ["Python", "FastAPI", "Machine Learning", "Git & GitHub"],
            "common_requirements": "Experience integrating AI models into customer-facing SaaS applications."
        },
        "prompt engineer": {
            "average_salary": "$95,000",
            "demand_level": "Medium-High",
            "growth_rate": "+35% YoY",
            "top_skills": ["Python", "Git & GitHub"],
            "common_requirements": "Experience with dynamic prompt formatting, context engineering, and model validation."
        },
        "ai research engineer": {
            "average_salary": "$158,000",
            "demand_level": "High",
            "growth_rate": "+40% YoY",
            "top_skills": ["Python", "Deep Learning", "PyTorch", "TensorFlow", "Machine Learning"],
            "common_requirements": "Experience designing novel network architectures, training large models, and publishing."
        }
    }
    
    title_key = job_title.lower().strip()
    if title_key in market_data:
        return json.dumps(market_data[title_key], indent=2)
        
    # Generic response for other titles
    generic_data = {
        "average_salary": "$110,000",
        "demand_level": "Medium",
        "growth_rate": "+8% YoY",
        "top_skills": ["Python", "SQL", "Git & GitHub"],
        "common_requirements": "Strong technical problem-solving skills, basic coding, and database management."
    }
    return json.dumps(generic_data, indent=2)

# Tool 3: Resume Parser Tool
@mcp.tool(name="resume_parser_tool")
def resume_parser_tool(file_path: str) -> str:
    """
    Parses local PDF resumes and extracts structured details including matching database skills.
    :param file_path: Absolute local path to resume PDF.
    """
    if not os.path.exists(file_path):
        return json.dumps({"error": f"Resume file not found at path: {file_path}"})
        
    text = ""
    try:
        from pypdf import PdfReader
        with open(file_path, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                text_content = page.extract_text()
                if text_content:
                    text += text_content + "\n"
    except Exception as e:
        return json.dumps({"error": f"Failed to parse PDF file: {str(e)}"})
        
    # Match skills from the database
    skills_rows = query_db("SELECT name FROM skills")
    all_skills = [row["name"] for row in skills_rows]
    
    detected_skills = []
    text_lower = text.lower()
    for skill in all_skills:
        # Avoid partial matches by checking boundaries
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower):

            detected_skills.append(skill)
            
    # Simple years of experience estimation
    exp_matches = re.findall(r'(\d+)\+?\s*years?', text_lower)
    experience_years = max([float(x) for x in exp_matches]) if exp_matches else 1.0

    return json.dumps({
        "parsed_skills": detected_skills,
        "experience_years": experience_years,
        "raw_text_length": len(text)
    }, indent=2)

# Tool 4: Calendar Tool
@mcp.tool(name="calendar_tool")
def calendar_tool(action: str, task_id: str = None, start_time: str = None, end_time: str = None, title: str = None) -> str:
    """
    Read, write, and delete events. Keeps a local workspace .ics file in sync for convenience.
    :param action: 'read', 'write', or 'delete'
    :param task_id: Target task identifier
    :param start_time: ISO8601 start string (e.g. '2026-07-06T18:00:00')
    :param end_time: ISO8601 end string
    :param title: Summary of calendar block
    """
    if action == "read":
        tasks_with_schedule = query_db("SELECT id, title, scheduled_start, scheduled_end FROM tasks WHERE scheduled_start IS NOT NULL")
        events = []
        for row in tasks_with_schedule:
            events.append({
                "task_id": row["id"],
                "title": row["title"],
                "start": row["scheduled_start"],
                "end": row["scheduled_end"]
            })
        return json.dumps(events, indent=2)
        
    elif action == "write":
        if not task_id or not start_time or not end_time:
            return json.dumps({"error": "task_id, start_time, and end_time are required for writing to calendar."})
            
        # Verify task exists
        task = query_db("SELECT id FROM tasks WHERE id = ?", (task_id,), one=True)
        if not task:
            # Create a mock/placeholder task under an ad-hoc milestone if task doesn't exist
            # This is helpful if scheduler agent books general blocks
            pass
            
        execute_db(
            "UPDATE tasks SET scheduled_start = ?, scheduled_end = ?, status = 'scheduled' WHERE id = ?",
            (start_time, end_time, task_id)
        )
        
        # Write to simple workspace .ics file for visual local double-booking tests
        ics_path = "calendar.ics"
        try:
            with open(ics_path, "a", encoding="utf-8") as f:
                f.write(f"BEGIN:VEVENT\nSUMMARY:{title or 'Study Slot'}\nDTSTART:{start_time.replace('-','').replace(':','')}\nDTEND:{end_time.replace('-','').replace(':','')}\nEND:VEVENT\n")
        except Exception:
            pass
            
        return json.dumps({"status": "success", "msg": f"Task {task_id} successfully scheduled."})
        
    elif action == "delete":
        if not task_id:
            return json.dumps({"error": "task_id is required for deleting a schedule."})
            
        execute_db(
            "UPDATE tasks SET scheduled_start = NULL, scheduled_end = NULL, status = 'pending' WHERE id = ?",
            (task_id,)
        )
        return json.dumps({"status": "success", "msg": f"Task {task_id} schedule removed."})
        
    else:
        return json.dumps({"error": f"Unknown calendar action: {action}"})

# Tool 5: Skill Database Tool
@mcp.tool(name="skill_database_tool")
def skill_database_tool(action: str, user_skills: list = None, target_job: str = None) -> str:
    """
    Get matching details and calculate gaps between user skills and career target skill profiles.
    :param action: 'get_gaps' or 'validate_skill'
    :param user_skills: List of current skills (e.g. ['Python', 'SQL'])
    :param target_job: Target role title
    """
    if action == "get_gaps":
        if not target_job:
            return json.dumps({"error": "target_job required for gap analysis."})
            
        # Get target skills from job market data dictionary mapping
        market_res = json.loads(job_market_tool(target_job))
        required_skills = market_res.get("top_skills", ["Python", "SQL"])
        
        user_skills_clean = [s.lower().strip() for s in (user_skills or [])]
        
        gaps = []
        matching = []
        
        for req in required_skills:
            if req.lower().strip() in user_skills_clean:
                matching.append(req)
            else:
                gaps.append(req)
                
        return json.dumps({
            "target_job": target_job,
            "matching_skills": matching,
            "missing_skills": gaps,
            "match_percentage": (len(matching) / len(required_skills)) * 100 if required_skills else 0
        }, indent=2)
        
    elif action == "validate_skill":
        # Returns standard description of a skill
        rows = query_db("SELECT name, description, category FROM skills")
        all_skills = {r["name"].lower(): {"name": r["name"], "desc": r["description"], "cat": r["category"]} for r in rows}
        
        results = {}
        for skill in (user_skills or []):
            sk_key = skill.lower().strip()
            if sk_key in all_skills:
                results[skill] = all_skills[sk_key]
            else:
                results[skill] = {"name": skill, "desc": "Custom user skill", "cat": "General"}
        return json.dumps(results, indent=2)
        
    return json.dumps({"error": f"Invalid action: {action}"})

if __name__ == "__main__":
    import sys
    # FastMCP starts the stdio server automatically when executed
    mcp.run()
