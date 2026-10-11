# src/llm_client.py
import json, time
from google import genai
from google.genai import types
from openai import OpenAI
from config import *

# Configure Gemini client (new google-genai SDK)
client_gemini = genai.Client(api_key=GEMINI_API_KEY)

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
    models_to_try = [GEMINI_MODEL, "gemini-3-flash-preview", "gemini-2.5-flash-lite", "gemini-flash-latest"]
    last_error = None
    for m_name in models_to_try:
        try:
            response = client_gemini.models.generate_content(
                model=m_name,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    http_options=types.HttpOptions(timeout=15_000),
                ),
            )
            return response.text
        except Exception as e:
            last_error = e
            continue
    raise last_error

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
