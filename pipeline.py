# pipeline.py
import json
import sys
from pathlib import Path

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.parser import parse_resume, parse_jd
from src.extractor import extract_resume, extract_jd
from src.jd_normalizer import normalize_jd
from src.scorer import score_with_confidence
from src.decision import make_decision
from src.fairness import run_fairness_audit

def screen_candidate(resume_path: str, jd_text: str,
                     run_fairness: bool = False) -> dict:
    """
    Full pipeline: resume file + JD text → screening result.
    Steps:
      1. Parse & mask PII
      2. Extract structured entities (Pass 1)
      3. Normalize JD against RAG templates
      4. Score candidate with confidence (Pass 2)
      5. Evaluate Phase 7 organizational decision policy
      6. Optional: Run Phase 8 counterfactual fairness audit
    """
    resume_name = Path(resume_path).name if resume_path else "Direct Text"
    print(f"\n{'='*55}")
    print(f"Screening: {resume_name}")

    # Step 1: Parse
    print("[1/5] Parsing documents...")
    resume_text = parse_resume(resume_path)
    jd_text_clean = parse_jd(jd_text)

    # Step 2: Extract (Pass 1)
    print("[2/5] Extracting structured fields...")
    resume_data = extract_resume(resume_text)
    jd_data = extract_jd(jd_text_clean)

    # Step 3: Normalize JD via RAG
    print("[3/5] Normalizing JD against templates...")
    try:
        jd_normalized = normalize_jd(jd_text_clean)
        jd_data["normalized_template"] = jd_normalized
    except Exception as e:
        jd_normalized = None

    # Step 4: Score with confidence (Pass 2)
    print("[4/5] Scoring candidate...")
    score_result = score_with_confidence(
        resume_data,
        jd_data,
        jd_normalized,
        resume_text=resume_text
    )

    # Step 5: Decision (Phase 7 Policy)
    print("[5/5] Making decision...")
    decision = make_decision(score_result, jd_data)

    result = {
        "resume_file":   resume_name,
        "resume_path":   str(resume_path),
        "resume_data":   resume_data,
        "jd_data":       jd_data,
        "jd_normalized": jd_normalized,
        "score_result":  score_result,
        "decision":      decision
    }

    # Optional Step 6: Fairness Audit (Phase 8)
    if run_fairness:
        print("[Fairness] Running counterfactual fairness audit...")
        orig_score = score_result.get("score", 0)

        def _variant_scorer(var_text: str) -> int:
            var_data = extract_resume(var_text)
            var_score_res = score_with_confidence(var_data, jd_data, jd_normalized, resume_text=var_text)
            return var_score_res.get("score", orig_score)

        cand_name = resume_data.get("name")
        cand_col = resume_data.get("education", {}).get("institution") if isinstance(resume_data.get("education"), dict) else None
        fairness_res = run_fairness_audit(
            resume_text,
            orig_score,
            _variant_scorer,
            candidate_name=cand_name,
            candidate_college=cand_col
        )
        result["fairness_audit"] = fairness_res
        delta = fairness_res.get("max_delta", 0)
        status = "PASSED (Zero Bias)" if not fairness_res.get("bias_detected") else f"FLAGGED (Delta: {delta} pts)"
        print(f"  Fairness Audit: {status}")

    # Print summary
    print(f"\n  Score:      {decision['score']}/100")
    print(f"  Confidence: {decision['confidence']}")
    print(f"  Decision:   {decision['decision']}")
    print(f"  Reason:     {decision['reason']}")

    return result

def rank_candidates(resume_paths: list, jd_text: str, run_fairness: bool = False) -> list:
    """Screen multiple resumes and return ranked list sorted by score descending."""
    results = []
    for path in resume_paths:
        try:
            r = screen_candidate(str(path), jd_text, run_fairness=run_fairness)
            results.append(r)
        except Exception as e:
            print(f"  [pipeline] Failed for {path}: {e}")

    # Sort by score descending
    results.sort(key=lambda x: x["decision"]["score"], reverse=True)

    print(f"\n{'='*65}")
    print(f"🏆 RANKED SCREENING RESULTS ({len(results)} candidates)")
    print(f"{'='*65}")
    for i, r in enumerate(results, 1):
        d = r["decision"]
        print(f"{i:2}. {r['resume_file'][:30]:30} | "
              f"Score: {d['score']:3}/100 | "
              f"Conf: {d['confidence']:4} | "
              f"Verdict: {d['decision']}")

    return results

if __name__ == "__main__":
    # Sample JD
    JD = """
    Job Title: Backend Software Engineer
    Experience: 2+ years
    Requirements:
    - Required: Python, RESTful APIs, PostgreSQL, Git
    - Preferred: Docker, AWS, FastAPI
    Location: Bangalore, India
    """
    
    # Check for available test resumes
    resumes = list(Path("data/raw_resumes").glob("*.pdf")) + \
              list(Path("data/raw_resumes").glob("*.docx")) + \
              list(Path("data/raw_resumes").glob("*.txt"))
    
    if not resumes:
        # Fallback to sample resume if raw_resumes is empty
        sample_file = Path("data/raw_resumes/sample_resume.txt")
        if sample_file.exists():
            resumes = [sample_file]

    print(f"Found {len(resumes)} resume(s) to process.")
    target_resumes = resumes[:5]
    
    ranked = rank_candidates(target_resumes, JD, run_fairness=False)
    
    # Save results
    output_path = Path("data/golden_eval/pipeline_output.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ranked, f, indent=2, ensure_ascii=False)
    print(f"\n✔ Results successfully saved to {output_path}")
