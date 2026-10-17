# eval/judge.py
"""
LLM-as-Judge Evaluator for Explanation Quality & Human Agreement.

Uses Groq qwen/qwen3.8-27b with safe_call retry backoff.
Evaluates AI screening explanations against a 5-dimension rubric:
1. Groundedness / Faithfulness (1-5): Verifies facts against resume (no hallucinations).
2. Completeness & Depth (1-5): Covers both strengths and critical missing must-haves.
3. Actionability & Constructiveness (1-5): Clear, concrete justification for recruiters.
4. Objectivity & Fair Tone (1-5): Professional, bias-free, compliant evaluation.
5. Decision Alignment (1-5): Explanation logically justifies the final score & verdict.

Measures Judge-Human Agreement Rate and saves outputs to eval/judge_results.json.
"""

import sys
import os
import re
import time
import json
import random
from pathlib import Path
from typing import Dict, Any, List, Optional

# Reconfigure stdout for UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_EVAL_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _EVAL_DIR.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(_BACKEND_DIR / ".env")

try:
    from groq import Groq, RateLimitError
except ImportError:
    from openai import OpenAI as Groq
    RateLimitError = Exception

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEFAULT_GROQ_MODEL = "qwen/qwen3.8-27b"

GOLDEN_JSON = _EVAL_DIR / "data" / "golden_dataset.json"
RESULTS_JSON = _EVAL_DIR / "results.json"
JUDGE_RESULTS_JSON = _EVAL_DIR / "judge_results.json"


def get_groq_client():
    load_dotenv(_BACKEND_DIR / ".env", override=True)
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY not found in backend/.env")
    return Groq(api_key=key)


