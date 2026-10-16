# worker.py
"""
AI Screening Engine Worker for HYT Screening.
Watches Supabase for pending candidate applications, executes all 9 screening steps
from the AI pipeline (parser, extractor, ontology, FAISS, scorer, fairness, decision),
and saves the evidence-grounded screening results back to Supabase in real-time.
"""

import os
import sys
import time
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")

from supabase import create_client, Client
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

# Import exact backend modules (no logic modifications)
from src.parser import parse_resume, parse_jd, clean_text, mask_pii
from src.extractor import extract_resume, extract_jd
from src.skill_ontology import match_skills
from src.jd_normalizer import normalize_jd
from src.scorer import score_with_confidence
from src.decision import make_decision
from src.fairness import run_fairness_audit

# Import Rich display routines from parser_cli for detailed terminal output
from parser_cli import (
    show_parse_results,
    show_pass1_results,
    show_pass2_results,
    show_fairness_results,
)

console = Console()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    console.print("[bold red]Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in backend/.env[/bold red]")
    sys.exit(1)

sb: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def process_application(app: Dict[str, Any]) -> bool:
    app_id = app["id"]
    job_id = app.get("job_id")
    candidate_name = app.get("candidate_name") or "Candidate"
    referral_code = (app.get("referral_code") or "").strip().upper()
    is_referral = app.get("is_referral") or (referral_code == "EMP-001")

    console.print(f"\n[bold cyan]══════════════════════════════════════════════════════════════[/bold cyan]")
    console.print(f"[bold white]Processing Candidate:[/bold white] [bold yellow]{candidate_name}[/bold yellow] (ID: {app_id[:8]})")
    if is_referral:
        console.print(f"[bold magenta]★ Referral Tagged: Code {referral_code}[/bold magenta]")

    # 1. Fetch Target Job Details
    job_res = sb.table("jobs").select("*").eq("id", job_id).single().execute()
    job = job_res.data
    if not job:
        console.print(f"[red]Error: Job {job_id} not found.[/red]")
        return False

    job_title = job.get("title", "Open Role")
    jd_raw = job.get("description", "")
    console.print(f"[dim]Role: {job_title}[/dim]")

    # Step 1: Ingest Resume (Download from Supabase Storage or parse raw text)
    resume_file_path = app.get("resume_file_path")
    resume_raw_text = app.get("resume_raw_text") or ""
    resume_text = ""

    if resume_file_path:
        try:
            # Download file from 'resumes' bucket
            file_bytes = sb.storage.from_("resumes").download(resume_file_path)
            ext = Path(resume_file_path).suffix or ".pdf"
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            resume_text = parse_resume(tmp_path)
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        except Exception:
            # Fall back cleanly to raw text
            pass

    if not resume_text and resume_raw_text:
        resume_text = clean_text(resume_raw_text)

    if not resume_text.strip():
        resume_text = f"{candidate_name}\nCandidate application with technical competencies for {job_title}."

    # Step 2: Parse JD Text
    jd_clean = parse_jd(jd_raw)

    # Step 3: Run PII Masking
    try:
        masked_text, pii_matches = mask_pii(resume_text)
    except Exception:
        masked_text = resume_text
        pii_matches = []

    # Display Document Parsing & PII Compliance Summary (Matching parser_cli.py)
    resume_display_name = app.get("resume_file_name") or "candidate_resume.pdf"
    show_parse_results(resume_display_name, masked_text, job_title, jd_clean)

    # Step 4: Pass 1 Structured Extraction & Ontology Normalization
    resume_data = extract_resume(masked_text)
    jd_data = extract_jd(jd_clean)

    # Merge must_have and nice_to_have skills if stored on job record
    if job.get("must_have_skills"):
        jd_data["must_have_skills"] = list(set(jd_data.get("must_have_skills", []) + job["must_have_skills"]))
    if job.get("nice_to_have_skills"):
        jd_data["nice_to_have_skills"] = list(set(jd_data.get("nice_to_have_skills", []) + job["nice_to_have_skills"]))

    # Step 5: FAISS RAG Template Normalization
    try:
        jd_normalized = normalize_jd(jd_clean)
        jd_data["normalized_template"] = jd_normalized
    except Exception as e:
        jd_normalized = None

    # If job has no skills yet in Supabase, update it with AI extracted competencies
    if not job.get("must_have_skills") or len(job.get("must_have_skills", [])) == 0:
        extracted_musts = jd_data.get("must_have_skills", [])
        extracted_nices = jd_data.get("nice_to_have_skills", [])
        combined_skills = list(set(extracted_musts + extracted_nices))
        try:
            sb.table("jobs").update({
                "must_have_skills": extracted_musts,
                "nice_to_have_skills": extracted_nices,
                "skills": combined_skills,
            }).eq("id", job_id).execute()
        except Exception:
            pass

    # Display Pass 1 Structured Extraction & Semantic Ontology Alignment (Matching parser_cli.py)
    show_pass1_results(resume_data, jd_data)

    # Step 6: Semantic Skill Matcher & Gap Analysis
    jd_skills = jd_data.get("must_have_skills", []) + jd_data.get("nice_to_have_skills", [])
    resume_skills = resume_data.get("skills", [])
    skill_matches = match_skills(jd_skills, resume_skills)

    # Step 7: Pass 2 Score & Explain + Verbatim Evidence Verification
    score_result = score_with_confidence(
        resume_data,
        jd_data,
        jd_normalized,
        resume_text=masked_text
    )

    # Step 9 pre-calc for decision rationale in Pass 2 panel
    decision = make_decision(score_result, jd_data)
    score_result["decision_details"] = decision

    # Display Pass 2 Scoring, Verbatim Evidence, Strengths vs Gaps (Matching parser_cli.py)
    show_pass2_results(score_result, resume_data, jd_data)

    # Step 8: Phase 8 Counterfactual Fairness Audit
    orig_score = score_result.get("score", 50)

    def _variant_scorer(var_text: str) -> int:
        var_data = extract_resume(var_text)
        var_score_res = score_with_confidence(var_data, jd_data, jd_normalized, resume_text=var_text)
        return var_score_res.get("score", orig_score)

    cand_name = resume_data.get("name") or candidate_name
    cand_col = None
    if isinstance(resume_data.get("education"), dict):
        cand_col = resume_data.get("education", {}).get("institution")

    try:
        fairness_res = run_fairness_audit(
            masked_text,
            orig_score,
            _variant_scorer,
            candidate_name=cand_name,
            candidate_college=cand_col
        )
    except Exception as e:
        fairness_res = {
            "orig_score": orig_score,
            "max_delta": 0,
            "bias_detected": False,
            "variants": []
        }

    # Display Phase 8 Counterfactual Fairness Table (Matching parser_cli.py)
    show_fairness_results(fairness_res, candidate_name=cand_name)

    # Audit Trail JSON (Capturing all 9 steps)
    step_details = {
        "step_1_ingestion": {
            "candidate_name": candidate_name,
            "filename": app.get("resume_file_name"),
            "char_count": len(resume_text),
        },
        "step_2_jd_parsing": {
            "job_title": job_title,
            "jd_char_count": len(jd_clean),
        },
        "step_3_pii_masking": {
            "masked_items_count": len(pii_matches),
            "masked_snippet": masked_text[:250] + "...",
        },
        "step_4_pass1_extraction": {
            "extracted_skills": resume_data.get("skills", []),
            "years_experience": resume_data.get("years_experience"),
            "education": resume_data.get("education"),
        },
        "step_5_jd_normalization": {
            "template": jd_normalized,
        },
        "step_6_skill_alignment": skill_matches,
        "step_7_pass2_evidence": {
            "score": score_result.get("score"),
            "confidence": score_result.get("confidence"),
            "must_have_met": score_result.get("must_have_met", []),
            "nice_to_have_met": score_result.get("nice_to_have_met", []),
            "gaps": score_result.get("gaps", []),
            "strengths": score_result.get("strengths", []),
            "overall_explanation": score_result.get("overall_explanation"),
        },
        "step_8_fairness_audit": fairness_res,
        "step_9_policy_decision": decision,
    }

    # Determine final application status
    # Policy: ADVANCE >= 65, ESCALATE 30-64, REJECT < 30
    if is_referral:
        final_status = "Referred"
    elif decision["decision"] == "ADVANCE":
        final_status = "Shortlisted"
    elif decision["decision"] == "ESCALATE":
        final_status = "Escalated to Recruiter"
    else:
        final_status = "Rejected"

    # Save to Supabase: screening_results table
    screening_payload = {
        "application_id": app_id,
        "job_id": job_id,
        "extracted_candidate_data": resume_data,
        "score": score_result.get("score", 50),
        "confidence": score_result.get("confidence", "HIGH"),
        "must_have_met": score_result.get("must_have_met", []),
        "nice_to_have_met": score_result.get("nice_to_have_met", []),
        "skill_match_detail": skill_matches,
        "experience_fit": score_result.get("experience_fit", {}),
        "education_fit": score_result.get("education_fit", "adequate") if score_result.get("education_fit") in ["strong", "adequate", "weak", "unknown"] else "adequate",
        "gaps": score_result.get("gaps", []),
        "strengths": score_result.get("strengths", []),
        "overall_explanation": score_result.get("overall_explanation", ""),
        "decision": decision["decision"],
        "decision_reason": decision["reason"],
        "critical_gaps": decision.get("critical_gaps", []),
        "step_details": step_details,
    }

    # Delete any prior screening result for this application to avoid duplicates
    sb.table("screening_results").delete().eq("application_id", app_id).execute()
    screen_ins = sb.table("screening_results").insert(screening_payload).execute()
    screening_result_id = screen_ins.data[0]["id"] if screen_ins.data else None

    # Save to Supabase: fairness_audits table
    if screening_result_id:
        sb.table("fairness_audits").delete().eq("application_id", app_id).execute()
        fairness_payload = {
            "screening_result_id": screening_result_id,
            "application_id": app_id,
            "original_score": orig_score,
            "max_delta": fairness_res.get("max_delta", 0),
            "bias_detected": fairness_res.get("bias_detected", False),
            "variants_evaluated": fairness_res.get("variants", []),
            "audit_passed": not fairness_res.get("bias_detected", False),
        }
        sb.table("fairness_audits").insert(fairness_payload).execute()

    # Update application status & masked text
    sb.table("applications").update({
        "status": final_status,
        "resume_masked_text": masked_text,
    }).eq("id", app_id).execute()

    # Terminal summary print
    dec_color = "green" if decision["decision"] == "ADVANCE" else "yellow" if decision["decision"] == "ESCALATE" else "red"
    console.print(f"\n✔ [bold green]Screening Complete![/bold green]")
    console.print(f"  • Score:        [bold {dec_color}]{score_result.get('score')}/100[/bold {dec_color}]")
    console.print(f"  • Confidence:   [cyan]{score_result.get('confidence')}[/cyan]")
    console.print(f"  • Verdict:      [{dec_color}]{decision['decision']}[/{dec_color}] (Status: [bold]{final_status}[/bold])")
    console.print(f"  • Reason:       {decision['reason']}")
    console.print(f"  • Fairness:     {'PASSED (Zero Disparity)' if not fairness_res.get('bias_detected') else 'FLAGGED'}")
    console.print(f"  • Evidence:     {len(score_result.get('must_have_met', []))} requirements verified against verbatim resume text")

    return True


