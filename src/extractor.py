# src/extractor.py
import re
import sys
from pathlib import Path
from typing import Dict, Any, List

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.llm_client import call_llm
from src.skill_ontology import normalize_skill

EXTRACT_SYSTEM = """You are an expert resume and job description parser.
Extract structured information EXACTLY as specified.
Return ONLY valid JSON. No explanation, no preamble, no markdown."""

RESUME_EXTRACT_PROMPT = """Extract the following fields from this resume.
Be precise and literal — only extract what is explicitly stated.

Return this exact JSON structure:
{{
    "name": "candidate name or null",
    "skills": ["list", "of", "all", "technical", "skills", "mentioned"],
    "years_experience": <integer or null if unclear>,
    "education": {{
        "degree": "highest degree",
        "field": "field of study",
        "institution": "university name",
        "year": "graduation year or null"
    }},
    "past_roles": [
        {{"title": "job title", "company": "company", "duration_years": <float>}}
    ],
    "location": "city, country or null",
    "certifications": ["list of certifications"],
    "languages": ["programming or spoken languages"],
    "experience_ambiguity": <true if years_experience was unclear, else false>
}}

RESUME:
{resume_text}"""

JD_EXTRACT_PROMPT = """Extract the following fields from this job description.
Distinguish carefully between must-have (required) and nice-to-have (preferred).

CRITICAL RULE for must-have vs nice-to-have classification:
- must-have: "required", "must have", "strong knowledge of", "X years of experience in", "proven experience in", "proficient in"
- nice-to-have: "familiarity with", "experience with", "such as", "knowledge of", "preferred", "plus", "bonus", "good to have", "nice to have", "desirable"

For guidance:
- "Strong knowledge of PHP and MySQL" → must-have ("php", "mysql")
- "Experience with modern PHP frameworks (such as Laravel or Symfony)" → nice-to-have
- "Familiarity with RESTful API" → nice-to-have
- "Experience with version control systems (such as Git)" → nice-to-have
- Soft skills (communication, teamwork) → nice-to-have unless explicitly labeled "mandatory" or "must have"

Return this exact JSON structure:
{{
    "job_title": "exact job title",
    "company": "company name or null",
    "must_have_skills": ["absolutely required skills"],
    "nice_to_have_skills": ["preferred but not required skills"],
    "min_years_experience": <integer or null>,
    "education_required": "required education level or null",
    "location": "job location or remote",
    "responsibilities": ["key responsibilities, max 5"],
    "domain": "industry/domain e.g. fintech, healthcare, SaaS"
}}

JOB DESCRIPTION:
{jd_text}"""

def _normalize_skill_list(skills: Any) -> List[str]:
    """
    Helper to deduplicate and normalize skills through skill ontology.
    Intelligently splits multi-skill conjunctions like 'PHP and MySQL',
    'Docker & Kubernetes', 'React / Redux', while preserving canonical skills.
    """
    if not isinstance(skills, list):
        return []
    normalized: List[str] = []
    seen = set()

    for raw_item in skills:
        if not isinstance(raw_item, str) or not raw_item.strip():
            continue
        clean_item = raw_item.strip()
        # If the phrase has conjunctions/delimiters and is not already a single exact skill in ontology
        sub_items = re.split(
            r"(?<=\S)\s+and\s+(?=\S)|(?<=\S)\s*&\s*(?=\S)|(?<=\S)\s*,\s*(?=\S)|(?<=\S)\s+/\s+(?=\S)",
            clean_item,
            flags=re.IGNORECASE
        )

        if len(sub_items) > 1:
            for item in sub_items:
                s = item.strip()
                if not s:
                    continue
                canon = normalize_skill(s)
                if canon and canon not in seen:
                    seen.add(canon)
                    normalized.append(canon)
        else:
            canon = normalize_skill(clean_item)
            if canon and canon not in seen:
                seen.add(canon)
                normalized.append(canon)

    return normalized

def extract_resume(resume_text: str, fast: bool = False) -> Dict[str, Any]:
    """
    Pass 1a: Extract structured fields from resume.
    Uses Gemini (gemini-2.0-flash) by default via call_llm(fast=False).
    Normalizes all extracted skills through the technical skill ontology.
    """
    prompt = RESUME_EXTRACT_PROMPT.format(resume_text=resume_text[:4000])
    result = call_llm(EXTRACT_SYSTEM, prompt, fast=fast)
    
    # Normalize all extracted skills through ontology
    result["skills"] = _normalize_skill_list(result.get("skills", []))
    return result

def extract_jd(jd_text: str, fast: bool = False) -> Dict[str, Any]:
    """
    Pass 1b: Extract structured fields from job description.
    Uses Gemini (gemini-2.0-flash) by default via call_llm(fast=False).
    Normalizes must-have and nice-to-have skills through the technical skill ontology.
    """
    prompt = JD_EXTRACT_PROMPT.format(jd_text=jd_text[:4000])
    result = call_llm(EXTRACT_SYSTEM, prompt, fast=fast)
    
    # Normalize JD skills through ontology
    result["must_have_skills"] = _normalize_skill_list(result.get("must_have_skills", []))
    result["nice_to_have_skills"] = _normalize_skill_list(result.get("nice_to_have_skills", []))
    return result
