import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config
import google.generativeai as genai
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional



class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, client_id: str, websocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_log(self, client_id: str, log: dict):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(log)
            except Exception:
                pass

manager = ConnectionManager()
main_loop = None

def broadcast_log(client_id: str, agent: str, action: str, status: str, message: str, extra: Optional[dict] = None):
    print(f"[broadcast_log] Broadcast attempt. Client: {client_id}, Agent: {agent}, Action: {action}, Status: {status}")
    if not client_id:
        print("[broadcast_log] Aborted: No client_id provided.")
        return
    log_payload = {
        "agent": agent,
        "action": action,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "message": message
    }
    if extra:
        log_payload.update(extra)
    
    print(f"[broadcast_log] Active connections in manager: {list(manager.active_connections.keys())}")
    if client_id in manager.active_connections:
        print(f"[broadcast_log] Target client connected. Sending WebSocket event...")
        if main_loop and main_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                manager.send_log(client_id, log_payload),
                main_loop
            )
        else:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    manager.send_log(client_id, log_payload),
                    loop
                )
            else:
                loop.run_until_complete(manager.send_log(client_id, log_payload))
    else:
        print(f"[broadcast_log] Warning: Target client {client_id} NOT found in active connections!")



class BaseAgent:
    def __init__(self, name: str, system_instruction: str):
        self.name = name
        self.system_instruction = system_instruction
        self.api_key = config.GEMINI_API_KEY
        self.model_name = config.GEMINI_MODEL
        self.model = None

        # Testing Guardrail to prevent live endpoint quota depletion during test suites
        if os.getenv("INTEGRATION_TESTING") == "true" or os.getenv("PYTEST_CURRENT_TEST"):
            print(f"[Agent {self.name}] Running under testing context. Forcing MOCK mode.")
            self.model = None
            return

        if self.api_key and self.api_key != "your_gemini_api_key_here":
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=system_instruction
                )
                print(f"[Agent {self.name}] Initialized with model {self.model_name}")
            except Exception as e:
                print(f"[Agent {self.name}] Initialization failed, falling back to Mock: {e}")
        else:
            print(f"[Agent {self.name}] GEMINI_API_KEY not set. Operating in MOCK mode.")

    def run_llm(self, prompt: str, response_json: bool = False) -> str:
        """
        Runs the LLM query with self.system_instruction.
        If offline or mocked, redirects to _mock_run.
        """
        print(f"[Agent {self.name}] Calling Gemini LLM (JSON constraint: {response_json})...")
        if self.model:
            try:
                config = {}
                if response_json:
                    config["response_mime_type"] = "application/json"
                
                response = self.model.generate_content(
                    prompt, 
                    generation_config=config
                )
                return response.text
            except Exception as e:
                print(f"[Agent {self.name}] LLM run error: {e}. Executing fallback mock.")
                return self._mock_run(prompt)
        else:
            return self._mock_run(prompt)


    def _mock_run(self, prompt: str) -> str:
        """
        Mock implementation to be overridden by subclasses.
        """
        return f"Mock response from {self.name} for prompt: {prompt[:100]}..."
