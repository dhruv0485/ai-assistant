# src/scorer.py
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.llm_client import call_llm
from src.skill_ontology import match_skills
from src.decision import make_decision
from config import (
    BORDERLINE_LOW,
    BORDERLINE_HIGH,
    CONFIDENCE_RUNS,
    CONFIDENCE_VARIANCE,
    ADVANCE_THRESHOLD,
    ESCALATE_THRESHOLD,
    REJECT_THRESHOLD,
    GEMINI_PASS2_MODEL,
)

SCORE_SYSTEM = """You are a senior technical recruiter with 10 years experience.
You score candidates fairly and cite specific evidence from their resume.
You NEVER make assumptions. If something is not stated, it is not there.
Wrongly rejecting a good candidate is worse than shortlisting a weak one.
Return ONLY valid JSON. No markdown, no explanation, no preamble."""

SCORE_PROMPT = """Score this candidate for the job below.

CRITICAL EVIDENCE RULE:
For evidence field, you MUST copy the EXACT sentence or phrase from the 
resume text that proves the skill. Do NOT just write the skill name.
Example:
  BAD:  "evidence": "mysql"
  GOOD: "evidence": "Launched 5 web applications using FastAPI, MongoDB, and PostgreSQL with Razorpay REST APIs"
If no sentence exists, set evidence to null and met to false.

JD EXTRACTED FIELDS:
{jd_extracted}

RESUME EXTRACTED FIELDS:
{resume_extracted}

RAW RESUME TEXT (use this to cite exact sentences):
{resume_text}

SEMANTIC SKILL MATCHES (pre-computed):
{skill_matches}

Instructions:
1. For every must-have skill: find the exact resume sentence proving it. If absent, mark as gap and set evidence to null.
2. For every nice-to-have: same process.
3. Consider years of experience relative to requirement.
4. Consider education fit.
5. Score 0-100 based on evidence only.

Return this exact JSON structure:
{{
    "score": <integer 0-100>,
    "must_have_met": [
        {{"skill": "skill name", "evidence": "exact sentence from resume proving this", "met": true}}
    ],
    "nice_to_have_met": [
        {{"skill": "skill name", "evidence": "exact sentence from resume or null", "met": true}}
    ],
    "experience_fit": {{
        "required_years": <int or null>,
        "candidate_years": <int or null>,
        "note": "brief note"
    }},
    "education_fit": "strong/adequate/weak/unknown",
    "gaps": ["list of key missing requirements"],
    "strengths": ["list of standout positives"],
    "overall_explanation": "2-3 sentence summary for recruiter"
}}"""

def get_decision(score: int) -> Dict[str, str]:
    """
    Maps a 0-100 score to organizational screening decision thresholds:
    - Score >= ADVANCE_THRESHOLD (65) -> AUTO-ADVANCE
    - Score >= ESCALATE_THRESHOLD (30) -> ESCALATE (30-64 human recruiter review)
    - Score < REJECT_THRESHOLD (30)   -> REJECT (< 30)
    """
    if score >= ADVANCE_THRESHOLD:
        return {
            "decision": "AUTO-ADVANCE",
            "label": "Shortlisted for Interview",
            "style": "bold green"
        }
    elif score >= ESCALATE_THRESHOLD:
        return {
            "decision": "ESCALATE",
            "label": "Escalate to Human Recruiter",
            "style": "bold yellow"
        }
    else:
        return {
            "decision": "REJECT",
            "label": "Does Not Meet Core Requirements",
            "style": "bold red"
        }

