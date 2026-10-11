import os
import sys
import json
from pathlib import Path

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

import tkinter as tk
from tkinter import filedialog
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.markup import escape
from rich.json import JSON
from rich import box

# Import parser functions
from src.parser import (
    parse_resume,
    parse_jd,
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_txt,
    clean_text,
    mask_pii,
)

# Import Pass 1 extractor & ontology functions
from src.extractor import extract_resume, extract_jd
from src.skill_ontology import normalize_skill, match_skills, get_skill_category
from src.jd_normalizer import normalize_jd

console = Console()

def open_file_dialog(title: str, filetypes: list) -> str:
    """Opens a native OS file picker window to select/upload a file."""
    try:
        root = tk.Tk()
        root.withdraw()  # Hide root window
        root.attributes("-topmost", True)  # Bring file dialog to front
        selected_file = filedialog.askopenfilename(title=title, filetypes=filetypes)
        root.destroy()
        return selected_file
    except Exception as e:
        console.print(f"[yellow]Notice: Native file picker unavailable ({e}). Falling back to text prompt.[/yellow]")
        return ""

def display_banner():
    banner_text = Text()
    banner_text.append("HYT SCREENING ", style="bold cyan")
    banner_text.append("— Resume & Job Description Studio\n", style="bold white")
    banner_text.append("• Document Ingestion & PII Masking (PDF, DOCX, TXT)\n", style="dim")
    banner_text.append("• Pass 1: Structured Extraction (Gemini 2.0 Flash)\n", style="cyan")
    banner_text.append("• Semantic Skill Ontology & Normalization (38 Technical Domains)", style="dim")
    console.print(Panel(banner_text, box=box.ROUNDED, border_style="cyan"))

