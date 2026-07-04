# config.py
"""Centralized configuration loader for the project.
Loads environment variables from .env and provides defaults.
Used across agents and server modules.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

def get_env(key: str, default: str | None = None) -> str:
    value = os.getenv(key)
    if value is None:
        if default is None:
            raise EnvironmentError(f"Missing required environment variable: {key}")
        return default
    return value

GEMINI_MODEL = get_env('GEMINI_MODEL', 'gemini-2.5-flash')
GEMINI_API_KEY = get_env('GEMINI_API_KEY')
DATABASE_URL = get_env('DATABASE_URL', str(BASE_DIR / 'careerforge.db'))
