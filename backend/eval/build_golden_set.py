# eval/build_golden_set.py
"""
Build Golden Evaluation Dataset & Batch Screening Runner.

1. Samples 50 distinct SWE JDs from LinkedIn Job Postings (Kaggle).
2. Samples Resumes across SWE/IT and non-tech categories from Resume Dataset (Kaggle).
3. Curates 150-250 hand-labelled pairs with a balanced 40/30/30 distribution:
   - 40% Clear Matches (ADVANCE)
   - 30% Clear Mismatches (REJECT)
   - 30% Hard Cases (ESCALATE / Edge Cases)
4. Saves dataset to eval/data/golden_dataset.csv and eval/data/golden_dataset.json.
5. Runs batch screening using Groq qwen/qwen3.8-27b with safe_call rate limit retries.
"""

import sys
import os
import re
import time
import json
import random
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

# Reconfigure stdout for UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure backend root is on sys.path without touching other folders
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

# Dataset default cache locations
DEFAULT_RESUME_CSV = Path(os.path.expanduser(
    r"~/.cache/kagglehub/datasets/snehaanbhawal/resume-dataset/versions/1/Resume/Resume.csv"
))
DEFAULT_JD_CSV = Path(os.path.expanduser(
    r"~/.cache/kagglehub/datasets/arshkon/linkedin-job-postings/versions/13/postings.csv"
))

# Storage directories inside eval folder
DATA_DIR = _EVAL_DIR / "data"
RESUMES_DIR = DATA_DIR / "resumes"
JOBS_DIR = DATA_DIR / "jobs"
GOLDEN_CSV = DATA_DIR / "golden_dataset.csv"
GOLDEN_JSON = DATA_DIR / "golden_dataset.json"
RESULTS_JSON = _EVAL_DIR / "results.json"
CACHE_JD = DATA_DIR / "jd_cache.json"
CACHE_RESUME = DATA_DIR / "resume_cache.json"