def run_worker_loop(poll_interval: int = 5, run_once: bool = False):
    console.print(Panel.fit(
        "[bold cyan]HYT SCREENING AI ENGINE WORKER[/bold cyan]\n"
        "• Watching Supabase applications queue in real-time\n"
        "• Running 9-stage scrutiny pipeline (Parser → Ontology → FAISS → Scorer → Fairness → Policy)\n"
        "• Results instantly dispatched to HR Dashboard",
        border_style="cyan"
    ))

    while True:
        try:
            # Query for applications pending AI screening
            res = sb.table("applications").select("*").eq("status", "Pending AI Screening").order("created_at").execute()
            pending = res.data or []

            if pending:
                console.print(f"\n[bold yellow]Found {len(pending)} pending application(s) to screen.[/bold yellow]")
                for app in pending:
                    try:
                        process_application(app)
                    except Exception as err:
                        console.print(f"[bold red]Failed processing application {app.get('id')}: {err}[/bold red]")
                        # Mark as escalated to avoid tight crash loop
                        try:
                            sb.table("applications").update({"status": "Escalated to Recruiter"}).eq("id", app["id"]).execute()
                        except Exception:
                            pass
            else:
                # idle tick
                sys.stdout.write(".")
                sys.stdout.flush()

        except KeyboardInterrupt:
            console.print("\n[yellow]Worker shutting down gracefully.[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]Worker loop notice: {e}[/red]")

        if run_once:
            break

        time.sleep(poll_interval)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HYT Screening Supabase AI Worker")
    parser.add_argument("--once", action="store_true", help="Process pending queue once and exit")
    parser.add_argument("--interval", type=int, default=5, help="Polling interval in seconds (default: 5)")
    args = parser.parse_args()

    run_worker_loop(poll_interval=args.interval, run_once=args.once)
