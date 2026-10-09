# config.py
import os
from dotenv import load_dotenv
load_dotenv()

# API Keys — put these in a .env file, never commit
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY")
OPENROUTER_KEY    = os.getenv("OPENROUTER_API_KEY")
GROQ_API_KEY      = os.getenv("GROQ_API_KEY")

# Model names — change here only, never hunt through code
GEMINI_MODEL      = "gemini-2.0-flash"
OPENROUTER_MODEL  = "qwen/qwen3-235b-a22b:free"
GROQ_MODEL        = "openai/gpt-oss-20b"
OLLAMA_MODEL      = "qwen3:7b"
EMBED_MODEL       = "all-MiniLM-L6-v2"

# Decision thresholds
ADVANCE_THRESHOLD   = 65    # score >= 65 → auto-advance
ESCALATE_THRESHOLD  = 40    # score 40-64 → escalate to human
                            # score < 40  → reject with note
CONFIDENCE_RUNS     = 3     # how many times to run borderline scoring
BORDERLINE_LOW      = 45    # bottom of borderline zone
BORDERLINE_HIGH     = 70    # top of borderline zone
CONFIDENCE_VARIANCE = 10    # if scores vary > this → LOW confidence
