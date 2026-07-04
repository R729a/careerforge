import json
from agents.base_agent import BaseAgent, broadcast_log

class TaskOptimizationAgent(BaseAgent):
    def __init__(self):
        system_instruction = (
            "You are the CareerForge AI Task Optimization Agent. Your job is to break down a specific career "
            "roadmap milestone into daily/weekly actionable micro-tasks. For each task, provide priority (high, medium, low) "
            "and estimated duration in hours. Output raw JSON matching this structure:\n"
            "[\n"
            "  {\n"
            "    \"title\": \"Task title\",\n"
            "    \"priority\": \"high\",\n"
            "    \"estimated_hours\": 3.5\n"
            "  }\n"
            "]"
        )
        super().__init__(name="TaskOptimizer", system_instruction=system_instruction)

    def optimize_tasks(self, milestone_title: str, milestone_description: str, client_id: str = None) -> list:
        broadcast_log(client_id, "TaskOptimizationAgent", "optimize_tasks", "running", f"Generating detailed subtasks for milestone: {milestone_title}...")
        prompt = (
            f"Decompose the following milestone into exactly 3-4 distinct actionable study or hands-on practice tasks:\n"
            f"Milestone: {milestone_title}\n"
            f"Description: {milestone_description}"
        )
        response_text = self.run_llm(prompt, response_json=True)


        try:
            cleaned = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except Exception:
            return self._mock_tasks(milestone_title)

    def _mock_tasks(self, milestone_title: str) -> list:
        # Check what the milestone is about to make mock tasks realistic
        m_lower = milestone_title.lower()
        if "python" in m_lower:
            return [
                {"title": "Watch Python basic syntax videos & download IDE", "priority": "high", "estimated_hours": 2.0},
                {"title": "Complete variables, lists, and loops exercises", "priority": "high", "estimated_hours": 3.0},
                {"title": "Build a CLI Calculator app using python functions", "priority": "medium", "estimated_hours": 4.0}
            ]
        elif "ml" in m_lower or "machine learning" in m_lower:
            return [
                {"title": "Study linear regression and gradient descent", "priority": "high", "estimated_hours": 3.0},
                {"title": "Implement linear regression in Jupyter using Scikit-Learn", "priority": "high", "estimated_hours": 4.0},
                {"title": "Evaluate model results using MSE metrics", "priority": "medium", "estimated_hours": 2.0}
            ]
        elif "pytorch" in m_lower or "deep learning" in m_lower:
            return [
                {"title": "Read PyTorch tensor operations documentation", "priority": "high", "estimated_hours": 1.5},
                {"title": "Build a 3-layer neural network on MNIST dataset", "priority": "high", "estimated_hours": 5.0},
                {"title": "Tune learning rate hyperparameters and graph training loss", "priority": "medium", "estimated_hours": 3.0}
            ]
        else:
            return [
                {"title": f"Review core study resources for {milestone_title}", "priority": "high", "estimated_hours": 2.5},
                {"title": f"Complete hands-on lab projects mapping to {milestone_title}", "priority": "high", "estimated_hours": 4.0},
                {"title": f"Complete practice quiz assessment", "priority": "medium", "estimated_hours": 1.5}
            ]
Definition: "Created task_optimizer.py agent component with task decomposition logic."
