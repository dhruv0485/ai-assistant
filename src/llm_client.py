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

def call_pass1_gemini(system: str, user: str) -> str:
    """
    Pass 1 fallback chain for spikes in demand:
      1. ('gemini', 'gemini-3.6-flash')        # primary — workhorse
      2. ('gemini', 'gemini-3.5-flash')        # fallback 1 — slightly heavier
      3. ('gemini', 'gemini-3.1-flash-lite')   # fallback 2 — older but reliable
      4. ('gemini', 'gemini-3.8-flash')        # fallback 3 — newest, may be busy
    """
    last_error = None
    for provider, m_name in PASS1_MODELS:
        if provider == "gemini":
            try:
                response = client_gemini.models.generate_content(
                    model=m_name,
                    contents=user,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        response_mime_type="application/json",
                        http_options=types.HttpOptions(timeout=45_000),
                    ),
                )
                return response.text
            except Exception as e:
                last_error = e
                print(f"  [llm_client] Pass 1 '{m_name}' unavailable/spike ({e}). Trying next fallback...")
                continue
        elif provider in ("openrouter", "groq"):
            client = openrouter_client if provider == "openrouter" else groq_client
            try:
                return call_openai_compatible(client, m_name, system, user)
            except Exception as e:
                last_error = e
                print(f"  [llm_client] Pass 1 ({provider}/{m_name}) error ({e}). Trying next fallback...")
                continue
    raise last_error

def call_gemini(system: str, user: str, model: str = None) -> str:
    # Use specified model or GEMINI_MODEL (used for Pass 2 and general calls)
    target_model = model or GEMINI_MODEL
    try:
        response = client_gemini.models.generate_content(
            model=target_model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                http_options=types.HttpOptions(timeout=45_000),
            ),
        )
        return response.text
    except Exception as e:
        # If 404 (retired model), fallback to active flash
        if "404" in str(e) or "NOT_FOUND" in str(e) or "no longer available" in str(e):
            response = client_gemini.models.generate_content(
                model="gemini-3.5-flash",
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    http_options=types.HttpOptions(timeout=45_000),
                ),
            )
            return response.text
        raise e

def call_openai_compatible(client, model: str, system: str, user: str) -> str:
    try:
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        if hasattr(e, "body") and isinstance(e.body, dict) and "error" in e.body:
            failed_gen = e.body["error"].get("failed_generation")
            if failed_gen:
                return failed_gen
        raise e

def call_pass1_llm(system: str, user: str) -> dict:
    """
    Dedicated Pass 1 LLM caller using PASS1_MODELS fallback chain for demand spikes:
      1. gemini-3.6-flash (primary)
      2. gemini-3.5-flash (fallback 1)
      3. gemini-3.1-flash-lite (fallback 2)
      4. gemini-3.8-flash (fallback 3)
    """
    try:
        raw = call_pass1_gemini(system, user)
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean)
    except Exception as e:
        print(f"  [llm_client] Pass 1 fallback chain failed: {e}")
        try:
            raw = call_openai_compatible(groq_client, GROQ_MODEL, system, user)
            clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(clean)
        except Exception:
            raise e

def call_llm(system: str, user: str, fast: bool = False, model: str = None, stage: str = None) -> dict:
    """
    Calls model:
      - Pass 1 (stage='pass1' or model=GEMINI_PASS1_MODEL): uses PASS1_MODELS fallback chain
      - Pass 2: uses specified model (gemini-3.5-flash-lite)
    """
    pass1_model_names = [m[1] for m in PASS1_MODELS]
    is_pass1 = (stage == "pass1") or (model == GEMINI_PASS1_MODEL) or (model in pass1_model_names and model != GEMINI_PASS2_MODEL)
    try:
        if is_pass1:
            raw = call_pass1_gemini(system, user)
        else:
            raw = call_gemini(system, user, model=model)
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean)
    except Exception as e:
        print(f"  [llm_client] Gemini call failed: {e}")
        # Emergency backup only if Gemini API is completely unavailable
        try:
            raw = call_openai_compatible(groq_client, GROQ_MODEL, system, user)
            clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(clean)
        except Exception:
            raise e