def safe_call(fn, *args, max_retries=6, **kwargs):
    """Execute LLM call with exponential backoff on Groq rate limits."""
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            err_str = str(e).lower()
            if "rate limit" in err_str or "429" in err_str or isinstance(e, RateLimitError):
                wait = (2 ** attempt) + random.uniform(0.5, 1.5)
                print(f"  [Judge RateLimit] Backing off {wait:.1f}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
            elif attempt < max_retries - 1 and ("timeout" in err_str or "503" in err_str):
                wait = (2 ** attempt) + 1.0
                print(f"  [Judge TransientError] {e}. Retrying in {wait:.1f}s...")
                time.sleep(wait)
            else:
                raise e
    raise RuntimeError("Rate limit retries exhausted in judge.")


JUDGE_SYSTEM = """You are an expert meta-evaluator and AI auditing judge for technical recruiting.
Evaluate candidate screening explanations with strict objectivity and rigorous standards.
Return ONLY valid JSON with no markdown formatting."""

JUDGE_PROMPT = """You are evaluating an AI Screening System's explanation and decision against human ground truth.

JOB CONTEXT:
Title: {jd_title}
Requirements / Context: {jd_snippet}

CANDIDATE BACKGROUND:
Category: {resume_category}
Resume Extract: {resume_snippet}

HUMAN GROUND TRUTH:
Human Score: {human_score}/100
Human Decision: {human_decision}
Human Notes: {human_notes}

AI SCREENING SYSTEM OUTPUT:
AI Score: {ai_score}/100
AI Decision: {ai_decision}
AI Explanation: {ai_explanation}
Key Strengths Cited: {key_strengths}
Key Gaps Cited: {key_gaps}

EVALUATION RUBRIC (Score each 1 to 5, where 5 is flawless and 1 is unacceptable):
1. Groundedness (1-5): Is the AI explanation strictly grounded in facts from the resume? (5 = no hallucinations, 1 = fabricated claims)
2. Completeness (1-5): Did the AI capture both critical strengths and must-have gaps? (5 = exhaustive, 1 = missed major obvious blockers)
3. Actionability (1-5): Is the explanation helpful and clear for a recruiter or hiring manager making a decision? (5 = highly actionable, 1 = vague)
4. Objectivity (1-5): Is the tone professional, unbiased, and free of discriminatory or pedigree proxy bias? (5 = perfectly objective)
5. Decision Alignment (1-5): Does the narrative explanation logically justify the score and verdict? (5 = seamless logic)

AGREEMENT WITH HUMAN:
- Does the AI decision and explanation align with the human ground truth?
- What would be your independent verdict as an expert judge?

Return this exact JSON structure:
{{
    "rubric_scores": {{
        "groundedness": <integer 1-5>,
        "completeness": <integer 1-5>,
        "actionability": <integer 1-5>,
        "objectivity": <integer 1-5>,
        "decision_alignment": <integer 1-5>
    }},
    "overall_quality_score": <float 0-100 calculated as average of rubric * 20>,
    "agrees_with_human": <boolean true/false>,
    "agrees_with_ai": <boolean true/false>,
    "judge_recommended_decision": "ADVANCE" | "ESCALATE" | "REJECT",
    "judge_critique": "Brief 1-2 sentence critique of the explanation quality and accuracy."
}}"""


def run_llm_judge(sample_size: int = 30, model: str = DEFAULT_GROQ_MODEL,
                  sleep_sec: float = 2.0) -> Dict[str, Any]:
    """
    Run LLM-as-judge evaluation on sample_size screened candidate pairs.
    """
    client = get_groq_client()

    # Load results
    if not RESULTS_JSON.exists():
        raise FileNotFoundError(
            f"Screening results not found at {RESULTS_JSON}. "
            "Please run 'python eval/build_golden_set.py --screen' first."
        )

    results = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    golden_pairs = {}
    if GOLDEN_JSON.exists():
        for p in json.loads(GOLDEN_JSON.read_text(encoding="utf-8")):
            golden_pairs[p["pair_id"]] = p

    # Load existing judge checkpoint
    existing_judgments = {}
    if JUDGE_RESULTS_JSON.exists():
        try:
            saved = json.loads(JUDGE_RESULTS_JSON.read_text(encoding="utf-8"))
            for j in saved.get("evaluations", []):
                existing_judgments[j["pair_id"]] = j
            print(f"Loaded {len(existing_judgments)} existing judge evaluations.")
        except Exception:
            existing_judgments = {}

    # Sample stratified pairs across match types (match, mismatch, hard case)
    evaluated_pairs = []
    by_type = {"clear_match": [], "clear_mismatch": [], "hard_case": []}
    for r in results:
        m_type = r.get("match_type", "clear_match")
        by_type.setdefault(m_type, []).append(r)

    target_per_type = max(1, sample_size // 3)
    sampled = []
    for m_type, group in by_type.items():
        sampled.extend(group[:target_per_type])
    if len(sampled) < sample_size:
        remaining = [r for r in results if r not in sampled]
        sampled.extend(remaining[:sample_size - len(sampled)])

    print(f"\n{'='*65}")
    print(f"Running LLM-as-Judge with Groq ({model}) on {len(sampled)} pairs")
    print(f"{'='*65}")

    for idx, r in enumerate(sampled, 1):
        pair_id = r["pair_id"]
        if pair_id in existing_judgments:
            evaluated_pairs.append(existing_judgments[pair_id])
            continue

        g_pair = golden_pairs.get(pair_id, {})
        jd_text = g_pair.get("jd_text", "")[:800]
        resume_text = g_pair.get("resume_text", "")[:1000]

        prompt = JUDGE_PROMPT.format(
            jd_title=r.get("jd_title", "Software Engineer"),
            jd_snippet=jd_text,
            resume_category=r.get("resume_category", "ENGINEERING"),
            resume_snippet=resume_text,
            human_score=r.get("human_score", 50),
            human_decision=r.get("human_decision", "ESCALATE"),
            human_notes=r.get("human_notes", "Standard candidate review."),
            ai_score=r.get("ai_score", 0),
            ai_decision=r.get("ai_decision", "REJECT"),
            ai_explanation=r.get("ai_explanation", "No explanation available."),
            key_strengths=", ".join(r.get("key_strengths", [])),
            key_gaps=", ".join(r.get("key_gaps", []))
        )

        def _call():
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            return resp.choices[0].message.content

        raw = safe_call(_call)
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        judge_eval = json.loads(clean)

        entry = {
            "pair_id": pair_id,
            "match_type": r.get("match_type"),
            "difficulty": r.get("difficulty"),
            "ai_decision": r.get("ai_decision"),
            "human_decision": r.get("human_decision"),
            "judge_recommended_decision": judge_eval.get("judge_recommended_decision"),
            "rubric_scores": judge_eval.get("rubric_scores", {}),
            "overall_quality_score": judge_eval.get("overall_quality_score", 80.0),
            "agrees_with_human": judge_eval.get("agrees_with_human", True),
            "agrees_with_ai": judge_eval.get("agrees_with_ai", True),
            "judge_critique": judge_eval.get("judge_critique", ""),
            "model_used": model
        }

        evaluated_pairs.append(entry)
        existing_judgments[pair_id] = entry

        rubric = entry["rubric_scores"]
        print(f"[{idx}/{len(sampled)}] {pair_id} | Qual: {entry['overall_quality_score']:.1f}/100 | "
              f"Grounded: {rubric.get('groundedness', 0)}/5 | Human Agree: {entry['agrees_with_human']}")

        # Save checkpoint
        temp_out = {
            "sample_size": len(evaluated_pairs),
            "evaluations": evaluated_pairs
        }
        JUDGE_RESULTS_JSON.write_text(json.dumps(temp_out, indent=2, ensure_ascii=False), encoding="utf-8")
        time.sleep(sleep_sec)

    # Compute aggregate summary statistics
    rubric_sums = {
        "groundedness": 0.0,
        "completeness": 0.0,
        "actionability": 0.0,
        "objectivity": 0.0,
        "decision_alignment": 0.0
    }
    n = max(len(evaluated_pairs), 1)
    human_agreements = sum(1 for e in evaluated_pairs if e["agrees_with_human"])
    ai_agreements = sum(1 for e in evaluated_pairs if e["agrees_with_ai"])

    for e in evaluated_pairs:
        r = e.get("rubric_scores", {})
        for k in rubric_sums:
            rubric_sums[k] += r.get(k, 3)

    rubric_means = {k: round(v / n, 2) for k, v in rubric_sums.items()}
    overall_mean_quality = round(np.mean([e.get("overall_quality_score", 0) for e in evaluated_pairs]), 2)
    human_agreement_rate = round(human_agreements / n * 100, 2)
    ai_agreement_rate = round(ai_agreements / n * 100, 2)

    summary = {
        "total_evaluated": n,
        "model_used": model,
        "mean_rubric_scores": rubric_means,
        "overall_explanation_quality_score": overall_mean_quality,
        "judge_human_agreement_rate_pct": human_agreement_rate,
        "judge_ai_agreement_rate_pct": ai_agreement_rate
    }

    final_payload = {
        "summary": summary,
        "evaluations": evaluated_pairs
    }

    JUDGE_RESULTS_JSON.write_text(json.dumps(final_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✔ LLM Judge Evaluation Complete! Saved to {JUDGE_RESULTS_JSON}")

    print("\n" + "="*50)
    print("LLM-AS-JUDGE EXPLANATION QUALITY SUMMARY:")
    print("="*50)
    for k, v in rubric_means.items():
        print(f"  {k.replace('_', ' ').title():<25}: {v:.2f} / 5.0")
    print(f"  Overall Explanation Quality : {overall_mean_quality:.2f} / 100")
    print(f"  Judge-Human Agreement Rate  : {human_agreement_rate:.2f}%")
    print(f"  Judge-AI Agreement Rate     : {ai_agreement_rate:.2f}%")
    print("="*50)

    return final_payload


if __name__ == "__main__":
    import numpy as np
    import argparse
    parser = argparse.ArgumentParser(description="Run LLM-as-judge evaluation")
    parser.add_argument("--samples", type=int, default=30, help="Number of pairs to evaluate")
    parser.add_argument("--model", type=str, default=DEFAULT_GROQ_MODEL, help="Model name on Groq")
    parser.add_argument("--sleep", type=float, default=2.0, help="Sleep between calls")
    args = parser.parse_args()

    run_llm_judge(sample_size=args.samples, model=args.model, sleep_sec=args.sleep)
