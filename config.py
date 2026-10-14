# config.py
import os
from pathlib import Path
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# API Keys — put these in a .env file, never commit
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY")
OPENROUTER_KEY    = os.getenv("OPENROUTER_API_KEY")
GROQ_API_KEY      = os.getenv("GROQ_API_KEY")

# Pass 1 model fallback chain for demand spikes
PASS1_MODELS = [
    ("gemini", "gemini-3.1-flash-lite"),        # primary — workhorse
    ("gemini", "gemini-3.5-flash"),        # fallback 1 — slightly heavier
    ("gemini", "gemini-3.6-flash"),   # fallback 2 — older but reliable
    ("gemini", "gemini-3.8-flash"),        # fallback 3 — newest, may be busy
]

GEMINI_PASS1_MODEL = PASS1_MODELS[0][1]        # primary Pass 1: gemini-3.6-flash
GEMINI_PASS2_MODEL = "gemini-3.1-flash-lite"   # Pass 2: Scoring, Explainability & Evidence
GEMINI_MODEL       = GEMINI_PASS1_MODEL        # Default / base Gemini model
OPENROUTER_MODEL  = "meta-llama/llama-3.3-70b-instruct:free"
GROQ_MODEL        = "openai/gpt-oss-20b"
OLLAMA_MODEL      = "qwen3:7b"
EMBED_MODEL       = "all-MiniLM-L6-v2"

# Decision thresholds
REJECT_THRESHOLD    = 30    # score < 30  → reject with note
ESCALATE_THRESHOLD  = 30    # score 30-64 → escalate to human review
ADVANCE_THRESHOLD   = 65    # score >= 65 → auto-advance
CONFIDENCE_RUNS     = 3     # how many times to run borderline scoring
BORDERLINE_LOW      = 45    # bottom of borderline zone
BORDERLINE_HIGH     = 70    # top of borderline zone
CONFIDENCE_VARIANCE = 10    # if scores vary > this → LOW confidence