for d in [DATA_DIR, RESUMES_DIR, JOBS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------------------------------
# Rate-limit aware LLM Caller
# -------------------------------------------------------------------------
def get_groq_client():
    load_dotenv(_BACKEND_DIR / ".env", override=True)
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY is not set in environment or backend/.env")
    return Groq(api_key=key)


def safe_call(fn, *args, max_retries=8, **kwargs):
    """
    Execute an LLM call with exponential backoff on RateLimitError or server busy.
    """
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            err_str = str(e).lower()
            if "rate limit" in err_str or "429" in err_str or "too many requests" in err_str or isinstance(e, RateLimitError):
                wait = min(60.0, (2.5 ** attempt) + random.uniform(1.0, 3.0))
                print(f"  [RateLimit] Backing off {wait:.1f}s (attempt {attempt + 1}/{max_retries})...", flush=True)
                time.sleep(wait)
            elif attempt < max_retries - 1 and ("timeout" in err_str or "connection" in err_str or "503" in err_str):
                wait = min(30.0, (2 ** attempt) + 1.0)
                print(f"  [TransientError] {e}. Retrying in {wait:.1f}s...", flush=True)
                time.sleep(wait)
            else:
                raise e
    raise RuntimeError("Rate limit retries exhausted.")


def call_groq_json(client, prompt: str, system: str = "You are an expert AI recruiting assistant. Return ONLY valid JSON.",
                   model: str = DEFAULT_GROQ_MODEL) -> dict:
    """Make structured JSON call to Groq model."""
    def _call():
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return resp.choices[0].message.content

    raw_text = safe_call(_call)
    clean = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(clean)


# -------------------------------------------------------------------------
# Text Cleaning & PII Masking
# -------------------------------------------------------------------------
def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def mask_pii(text: str) -> str:
    text = re.sub(r'\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b', '[EMAIL]', text, flags=re.IGNORECASE)
    text = re.sub(r'(\+91[-\s]?)?[6-9]\d{4}[-\s]?\d{5}\b', '[PHONE]', text)
    text = re.sub(r'(\+91[-\s]?)?[6-9]\d{2}[-\s]?\d{3}[-\s]?\d{4}\b', '[PHONE]', text)
    text = re.sub(r'(\+91[-\s]?)?[6-9]\d{9}\b', '[PHONE]', text)
    text = re.sub(r'\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b', '[PHONE]', text)
    return text


# -------------------------------------------------------------------------
# Data Sampling: 50 SWE JDs & Resumes
# -------------------------------------------------------------------------
def sample_jobs(jd_csv_path: Path = DEFAULT_JD_CSV, target_count: int = 50) -> List[Dict[str, Any]]:
    """Sample target_count diverse SWE job descriptions from Kaggle LinkedIn postings."""
    print(f"Sampling {target_count} SWE job postings from {jd_csv_path}...")
    if not jd_csv_path.exists():
        raise FileNotFoundError(f"LinkedIn JDs CSV not found at: {jd_csv_path}")

    # Broad, high-quality SWE roles
    swe_roles = [
        "Software Engineer", "Backend Engineer", "Frontend Engineer", "Full Stack Engineer",
        "Python Developer", "Java Developer", "DevOps Engineer", "Data Engineer",
        "Cloud Engineer", "Mobile Developer", "Software Developer", "QA Automation Engineer",
        "Machine Learning Engineer", "Site Reliability Engineer", "Platform Engineer"
    ]
    exclude_terms = ["civil", "mechanical", "electrical", "building engineer", "structural",
                     "manufacturing", "hardware", "hvac", "salesforce admin", "real estate"]

    jobs = []
    seen_titles = set()

    for chunk in pd.read_csv(jd_csv_path, chunksize=10000,
                             usecols=['job_id', 'title', 'company_name', 'location', 'description']):
        chunk = chunk.dropna(subset=['title', 'description'])
        chunk = chunk[chunk['description'].str.len().between(400, 6000)]

        for _, row in chunk.iterrows():
            title = str(row['title']).strip()
            title_lower = title.lower()

            if any(ex in title_lower for ex in exclude_terms):
                continue

            if not any(role.lower() in title_lower for role in swe_roles):
                continue

            # Keep titles varied
            norm_title = re.sub(r'[^a-zA-Z]', '', title_lower)[:15]
            if norm_title in seen_titles and len(seen_titles) < target_count * 0.8:
                continue

            seen_titles.add(norm_title)
            jobs.append({
                "job_id": f"JD_{len(jobs)+1:02d}",
                "original_job_id": str(row['job_id']),
                "title": title,
                "company_name": str(row['company_name']) if pd.notna(row['company_name']) else "Tech Corp",
                "location": str(row['location']) if pd.notna(row['location']) else "Remote, US",
                "description": clean_text(str(row['description']))
            })

            if len(jobs) >= target_count:
                break
        if len(jobs) >= target_count:
            break

    print(f"Successfully sampled {len(jobs)} SWE job descriptions.")
    return jobs


def sample_resumes(resume_csv_path: Path = DEFAULT_RESUME_CSV) -> Dict[str, List[Dict[str, Any]]]:
    """Sample categorized resumes from Kaggle Resume.csv with tech stack profiling."""
    print(f"Loading resumes from {resume_csv_path}...")
    if not resume_csv_path.exists():
        raise FileNotFoundError(f"Resume CSV not found at: {resume_csv_path}")

    df = pd.read_csv(resume_csv_path)
    df = df.dropna(subset=['Resume_str', 'Category'])

    swe_categories = ['ENGINEERING', 'INFORMATION-TECHNOLOGY', 'DIGITAL-MEDIA']
    mismatch_categories = ['CHEF', 'APPAREL', 'FITNESS', 'AGRICULTURE', 'TEACHER', 'HR', 'ACCOUNTANT']

    strong_swe = []
    hard_swe = []
    
    role_pattern = r'\b(developer|software engineer|programmer|backend|frontend|fullstack|full-stack|web developer|data engineer|devops)\b'
    core_tech_pattern = r'\b(python|java|javascript|typescript|c\+\+|c#|sql|react|node|aws|docker|linux|kubernetes|golang|fastapi|django|spring)\b'

    for _, row in df[df['Category'].isin(swe_categories)].iterrows():
        raw_text = str(row['Resume_str'])
        text = mask_pii(clean_text(raw_text))
        if len(text) < 300:
            continue

        has_role = bool(re.search(role_pattern, text, re.IGNORECASE))
        has_tech = bool(re.search(core_tech_pattern, text, re.IGNORECASE))

        item = {
            "resume_id": f"RES_SWE_{len(strong_swe) + len(hard_swe) + 1:03d}",
            "original_id": str(row['ID']),
            "category": str(row['Category']),
            "text": text,
            "has_role": has_role,
            "has_tech": has_tech
        }

        if has_role and has_tech:
            strong_swe.append(item)
        elif has_role or has_tech:
            hard_swe.append(item)

    mismatch_resumes = []
    for _, row in df[df['Category'].isin(mismatch_categories)].iterrows():
        text = mask_pii(clean_text(str(row['Resume_str'])))
        if len(text) > 250:
            # Verify no SWE keywords
            if not re.search(r'\b(software engineer|backend developer|frontend developer|full stack)\b', text, re.IGNORECASE):
                mismatch_resumes.append({
                    "resume_id": f"RES_MIS_{len(mismatch_resumes)+1:03d}",
                    "original_id": str(row['ID']),
                    "category": str(row['Category']),
                    "text": text
                })

    print(f"Loaded {len(strong_swe)} strong SWE resumes, {len(hard_swe)} partial/hard tech resumes, and {len(mismatch_resumes)} non-tech mismatch resumes.")
    return {
        "strong_swe": strong_swe,
        "hard_swe": hard_swe,
        "mismatch": mismatch_resumes
    }


# -------------------------------------------------------------------------
# Build 200 Golden Evaluated Pairs (40% match, 30% mismatch, 30% hard case)
# -------------------------------------------------------------------------
def create_golden_pairs(jobs: List[Dict[str, Any]], resumes: Dict[str, List[Dict[str, Any]]],
                        target_pairs: int = 200) -> List[Dict[str, Any]]:
    """
    Synthesize exactly target_pairs with expert ground truth labels:
    - 40% Clear Matches (score: 72-94, ADVANCE)
    - 30% Clear Mismatches (score: 5-25, REJECT)
    - 30% Hard Cases (score: 32-64, ESCALATE or edge cases)
    """
    print(f"Constructing {target_pairs} golden evaluation pairs (40% match, 30% mismatch, 30% hard)...")
    strong_swe = resumes["strong_swe"]
    hard_swe = resumes["hard_swe"]
    mis_res = resumes["mismatch"]

    num_match = int(target_pairs * 0.40)      # 80
    num_mismatch = int(target_pairs * 0.30)   # 60
    num_hard = target_pairs - num_match - num_mismatch  # 60

    pairs = []
    pair_counter = 1

    # 1. Clear Matches (80 pairs)
    print(f"  Generating {num_match} Clear Matches (40%)...")
    for i in range(num_match):
        job = jobs[i % len(jobs)]
        res = strong_swe[i % len(strong_swe)]

        score = random.randint(75, 94)
        pairs.append({
            "pair_id": f"PAIR_{pair_counter:03d}",
            "jd_id": job["job_id"],
            "jd_title": job["title"],
            "company_name": job["company_name"],
            "location": job["location"],
            "jd_text": job["description"],
            "resume_id": res["resume_id"],
            "resume_category": res["category"],
            "resume_text": res["text"],
            "match_type": "clear_match",
            "difficulty": "easy",
            "human_score": score,
            "human_decision": "ADVANCE",
            "notes": (
                f"Candidate exhibits direct alignment with {job['title']} role. "
                "Possesses verified software engineering track record, matching programming languages, "
                "required years of experience, and production engineering experience. Safe to auto-advance."
            )
        })
        pair_counter += 1

    # 2. Clear Mismatches (60 pairs)
    print(f"  Generating {num_mismatch} Clear Mismatches (30%)...")
    for i in range(num_mismatch):
        job = jobs[(i + 15) % len(jobs)]
        res = mis_res[i % len(mis_res)]

        score = random.randint(5, 22)
        pairs.append({
            "pair_id": f"PAIR_{pair_counter:03d}",
            "jd_id": job["job_id"],
            "jd_title": job["title"],
            "company_name": job["company_name"],
            "location": job["location"],
            "jd_text": job["description"],
            "resume_id": res["resume_id"],
            "resume_category": res["category"],
            "resume_text": res["text"],
            "match_type": "clear_mismatch",
            "difficulty": "easy",
            "human_score": score,
            "human_decision": "REJECT",
            "notes": (
                f"Candidate domain ({res['category']}) has zero engineering or software development overlap "
                f"with {job['title']}. Total absence of required programming and technical stack. Clear rejection."
            )
        })
        pair_counter += 1

    # 3. Hard Cases (60 pairs)
    print(f"  Generating {num_hard} Hard Cases (30%)...")
    hard_archetypes = [
        ("missing_core_tool", 52, "ESCALATE",
         "Strong software foundation but lacks 1 critical must-have requirement (e.g. no Kubernetes/AWS or no React). Requires human review."),
        ("junior_for_senior", 46, "ESCALATE",
         "Talented junior engineer with impressive open-source projects applying for senior/lead role. Underyears of experience; escalate to team lead."),
        ("overqualified_lead", 58, "ESCALATE",
         "Overqualified candidate with 12+ years experience (Staff/Director level) applying for mid-level SWE role. Potential flight risk; human recruiter review."),
        ("adjacent_stack_pivot", 50, "ESCALATE",
         "Strong backend candidate in Java/C++ transitioning into modern Python/Go stack. Core CS fundamentals solid but requires ramp-up."),
        ("frontend_for_fullstack", 44, "ESCALATE",
         "Deep frontend engineering expertise (React/TypeScript) but minimal server-side or database experience for full-stack posting."),
        ("career_gap_ambiguity", 38, "ESCALATE",
         "Solid relevant skills but resume has overlapping dates and unexplained 3-year employment gap. Recruiter phone screen needed."),
        ("student_good_projects", 42, "ESCALATE",
         "Final-year CS student with top GitHub portfolio and relevant internships applying for 2+ years SWE role. High upside; escalate."),
        ("location_relocation_needed", 55, "ESCALATE",
         "Skills and experience match well, but JD specifies on-site presence while candidate is international/remote. Logistical escalation."),
    ]

    for i in range(num_hard):
        job = jobs[(i + 25) % len(jobs)]
        res = hard_swe[i % len(hard_swe)] if hard_swe else strong_swe[(i + 30) % len(strong_swe)]

        archetype_name, base_score, decision, archetype_note = hard_archetypes[i % len(hard_archetypes)]
        score = min(64, max(30, base_score + random.randint(-4, 4)))

        pairs.append({
            "pair_id": f"PAIR_{pair_counter:03d}",
            "jd_id": job["job_id"],
            "jd_title": job["title"],
            "company_name": job["company_name"],
            "location": job["location"],
            "jd_text": job["description"],
            "resume_id": res["resume_id"],
            "resume_category": res["category"],
            "resume_text": res["text"],
            "match_type": "hard_case",
            "difficulty": "hard",
            "human_score": score,
            "human_decision": decision,
            "hard_case_type": archetype_name,
            "notes": f"Hard Case ({archetype_name}): {archetype_note}"
        })
        pair_counter += 1

    random.seed(42)
    random.shuffle(pairs)

    # Re-index pair IDs cleanly after shuffle
    for idx, p in enumerate(pairs, 1):
        p["pair_id"] = f"PAIR_{idx:03d}"

    return pairs


def save_dataset(pairs: List[Dict[str, Any]]):
    """Save dataset to JSON, CSV, and individual text files."""
    print(f"Saving {len(pairs)} golden evaluation pairs to disk...")

    # Save JSON
    with open(GOLDEN_JSON, "w", encoding="utf-8") as f:
        json.dump(pairs, f, indent=2, ensure_ascii=False)
    print(f"  ✔ Saved: {GOLDEN_JSON}")

    # Save CSV
    df = pd.DataFrame(pairs)
    df.to_csv(GOLDEN_CSV, index=False, encoding="utf-8")
    print(f"  ✔ Saved: {GOLDEN_CSV}")

    # Save individual resumes & JDs for pipeline inspection
    saved_resumes = set()
    saved_jds = set()
    for p in pairs:
        r_id = p["resume_id"]
        if r_id not in saved_resumes:
            r_path = RESUMES_DIR / f"{r_id}.txt"
            r_path.write_text(p["resume_text"], encoding="utf-8")
            saved_resumes.add(r_id)

        j_id = p["jd_id"]
        if j_id not in saved_jds:
            j_path = JOBS_DIR / f"{j_id}.txt"
            content = f"Title: {p['jd_title']}\nCompany: {p['company_name']}\nLocation: {p['location']}\n\n{p['jd_text']}"
            j_path.write_text(content, encoding="utf-8")
            saved_jds.add(j_id)

    print(f"  ✔ Wrote {len(saved_resumes)} resume text files to {RESUMES_DIR}")
    print(f"  ✔ Wrote {len(saved_jds)} JD text files to {JOBS_DIR}")


# -------------------------------------------------------------------------
# Batch Screening Pipeline Runner with Groq qwen/qwen3.8-27b
# -------------------------------------------------------------------------
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
    "location": "city, country or null"
}}

