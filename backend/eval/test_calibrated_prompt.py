import json
import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from eval.build_golden_set import get_groq_client, call_groq_json

client = get_groq_client()
with open("eval/data/golden_dataset.json", encoding="utf-8") as f:
    pairs = json.load(f)

test_pairs = [
    next(p for p in pairs if p["match_type"] == "clear_match"),
    next(p for p in pairs if p["match_type"] == "clear_mismatch"),
    next(p for p in pairs if p["match_type"] == "hard_case")
]

calibrated_prompt = """You are a rigorous Principal Software Engineering Recruiter evaluating candidate-job alignment.

CRITICAL RULE (GROUNDEDNESS): Only cite evidence that appears VERBATIM or near-verbatim in the resume text. If a skill is not explicitly mentioned, mark it as a gap. Never infer or assume unstated experience.

JOB POSTING:
Title: {jd_title}
Requirements / Description:
{jd_text}

CANDIDATE RESUME:
Category: {resume_category}
Resume Extract:
{resume_text}

CALIBRATION GUIDE (follow strictly):
- Score 70-100 (ADVANCE): Candidate meets ALL core must-have technical skills, has direct relevant SWE experience, and is a strong match for technical interview.
- Score 40-69 (ESCALATE): Borderline candidate requiring human recruiter review. Meets partial stack, or junior for senior role, or overqualified engineering manager, or stack transition (e.g. Java to Python).
- Score 0-39 (REJECT): Candidate missing critical core must-haves, non-engineering background, or severe qualification mismatch.

DECISION RULES:
- ADVANCE: score >= 65 AND core engineering must-haves met
- ESCALATE: score 35-64 OR edge case requiring human judgment
- REJECT: score < 35 OR wrong domain

Return JSON:
{{
    "score": <integer 0-100>,
    "decision": "ADVANCE" | "ESCALATE" | "REJECT",
    "confidence": "HIGH" | "MEDIUM" | "LOW",
    "matched_skills": ["list"],
    "missing_skills": ["list"],
    "overall_explanation": "2-3 sentence hiring rationale grounded verbatim in text.",
    "key_strengths": ["strength 1"],
    "key_gaps": ["gap 1"]
}}"""

for p in test_pairs:
    prompt = calibrated_prompt.format(
        jd_title=p["jd_title"],
        jd_text=p["jd_text"][:1800],
        resume_category=p["resume_category"],
        resume_text=p["resume_text"][:2200]
    )
    res = call_groq_json(client, prompt)
    print(f"{p['pair_id']} ({p['match_type']}): AI Score={res.get('score')}, AI Decision={res.get('decision')} vs Human Score={p['human_score']}, Human Decision={p['human_decision']}")
