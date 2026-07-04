import json
from agents.base_agent import BaseAgent, broadcast_log

class StudyCoachAgent(BaseAgent):
    def __init__(self):
        system_instruction = (
            "You are the CareerForge AI Exam & Study Coach Agent. Your job is to generate high-quality "
            "technical study summaries (notes) and multiple-choice quizzes to assess a user's progress. "
            "When asked for a quiz, you MUST return a raw JSON array of questions:\n"
            "[\n"
            "  {\n"
            "    \"question_id\": 1,\n"
            "    \"text\": \"Question text?\",\n"
            "    \"options\": [\"Option A\", \"Option B\", \"Option C\"],\n"
            "    \"correct_index\": 0\n"
            "  }\n"
            "]"
        )
        super().__init__(name="StudyCoach", system_instruction=system_instruction)

    def generate_study_notes(self, subject: str, client_id: str = None) -> str:
        broadcast_log(client_id, "StudyCoachAgent", "generate_study_notes", "running", f"Study Coach Agent compiling training study notes on subject: {subject}...")
        prompt = f"Generate a comprehensive, brief study cheat-sheet/notes for the following topic: {subject}."
        return self.run_llm(prompt)

    def generate_quiz(self, subject: str, client_id: str = None) -> list:
        broadcast_log(client_id, "StudyCoachAgent", "generate_quiz", "running", f"Study Coach Agent formulating diagnostic review questions for: {subject}...")
        prompt = f"Generate a 3-question multiple-choice quiz about: {subject}. Output only the JSON payload."
        response_text = self.run_llm(prompt, response_json=True)


        try:
            cleaned = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except Exception:
            return self._mock_quiz(subject)

    def _mock_quiz(self, subject: str) -> list:
        s_lower = subject.lower()
        if "pytorch" in s_lower:
            return [
                {
                    "question_id": 1,
                    "text": "Which PyTorch function is used to compute gradients during the backward pass?",
                    "options": ["loss.backward()", "optimizer.step()", "tensor.zero_grad()", "gradients()"],
                    "correct_index": 0,
                    "hint": "loss.backward() computes the gradient of current tensor w.r.t graph leaves."
                },
                {
                    "question_id": 2,
                    "text": "What does tensor.view(-1, 1) accomplish?",
                    "options": ["Transposes the tensor", "Reshapes the tensor to have 1 column and dynamic rows", "Deletes data", "Flattens into 1D"],
                    "correct_index": 1,
                    "hint": "The -1 argument tells PyTorch to dynamically infer the row dimension size based on elements."
                },
                {
                    "question_id": 3,
                    "text": "Which optimizer is commonly used in deep learning for adaptive gradient weights?",
                    "options": ["SGD", "Adam", "AdaGrad", "RMSprop"],
                    "correct_index": 1,
                    "hint": "Adam combines RMSprop adaptive scale with SGD with momentum."
                }
            ]
        elif "python" in s_lower:
            return [
                {
                    "question_id": 1,
                    "text": "What is the output of len([1, 2, 3]) in Python?",
                    "options": ["2", "3", "4", "Error"],
                    "correct_index": 1,
                    "hint": "The len() function returns the total number of items stored in list collections."
                },
                {
                    "question_id": 2,
                    "text": "How do you define a function in Python?",
                    "options": ["function myFunc():", "def myFunc():", "func myFunc():", "lambda myFunc():"],
                    "correct_index": 1,
                    "hint": "Python uses the def keyword to start standard method declarations."
                },
                {
                    "question_id": 3,
                    "text": "Which of the following is an immutable data type in Python?",
                    "options": ["List", "Dictionary", "Set", "Tuple"],
                    "correct_index": 3,
                    "hint": "Tuples are write-protected read-only collections."
                }
            ]
        else:
            return [
                {
                    "question_id": 1,
                    "text": f"What is the core concern of {subject}?",
                    "options": ["Solving computational complexities", "Hardware virtualization", "Standard procedures"],
                    "correct_index": 0,
                    "hint": "Target topics focus primarily on breaking down algorithmic structures and complexities."
                },
                {
                    "question_id": 2,
                    "text": f"Which tool is most relevant to {subject}?",
                    "options": ["Git version control", "Command line terminal", "Database engine"],
                    "correct_index": 0,
                    "hint": "Version control helps trace milestones modifications."
                },
                {
                    "question_id": 3,
                    "text": f"What is a standard best practice in {subject}?",
                    "options": ["Documentation and metrics tracking", "Ignoring compilation alerts", "Using raw variables only"],
                    "correct_index": 0,
                    "hint": "Adding descriptions and tracking metrics ensures audit security validation."
                }
            ]