def score_candidate(resume_extracted: dict, jd_extracted: dict,
                    jd_normalized: Optional[dict] = None, resume_text: str = "",
                    fast: bool = False) -> dict:
    """
    Pass 2: Score and explain the match.
    Uses Gemini (gemini-3.5-flash-lite) by default via call_llm(fast=False, model=GEMINI_PASS2_MODEL)
    for deep evidence extraction and reasoning.
    Pre-computes semantic skill matches with the ontology.
    """
    # Pre-compute semantic skill matches
    jd_skills = jd_extracted.get("must_have_skills", []) + \
                jd_extracted.get("nice_to_have_skills", [])
    resume_skills = resume_extracted.get("skills", [])
    skill_matches = match_skills(jd_skills, resume_skills)

    # Use raw resume text if provided; otherwise synthesize from extracted profile
    clean_resume_text = resume_text.strip() if resume_text else json.dumps(resume_extracted, indent=2)

    prompt = SCORE_PROMPT.format(
        jd_extracted=json.dumps(jd_extracted, indent=2),
        resume_extracted=json.dumps(resume_extracted, indent=2),
        resume_text=clean_resume_text[:4000],
        skill_matches=json.dumps(skill_matches, indent=2)
    )

    result = call_llm(SCORE_SYSTEM, prompt, fast=fast, model=GEMINI_PASS2_MODEL)  # Pass 2 model (gemini-3.5-flash-lite)
    result["skill_match_detail"] = skill_matches

    # Ensure score is an integer between 0 and 100
    score_val = result.get("score", 50)
    try:
        score_val = max(0, min(100, int(round(float(score_val)))))
    except Exception:
        score_val = 50
    result["score"] = score_val

    # Attach Phase 7 Decision Engine evaluation
    dec_meta = get_decision(score_val)
    dec_policy = make_decision(result, jd_extracted)
    result["decision"] = dec_policy["decision"]
    result["decision_label"] = dec_meta["label"]
    result["decision_reason"] = dec_policy["reason"]
    result["critical_gaps"] = dec_policy.get("critical_gaps", [])
    result["decision_details"] = dec_policy

    return result

def score_with_confidence(resume_extracted: dict, jd_extracted: dict,
                          jd_normalized: Optional[dict] = None, resume_text: str = "") -> dict:
    """
    For borderline candidates (45-70): run scoring N times, report confidence & variance.
    For clear cases: run once with HIGH confidence.
    """
    # Quick first score to check if borderline
    first_result = score_candidate(
        resume_extracted, jd_extracted, jd_normalized, resume_text=resume_text, fast=False
    )
    score = first_result.get("score", 50)

    # Not borderline — trust single score
    if not (BORDERLINE_LOW <= score <= BORDERLINE_HIGH):
        first_result["confidence"] = "HIGH"
        first_result["confidence_scores"] = [score]
        first_result["score_variance"] = 0
        dec_policy = make_decision(first_result, jd_extracted)
        first_result["decision"] = dec_policy["decision"]
        first_result["decision_reason"] = dec_policy["reason"]
        first_result["critical_gaps"] = dec_policy.get("critical_gaps", [])
        first_result["decision_details"] = dec_policy
        return first_result

    # Borderline — run CONFIDENCE_RUNS times
    print(f"  [scorer] Borderline score {score}. Running {CONFIDENCE_RUNS} passes...")
    all_scores = [score]
    for _ in range(CONFIDENCE_RUNS - 1):
        r = score_candidate(
            resume_extracted, jd_extracted, jd_normalized, resume_text=resume_text, fast=False
        )
        all_scores.append(r.get("score", score))

    variance = max(all_scores) - min(all_scores)
    avg_score = round(sum(all_scores) / len(all_scores))

    first_result["score"] = avg_score
    first_result["confidence"] = "LOW" if variance > CONFIDENCE_VARIANCE else "HIGH"
    first_result["confidence_scores"] = all_scores
    first_result["score_variance"] = variance

    # Update decision using Phase 7 Decision Engine based on final average score & calibrated confidence
    dec_meta = get_decision(avg_score)
    dec_policy = make_decision(first_result, jd_extracted)
    first_result["decision"] = dec_policy["decision"]
    first_result["decision_label"] = dec_meta["label"]
    first_result["decision_reason"] = dec_policy["reason"]
    first_result["critical_gaps"] = dec_policy.get("critical_gaps", [])
    first_result["decision_details"] = dec_policy

    return first_result