def show_parse_results(resume_path: str, resume_parsed_text: str, jd_input: str, jd_parsed_text: str):
    """Displays raw parsed text and PII masking results."""
    console.print("\n")
    
    # Summary Table
    table = Table(title="📊 Parsing Summary", box=box.ROUNDED, header_style="bold magenta")
    table.add_column("Document", style="cyan", no_wrap=True)
    table.add_column("Source / File", style="white")
    table.add_column("Characters", justify="right", style="green")
    table.add_column("Words", justify="right", style="green")
    table.add_column("PII Masked Count", justify="right", style="yellow")

    resume_pii_count = (
        resume_parsed_text.count("[EMAIL]") + resume_parsed_text.count("[PHONE]")
        if resume_parsed_text
        else 0
    )
    table.add_row(
        "📄 Resume",
        Path(resume_path).name if resume_path else "None",
        str(len(resume_parsed_text)) if resume_parsed_text else "0",
        str(len(resume_parsed_text.split())) if resume_parsed_text else "0",
        str(resume_pii_count),
    )

    jd_source_name = Path(jd_input).name if Path(jd_input).exists() else "Direct Text Input"
    table.add_row(
        "📋 Job Description",
        jd_source_name if jd_input else "None",
        str(len(jd_parsed_text)) if jd_parsed_text else "0",
        str(len(jd_parsed_text.split())) if jd_parsed_text else "0",
        "N/A",
    )
    console.print(table)

    # Resume Parsed Content Panel
    if resume_parsed_text:
        console.print("\n")
        safe_resume_name = escape(Path(resume_path).name if resume_path else "")
        resume_header = f"📄 RESUME PARSED OUTPUT ({safe_resume_name}) [PII MASKED]"
        console.print(
            Panel(
                Text(resume_parsed_text),
                title=f"[bold green]{resume_header}[/bold green]",
                subtitle="[dim]Verified with PDF/DOCX/TXT Parser + Privacy Compliance[/dim]",
                border_style="green",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

    # JD Parsed Content Panel
    if jd_parsed_text:
        console.print("\n")
        safe_jd_name = escape(Path(jd_input).name if Path(jd_input).exists() else "Direct Input")
        jd_header = f"📋 JOB DESCRIPTION PARSED OUTPUT ({safe_jd_name})"
        console.print(
            Panel(
                Text(jd_parsed_text),
                title=f"[bold blue]{jd_header}[/bold blue]",
                subtitle="[dim]Normalized & Cleaned[/dim]",
                border_style="blue",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

def show_pass1_results(resume_extracted: dict = None, jd_extracted: dict = None):
    """
    Renders structured Pass 1 extraction output (Gemini 2.0 Flash)
    and semantic skill ontology matching in Rich tables & panels.
    """
    console.print("\n")
    console.print(Panel(
        "[bold cyan]🤖 PASS 1: STRUCTURED EXTRACTION & SKILL ONTOLOGY[/bold cyan]\n"
        "[dim]Engine: Gemini 2.0 Flash (Quality Path) | Ontology: 38 Technical Categories[/dim]",
        box=box.DOUBLE,
        border_style="cyan"
    ))

    # --- RESUME EXTRACTION DISPLAY ---
    if resume_extracted:
        console.print("\n")
        res_info = Table(box=box.ROUNDED, header_style="bold green")
        res_info.add_column("Metric / Field", style="bold white", width=22)
        res_info.add_column("Extracted Value", style="white")

        name = resume_extracted.get("name") or "[italic dim]Not specified[/italic dim]"
        loc = resume_extracted.get("location") or "[italic dim]Not specified[/italic dim]"
        exp = resume_extracted.get("years_experience")
        exp_str = f"{exp} years" if exp is not None else "[italic dim]Unclear[/italic dim]"
        if resume_extracted.get("experience_ambiguity"):
            exp_str += " [bold yellow](⚠️ Flagged as Ambiguous)[/bold yellow]"

        res_info.add_row("Candidate Name", str(name))
        res_info.add_row("Location", str(loc))
        res_info.add_row("Total Experience", exp_str)

        # Education
        edu = resume_extracted.get("education") or {}
        edu_parts = [
            edu.get("degree"),
            edu.get("field"),
            edu.get("institution"),
            f"({edu.get('year')})" if edu.get("year") else None,
        ]
        edu_str = ", ".join([str(p) for p in edu_parts if p]) or "[italic dim]None listed[/italic dim]"
        res_info.add_row("Education", edu_str)

        # Certifications & Languages
        certs = resume_extracted.get("certifications") or []
        langs = resume_extracted.get("languages") or []
        res_info.add_row("Certifications", ", ".join(certs) if certs else "[italic dim]None[/italic dim]")
        res_info.add_row("Languages", ", ".join(langs) if langs else "[italic dim]None[/italic dim]")

        console.print(Panel(res_info, title="[bold green]👤 Candidate Profile (Resume Pass 1)[/bold green]", border_style="green", box=box.ROUNDED))

        # Past Roles Table
        roles = resume_extracted.get("past_roles") or []
        if roles:
            roles_table = Table(title="💼 Experience & Role History", box=box.SIMPLE_HEAVY, header_style="bold cyan")
            roles_table.add_column("Title", style="white bold")
            roles_table.add_column("Company", style="cyan")
            roles_table.add_column("Duration", justify="right", style="green")
            for r in roles:
                dur = r.get("duration_years")
                dur_str = f"{dur} yrs" if dur is not None else "[dim]N/A[/dim]"
                roles_table.add_row(r.get("title", "N/A"), r.get("company", "N/A"), dur_str)
            console.print(roles_table)

        # Normalized Skills Table with Ontology Category
        skills = resume_extracted.get("skills") or []
        if skills:
            skills_table = Table(title=f"🛠️ Extracted Skills ({len(skills)} Normalized)", box=box.ROUNDED, header_style="bold magenta")
            skills_table.add_column("#", justify="right", style="dim", width=4)
            skills_table.add_column("Canonical Skill", style="bold green")
            skills_table.add_column("Technical Category", style="yellow")

            for idx, s in enumerate(skills, 1):
                cat = get_skill_category(s) or "general_technical"
                skills_table.add_row(str(idx), s, cat)
            console.print(skills_table)

    # --- JOB DESCRIPTION EXTRACTION DISPLAY ---
    if jd_extracted:
        console.print("\n")
        jd_info = Table(box=box.ROUNDED, header_style="bold blue")
        jd_info.add_column("Field", style="bold white", width=22)
        jd_info.add_column("Extracted Requirement", style="white")

        title = jd_extracted.get("job_title") or "[italic dim]Not specified[/italic dim]"
        company = jd_extracted.get("company") or "[italic dim]Not specified[/italic dim]"
        domain = jd_extracted.get("domain") or "[italic dim]General Tech[/italic dim]"
        min_exp = jd_extracted.get("min_years_experience")
        min_exp_str = f"{min_exp}+ years" if min_exp is not None else "[italic dim]None specified[/italic dim]"
        edu_req = jd_extracted.get("education_required") or "[italic dim]None specified[/italic dim]"
        loc_req = jd_extracted.get("location") or "[italic dim]Not specified[/italic dim]"

        jd_info.add_row("Target Job Title", str(title))
        jd_info.add_row("Hiring Company", str(company))
        jd_info.add_row("Industry Domain", str(domain))
        jd_info.add_row("Min Experience Required", min_exp_str)
        jd_info.add_row("Education Required", str(edu_req))
        jd_info.add_row("Location", str(loc_req))

        norm_template = jd_extracted.get("normalized_template")
        if norm_template:
            matched_role = norm_template.get("matched_role")
            sim = norm_template.get("similarity", 0.0)
            canonical_musts = ", ".join(norm_template.get("canonical_musts", []))
            jd_info.add_row("FAISS Standard Role", f"[bold cyan]{matched_role}[/bold cyan] (similarity: {sim:.2f})")
            if canonical_musts:
                jd_info.add_row("Standard Role Musts", canonical_musts)

        console.print(Panel(jd_info, title="[bold blue]📋 Target Role Profile (JD Pass 1)[/bold blue]", border_style="blue", box=box.ROUNDED))

        # Responsibilities
        resps = jd_extracted.get("responsibilities") or []
        if resps:
            resp_text = "\n".join([f"• {r}" for r in resps])
            console.print(Panel(resp_text, title="[bold blue]🎯 Core Responsibilities[/bold blue]", border_style="blue", box=box.ROUNDED))

        # Must Have vs Nice to Have Skills
        must_skills = jd_extracted.get("must_have_skills") or []
        nice_skills = jd_extracted.get("nice_to_have_skills") or []

        if must_skills or nice_skills:
            req_table = Table(title="📌 Job Skill Requirements (Normalized via Ontology)", box=box.ROUNDED, header_style="bold cyan")
            req_table.add_column("Type", style="bold", width=14)
            req_table.add_column("Canonical Skill", style="bold white")
            req_table.add_column("Taxonomy Category", style="yellow")

            for s in must_skills:
                cat = get_skill_category(s) or "general_technical"
                req_table.add_row("[bold red]Must-Have[/bold red]", s, cat)
            for s in nice_skills:
                cat = get_skill_category(s) or "general_technical"
                req_table.add_row("[bold green]Nice-To-Have[/bold green]", s, cat)

            console.print(req_table)

    # --- SEMANTIC MATCH REPORT (When both are present) ---
    if resume_extracted and jd_extracted:
        must_skills = jd_extracted.get("must_have_skills") or []
        res_skills = resume_extracted.get("skills") or []

        if must_skills and res_skills:
            console.print("\n")
            with console.status("[bold cyan]Computing semantic ontology match report...[/bold cyan]"):
                report = match_skills(must_skills, res_skills)

            match_pct = report.get("match_rate", 0.0) * 100
            rate_style = "bold green" if match_pct >= 70 else ("bold yellow" if match_pct >= 40 else "bold red")

            summary_panel_text = (
                f"Must-Have Skills Match Rate: [{rate_style}]{match_pct:.1f}%[/{rate_style}] | "
                f"Matched: [green]{len(report.get('matches', []))}[/green] / {len(must_skills)} | "
                f"Gaps: [red]{len(report.get('gaps', []))}[/red]"
            )
            console.print(Panel(summary_panel_text, title="[bold magenta]⚖️ Pass 1 Alignment Overview[/bold magenta]", border_style="magenta", box=box.ROUNDED))

            # Detailed Match Table
            match_table = Table(title="🔍 Skill Matching & Semantic Proximity Details", box=box.ROUNDED, header_style="bold magenta")
            match_table.add_column("Required Skill (JD)", style="bold white")
            match_table.add_column("Category", style="yellow")
            match_table.add_column("Candidate Match", style="cyan")
            match_table.add_column("Similarity", justify="right")
            match_table.add_column("Verdict", justify="center")

            # Matched rows
            for m in report.get("matches", []):
                cat = get_skill_category(m["jd_skill"]) or "tech"
                sim = m.get("similarity", 0.0)
                sim_str = f"[green]{sim:.2f}[/green]"
                verdict = "[bold green]✔ MATCHED[/bold green]"
                match_table.add_row(m["jd_skill"], cat, str(m.get("resume_match")), sim_str, verdict)

            # Gap rows
            for g in report.get("gaps", []):
                cat = get_skill_category(g["jd_skill"]) or "tech"
                sim = g.get("similarity", 0.0)
                sim_str = f"[red]{sim:.2f}[/red]"
                verdict = "[bold red]❌ GAP[/bold red]"
                candidate_attempt = g.get("resume_match") or "[dim]None[/dim]"
                match_table.add_row(g["jd_skill"], cat, f"[dim]{candidate_attempt}[/dim]", sim_str, verdict)

            console.print(match_table)

def run_parser_studio():
    resume_file = ""
    resume_parsed = ""
    jd_source = ""
    jd_parsed = ""

    # Cached Pass 1 structured extractions
    resume_extracted = None
    jd_extracted = None

    while True:
        console.clear()
        display_banner()

        # Status Panel
        status_table = Table(box=box.SIMPLE, show_header=False)
        status_table.add_column("Item", style="bold", width=24)
        status_table.add_column("Value")

        status_table.add_row(
            "Current Resume:",
            f"[green]{escape(resume_file)}[/green]" if resume_file else "[dim italic]None selected[/dim italic]",
        )
        jd_display_str = (
            Path(jd_source).name
            if Path(jd_source).exists()
            else (jd_source[:40] + "..." if len(jd_source) > 40 else jd_source)
        )
        status_table.add_row(
            "Current JD:",
            f"[blue]{escape(jd_display_str)}[/blue]" if jd_source else "[dim italic]None selected[/dim italic]",
        )

        # Pass 1 status in table
        res_pass1_status = (
            f"[bold green]✔ Extracted[/bold green] ({len(resume_extracted.get('skills', []))} skills)"
            if resume_extracted
            else "[dim italic]Not run[/dim italic]"
        )
        jd_pass1_status = (
            f"[bold blue]✔ Extracted[/bold blue] ({len(jd_extracted.get('must_have_skills', []))} required skills)"
            if jd_extracted
            else "[dim italic]Not run[/dim italic]"
        )
        status_table.add_row("Pass 1 (Resume):", res_pass1_status)
        status_table.add_row("Pass 1 (JD):", jd_pass1_status)

        console.print(Panel(status_table, title="[bold]Current Session State[/bold]", border_style="dim", box=box.ROUNDED))

        console.print("[bold cyan]Select an action:[/bold cyan]")
        console.print("  [bold green][1][/bold green] 📂 [bold]Upload Resume[/bold] (Opens File Picker for PDF/DOCX/TXT)")
        console.print("  [bold blue][2][/bold blue] 📂 [bold]Upload JD File[/bold] (Opens File Picker for PDF/DOCX/TXT)")
        console.print("  [bold yellow][3][/bold yellow] ✍️  [bold]Paste JD Text Directly[/bold]")
        console.print("  [bold magenta][4][/bold magenta] 📄 [bold]Run Parser & View Raw Parsed Text & PII Masking[/bold]")
        console.print("  [bold cyan][5][/bold cyan] 🤖 [bold]Run Pass 1: Extract & Normalize (Gemini 2.0 Flash + Ontology)[/bold]")
        console.print("  [bold magenta][6][/bold magenta] 🎯 [bold]Semantic Skill Matcher & Gap Analysis[/bold]")
        console.print("  [bold white][7][/bold white] 🧪 [bold]Load Sample Resume & JD (Quick Demo)[/bold]")
        console.print("  [bold red][0][/bold red] ❌ [bold]Exit[/bold]\n")

        choice = Prompt.ask("Enter option", choices=["0", "1", "2", "3", "4", "5", "6", "7"], default="5" if (resume_file or jd_source) else "1")

        if choice == "1":
            console.print("\n[cyan]Opening file picker dialog to choose Resume...[/cyan]")
            path = open_file_dialog(
                "Upload Resume (PDF, DOCX, TXT)",
                [
                    ("Resume files", "*.pdf;*.docx;*.txt"),
                    ("PDF files", "*.pdf"),
                    ("Word Documents", "*.docx"),
                    ("Text files", "*.txt"),
                    ("All files", "*.*"),
                ],
            )
            if not path:
                path = Prompt.ask("[yellow]No file picked from window. Enter file path manually (or leave blank to cancel)[/yellow]", default="")
            if path and Path(path).exists():
                resume_file = path
                resume_extracted = None  # Reset cached Pass 1
                console.print(f"[bold green]✔ Resume loaded:[/bold green] {resume_file}")
                try:
                    resume_parsed = parse_resume(resume_file)
                except Exception as e:
                    console.print(f"[bold red]Error parsing resume:[/bold red] {e}")
            elif path:
                console.print(f"[red]File not found: {path}[/red]")
            Prompt.ask("\nPress Enter to continue...")

        elif choice == "2":
            console.print("\n[cyan]Opening file picker dialog to choose Job Description...[/cyan]")
            path = open_file_dialog(
                "Upload Job Description (PDF, DOCX, TXT)",
                [("Document files", "*.pdf;*.docx;*.txt"), ("All files", "*.*")],
            )
            if not path:
                path = Prompt.ask("[yellow]No file picked from window. Enter file path manually (or leave blank to cancel)[/yellow]", default="")
            if path and Path(path).exists():
                jd_source = path
                jd_extracted = None  # Reset cached Pass 1
                try:
                    jd_parsed = parse_jd(jd_source)
                    console.print(f"[bold blue]✔ JD loaded:[/bold blue] {jd_source}")
                except Exception as e:
                    console.print(f"[bold red]Error parsing JD:[/bold red] {e}")
            elif path:
                console.print(f"[red]File not found: {path}[/red]")
            Prompt.ask("\nPress Enter to continue...")

        elif choice == "3":
            console.print("\n[cyan]Paste the Job Description text below (press Enter, then type 'DONE' on a new line):[/cyan]")
            lines = []
            while True:
                line = input()
                if line.strip() == "DONE":
                    break
                lines.append(line)
            raw_text = "\n".join(lines).strip()
            if raw_text:
                jd_source = raw_text
                jd_extracted = None  # Reset cached Pass 1
                jd_parsed = parse_jd(raw_text)
                console.print("[bold blue]✔ JD text saved and parsed.[/bold blue]")
            Prompt.ask("\nPress Enter to continue...")

        elif choice == "4":
            if not resume_file and not jd_source:
                console.print("[bold red]Please upload at least a Resume or a Job Description first![/bold red]")
                Prompt.ask("\nPress Enter to continue...")
                continue

            if resume_file and not resume_parsed:
                resume_parsed = parse_resume(resume_file)
            if jd_source and not jd_parsed:
                jd_parsed = parse_jd(jd_source)

            show_parse_results(resume_file, resume_parsed, jd_source, jd_parsed)
            
            # Offer seamless shortcut to run Pass 1
            if Confirm.ask("\n[bold cyan]Would you like to run Pass 1 Extraction (Gemini 2.0 Flash) now?[/bold cyan]", default=True):
                choice = "5"
            else:
                Prompt.ask("\nPress Enter to return to menu...")
                continue

        if choice == "5":
            if not resume_file and not jd_source:
                console.print("[bold red]Please upload at least a Resume or a Job Description first![/bold red]")
                Prompt.ask("\nPress Enter to continue...")
                continue

            # Parse raw text first if needed
            if resume_file and not resume_parsed:
                resume_parsed = parse_resume(resume_file)
            if jd_source and not jd_parsed:
                jd_parsed = parse_jd(jd_source)

            # Extract Resume with Gemini 2.0 Flash
            if resume_parsed and not resume_extracted:
                try:
                    with console.status("[bold cyan]Extracting structured Resume fields with Gemini 2.0 Flash...[/bold cyan]", spinner="dots"):
                        resume_extracted = extract_resume(resume_parsed, fast=False)
                    console.print("[bold green]✔ Resume extracted & skills normalized![/bold green]")
                except Exception as e:
                    console.print(f"[bold red]Error in Resume extraction:[/bold red] {e}")

            # Extract JD with Gemini 2.0 Flash + FAISS template normalizer
            if jd_parsed and not jd_extracted:
                try:
                    with console.status("[bold cyan]Extracting structured JD fields with Gemini 2.0 Flash...[/bold cyan]", spinner="dots"):
                        jd_extracted = extract_jd(jd_parsed, fast=False)
                        try:
                            jd_extracted["normalized_template"] = normalize_jd(jd_parsed)
                        except Exception:
                            pass
                    console.print("[bold blue]✔ JD extracted & requirements normalized![/bold blue]")
                except Exception as e:
                    console.print(f"[bold red]Error in JD extraction:[/bold red] {e}")

            show_pass1_results(resume_extracted, jd_extracted)

            if Confirm.ask("\n[dim]Would you like to view raw JSON outputs?[/dim]", default=False):
                if resume_extracted:
                    console.print("\n[bold green]=== Resume JSON ===[/bold green]")
                    console.print(JSON(json.dumps(resume_extracted)))
                if jd_extracted:
                    console.print("\n[bold blue]=== Job Description JSON ===[/bold blue]")
                    console.print(JSON(json.dumps(jd_extracted)))

            Prompt.ask("\nPress Enter to return to menu...")

        elif choice == "6":
            if not resume_extracted or not jd_extracted:
                console.print("[yellow]Pass 1 extraction has not been run for both Resume and JD yet.[/yellow]")
                if Confirm.ask("Run Pass 1 extraction now?", default=True):
                    # Trigger extraction
                    if resume_file and not resume_parsed:
                        resume_parsed = parse_resume(resume_file)
                    if jd_source and not jd_parsed:
                        jd_parsed = parse_jd(jd_source)

                    if resume_parsed and not resume_extracted:
                        with console.status("[bold cyan]Extracting Resume with Gemini 2.0 Flash...[/bold cyan]"):
                            resume_extracted = extract_resume(resume_parsed, fast=False)
                    if jd_parsed and not jd_extracted:
                        with console.status("[bold cyan]Extracting JD with Gemini 2.0 Flash...[/bold cyan]"):
                            jd_extracted = extract_jd(jd_parsed, fast=False)

            show_pass1_results(resume_extracted, jd_extracted)
            Prompt.ask("\nPress Enter to return to menu...")

        elif choice == "7":
            # Create sample files if they don't exist
            sample_resume_path = Path("data/raw_resumes/sample_resume.txt")
            sample_jd_path = Path("data/raw_jobs/sample_jd.txt")

            sample_resume_path.parent.mkdir(parents=True, exist_ok=True)
            sample_jd_path.parent.mkdir(parents=True, exist_ok=True)

            if not sample_resume_path.exists():
                sample_resume_path.write_text(
                    "Jane Doe\n"
                    "Email: jane.doe@techcorp.com\n"
                    "Phone: +919876543210\n"
                    "Location: Bangalore, India\n\n"
                    "SUMMARY:\n"
                    "Senior Software Engineer with 6+ years of experience in Python, FastAPI, and Machine Learning.\n\n"
                    "EXPERIENCE:\n"
                    "- Lead AI Engineer at DataScale Corp (2021 - Present)\n"
                    "  Built LLM inference pipelines, RAG systems, and Faiss vector search indices.\n"
                    "- Backend Developer at CloudSoft (2018 - 2021)\n"
                    "  Designed microservices in Python, Docker, PostgreSQL.\n\n"
                    "SKILLS:\n"
                    "Python, PyTorch, LangChain, Transformers, Docker, SQL, Git",
                    encoding="utf-8",
                )

            if not sample_jd_path.exists():
                sample_jd_path.write_text(
                    "Job Title: Senior AI / Machine Learning Engineer\n"
                    "Company: NextGen Systems\n\n"
                    "Requirements:\n"
                    "- 5+ years building production applications in Python.\n"
                    "- Deep hands-on experience with LLM orchestration, RAG, and vector search (Faiss, Chroma).\n"
                    "- Familiarity with FastAPI, Docker, and microservice architecture.\n"
                    "- Strong fundamentals in data structures, algorithms, and system design.\n\n"
                    "Responsibilities:\n"
                    "- Architect and deploy high-throughput AI screening agents.\n"
                    "- Optimize LLM latency and prompt evaluation pipelines.",
                    encoding="utf-8",
                )

            resume_file = str(sample_resume_path)
            jd_source = str(sample_jd_path)
            resume_extracted = None
            jd_extracted = None

            resume_parsed = parse_resume(resume_file)
            jd_parsed = parse_jd(jd_source)

            console.print("[bold green]✔ Loaded sample resume and sample JD.[/bold green]")
            show_parse_results(resume_file, resume_parsed, jd_source, jd_parsed)

            if Confirm.ask("\n[bold cyan]Run Pass 1 Extraction (Gemini 2.0 Flash) on sample data now?[/bold cyan]", default=True):
                with console.status("[bold cyan]Running Pass 1 Extraction with Gemini 2.0 Flash...[/bold cyan]"):
                    resume_extracted = extract_resume(resume_parsed, fast=False)
                    jd_extracted = extract_jd(jd_parsed, fast=False)
                    try:
                        jd_extracted["normalized_template"] = normalize_jd(jd_parsed)
                    except Exception:
                        pass
                show_pass1_results(resume_extracted, jd_extracted)

            Prompt.ask("\nPress Enter to return to menu...")

        elif choice == "0":
            console.print("[bold yellow]Exiting Studio. Goodbye![/bold yellow]")
            break

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Terminal Resume & JD Parser + Pass 1 Extraction Studio")
    parser.add_argument("--resume", type=str, help="Path to resume file (PDF/DOCX/TXT)")
    parser.add_argument("--jd", type=str, help="Path to JD file or raw text")
    parser.add_argument("--extract", action="store_true", help="Run Pass 1 structured extraction with Gemini 2.0 Flash")
    parser.add_argument("--demo", action="store_true", help="Run immediate demo with sample data")
    args = parser.parse_args()

    if args.demo:
        sample_resume_path = Path("data/raw_resumes/sample_resume.txt")
        sample_jd_path = Path("data/raw_jobs/sample_jd.txt")
        sample_resume_path.parent.mkdir(parents=True, exist_ok=True)
        sample_jd_path.parent.mkdir(parents=True, exist_ok=True)

        display_banner()
        r_text = parse_resume(str(sample_resume_path))
        j_text = parse_jd(str(sample_jd_path))
        show_parse_results(str(sample_resume_path), r_text, str(sample_jd_path), j_text)

        # Run Pass 1
        console.print("\n[bold cyan]Running Pass 1 Extraction (Gemini 2.0 Flash)...[/bold cyan]")
        r_ext = extract_resume(r_text, fast=False)
        j_ext = extract_jd(j_text, fast=False)
        try:
            j_ext["normalized_template"] = normalize_jd(j_text)
        except Exception:
            pass
        show_pass1_results(r_ext, j_ext)

    elif args.resume or args.jd:
        display_banner()
        r_text = parse_resume(args.resume) if args.resume else ""
        j_text = parse_jd(args.jd) if args.jd else ""
        show_parse_results(args.resume or "", r_text, args.jd or "", j_text)

        if args.extract:
            r_ext = extract_resume(r_text, fast=False) if r_text else None
            j_ext = extract_jd(j_text, fast=False) if j_text else None
            if j_ext and j_text:
                try:
                    j_ext["normalized_template"] = normalize_jd(j_text)
                except Exception:
                    pass
            show_pass1_results(r_ext, j_ext)
    else:
        run_parser_studio()