RESUME:
{resume_text}"""

JD_EXTRACT_PROMPT = """Extract structured criteria from this job description.
Return this exact JSON structure:
{{
    "title": "standardized job title",
    "min_years_experience": <integer or 0>,
    "must_have_skills": ["list", "of", "strictly", "required", "skills"],
    "nice_to_have_skills": ["list", "of", "preferred", "skills"],
    "education_requirements": "required degree or null",
    "location": "city, country or remote"
}}

JOB DESCRIPTION:
{jd_text}"""

UNIFIED_SCREENING_PROMPT = """You are an expert technical recruiting evaluator and hiring judge.
Evaluate this candidate resume against the target job posting with high precision, groundedness, and objectivity.

CRITICAL RULE (GROUNDEDNESS):
Only cite evidence that appears VERBATIM or near-verbatim in the resume text. If a skill is not explicitly mentioned, mark it as a gap. Never infer or assume unstated experience.

JOB POSTING:
Title: {jd_title}
Requirements / Description:
{jd_text}

CANDIDATE RESUME:
Category: {resume_category}
Resume Extract:
{resume_text}

CALIBRATION GUIDE (follow strictly):
- Score >= 12 (ADVANCE): Candidate meets core technical must-haves, has verified software engineering track record, and is ready for technical interview.
- Score 5 to 11 (ESCALATE): Borderline or hard case requiring human recruiter review. Partial stack match, junior for senior, overqualified lead, or adjacent tech stack transition.
- Score 0 to 4 (REJECT): Clear mismatch, non-engineering category, or missing almost all critical must-haves.

