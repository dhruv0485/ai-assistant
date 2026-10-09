# src/llm_client.py
import json, time
import google.generativeai as genai
from openai import OpenAI
from config import *

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Configure OpenRouter + Groq clients (same OpenAI-compatible API)
openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY
)
groq_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY
)

def call_gemini(system: str, user: str) -> str:
    try:
        model = genai.GenerativeModel(
            GEMINI_MODEL,
            system_instruction=system
        )
        response = model.generate_content(
            user,
            generation_config={"response_mime_type": "application/json"}
        )
        return response.text
    except Exception as e:
        # Google deprecation handler: fallback to current flash model if 2.0 returns 404
        if "no longer available" in str(e).lower() or "404" in str(e):
            fallback_model = "gemini-3.8-flash"
            model = genai.GenerativeModel(
                fallback_model,
                system_instruction=system
            )
            response = model.generate_content(
                user,
                generation_config={"response_mime_type": "application/json"}
            )
            return response.text
        raise e

def call_openai_compatible(client, model: str, system: str, user: str) -> str:
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user}
        ]
    )
    return response.choices[0].message.content

def call_llm(system: str, user: str, fast: bool = False) -> dict:
    """
    Master LLM caller with automatic fallback chain.
    Returns parsed dict always.
    fast=True uses Groq for bulk/speed tasks.
    """
    providers = []

    if fast:
        # Speed path: Groq first
        providers = [
            ("groq",        lambda: call_openai_compatible(groq_client, GROQ_MODEL, system, user)),
            ("gemini",      lambda: call_gemini(system, user)),
            ("openrouter",  lambda: call_openai_compatible(openrouter_client, OPENROUTER_MODEL, system, user)),
        ]
    else:
        # Quality path: Gemini first
        providers = [
            ("gemini",      lambda: call_gemini(system, user)),
            ("openrouter",  lambda: call_openai_compatible(openrouter_client, OPENROUTER_MODEL, system, user)),
            ("groq",        lambda: call_openai_compatible(groq_client, GROQ_MODEL, system, user)),
        ]

    last_error = None
    for name, fn in providers:
        try:
            raw = fn()
            # Strip markdown fences if model added them
            clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(clean)
        except Exception as e:
            print(f"  [llm_client] {name} failed: {e}")
            last_error = e
            time.sleep(1)  # brief pause before trying next

    raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")