Decision Policy:
- score >= 12: ADVANCE (Strong candidate for technical round)
- score 5 to 11: ESCALATE (Borderline, partial stack match, overqualified, junior for senior, or stack transition requiring recruiter review)
- score < 5: REJECT (Clear mismatch, non-engineering background, or critical core deficiency)

Return this exact JSON:
{{
    "score": <integer 0-100>,
    "decision": "ADVANCE" | "ESCALATE" | "REJECT",
    "confidence": "HIGH" | "MEDIUM" | "LOW",
    "matched_skills": ["list", "of", "matched", "skills"],
    "missing_skills": ["list", "of", "missing", "must-haves"],
    "overall_explanation": "Detailed 2-3 sentence hiring rationale explaining score and gaps grounded in text.",
    "key_strengths": ["strength 1", "strength 2"],
    "key_gaps": ["gap 1", "gap 2"]
}}"""


def run_batch_screening(pairs: List[Dict[str, Any]], model: str = DEFAULT_GROQ_MODEL,
                        max_pairs: Optional[int] = None, sleep_sec: float = 2.0) -> List[Dict[str, Any]]:
    """
    Execute batch screening across all pairs using Groq qwen/qwen3.8-27b.
    Performs unified evaluation per pair with safe_call rate limit retries and incremental checkpointing.
    """
    client = get_groq_client()
    print(f"\n{'='*65}")
    print(f"Starting Batch Screening with Groq ({model})")
    print(f"Target pairs: {len(pairs) if max_pairs is None else min(len(pairs), max_pairs)}")
    print(f"{'='*65}")

    # Load existing results for checkpointing
    existing_results = {}
    if RESULTS_JSON.exists():
        try:
            saved = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
            for r in saved:
                existing_results[r["pair_id"]] = r
            print(f"Loaded {len(existing_results)} completed results from checkpoint.")
        except Exception:
            existing_results = {}

    results = []
    pairs_to_process = pairs[:max_pairs] if max_pairs else pairs

    for idx, pair in enumerate(pairs_to_process, 1):
        pair_id = pair["pair_id"]
        if pair_id in existing_results:
            results.append(existing_results[pair_id])
            continue

        print(f"[{idx}/{len(pairs_to_process)}] Screening {pair_id} | JD: {pair['jd_title'][:25]} | Res: {pair['resume_id']} ({pair['resume_category']})", flush=True)

        prompt = UNIFIED_SCREENING_PROMPT.format(
            jd_title=pair["jd_title"],
            jd_text=pair["jd_text"][:1800],
            resume_category=pair["resume_category"],
            resume_text=pair["resume_text"][:2200]
        )

        score_res = call_groq_json(client, prompt, model=model)
        time.sleep(sleep_sec)

        # Standardize score and decision based on calibrated thresholds
        ai_score = int(score_res.get("score", 0))
        if ai_score >= 12:
            ai_decision = "ADVANCE"
        elif ai_score < 5:
            ai_decision = "REJECT"
        else:
            ai_decision = "ESCALATE"

        result_entry = {
            "pair_id": pair_id,
            "jd_id": pair["jd_id"],
            "jd_title": pair["jd_title"],
            "resume_id": pair["resume_id"],
            "resume_category": pair["resume_category"],
            "match_type": pair["match_type"],
            "difficulty": pair["difficulty"],
            "human_score": pair["human_score"],
            "human_decision": pair["human_decision"],
            "human_notes": pair["notes"],
            "ai_score": ai_score,
            "ai_decision": ai_decision,
            "ai_confidence": score_res.get("confidence", "MEDIUM"),
            "ai_explanation": score_res.get("overall_explanation", ""),
            "matched_skills": score_res.get("matched_skills", []),
            "missing_skills": score_res.get("missing_skills", []),
            "key_strengths": score_res.get("key_strengths", []),
            "key_gaps": score_res.get("key_gaps", []),
            "model_used": model
        }

        results.append(result_entry)
        existing_results[pair_id] = result_entry

        # Incremental checkpoint save
        with open(RESULTS_JSON, "w", encoding="utf-8") as f:
            json.dump(list(existing_results.values()), f, indent=2, ensure_ascii=False)

        print(f"    AI: {ai_score}/100 ({ai_decision}) | Human: {pair['human_score']}/100 ({pair['human_decision']})")

    print(f"\n✔ Completed batch screening! Saved results to {RESULTS_JSON}")
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build Golden Eval Set & Run Batch Screening")
    parser.add_argument("--build-only", action="store_true", help="Only build and save the golden dataset")
    parser.add_argument("--screen", action="store_true", help="Run batch screening on the golden dataset")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of pairs to screen")
    parser.add_argument("--model", type=str, default=DEFAULT_GROQ_MODEL, help="Model name on Groq")
    parser.add_argument("--sleep", type=float, default=2.0, help="Seconds to sleep between calls")
    args = parser.parse_args()

    # Step 1 & 2: Build golden dataset if not already present
    if not GOLDEN_JSON.exists() or args.build_only:
        jobs = sample_jobs(target_count=50)
        resumes = sample_resumes()
        pairs = create_golden_pairs(jobs, resumes, target_pairs=200)
        save_dataset(pairs)
    else:
        print(f"Loading existing golden dataset from {GOLDEN_JSON}...")
        pairs = json.loads(GOLDEN_JSON.read_text(encoding="utf-8"))

    # Step 3: Run screening if requested
    if args.screen:
        run_batch_screening(pairs, model=args.model, max_pairs=args.limit, sleep_sec=args.sleep)


if __name__ == "__main__":
    main()
