import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import tkinter as tk
from tkinter import filedialog
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.text import Text
from rich.markup import escape
from rich import box

# Import parser functions
from src.parser import parse_resume, parse_jd, extract_text_from_pdf, extract_text_from_docx, extract_text_from_txt, clean_text, mask_pii

console = Console()

def open_file_dialog(title: str, filetypes: list) -> str:
    """Opens a native OS file picker window to select/upload a file."""
    try:
        root = tk.Tk()
        root.withdraw()  # Hide root window
        root.attributes('-topmost', True)  # Bring file dialog to front
        selected_file = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes
        )
        root.destroy()
        return selected_file
    except Exception as e:
        console.print(f"[yellow]Notice: Native file picker unavailable ({e}). Falling back to text prompt.[/yellow]")
        return ""

def display_banner():
    banner_text = Text()
    banner_text.append("HYT SCREENING ", style="bold cyan")
    banner_text.append("— Resume & Job Description Parser CLI\n", style="bold white")
    banner_text.append("Upload / Select documents and inspect full parsed text & PII masking directly in terminal.", style="dim")
    console.print(Panel(banner_text, box=box.ROUNDED, border_style="cyan"))

def show_parse_results(resume_path: str, resume_parsed_text: str, jd_input: str, jd_parsed_text: str):
    console.print("\n")
    
    # Summary Table
    table = Table(title="📊 Parsing Summary", box=box.ROUNDED, header_style="bold magenta")
    table.add_column("Document", style="cyan", no_wrap=True)
    table.add_column("Source / File", style="white")
    table.add_column("Characters", justify="right", style="green")
    table.add_column("Words", justify="right", style="green")
    table.add_column("PII Masked Count", justify="right", style="yellow")

    resume_pii_count = resume_parsed_text.count("[EMAIL]") + resume_parsed_text.count("[PHONE]") if resume_parsed_text else 0
    table.add_row(
        "📄 Resume",
        Path(resume_path).name if resume_path else "None",
        str(len(resume_parsed_text)) if resume_parsed_text else "0",
        str(len(resume_parsed_text.split())) if resume_parsed_text else "0",
        str(resume_pii_count)
    )

    jd_source_name = Path(jd_input).name if Path(jd_input).exists() else "Direct Text Input"
    table.add_row(
        "📋 Job Description",
        jd_source_name if jd_input else "None",
        str(len(jd_parsed_text)) if jd_parsed_text else "0",
        str(len(jd_parsed_text.split())) if jd_parsed_text else "0",
        "N/A"
    )
    console.print(table)

    # Resume Parsed Content Panel
    if resume_parsed_text:
        console.print("\n")
        safe_resume_name = escape(Path(resume_path).name if resume_path else "")
        resume_header = f"📄 RESUME PARSED OUTPUT ({safe_resume_name}) [PII MASKED]"
        console.print(Panel(
            Text(resume_parsed_text),
            title=f"[bold green]{resume_header}[/bold green]",
            subtitle="[dim]Verified with PDF/DOCX/TXT Parser + Privacy Compliance[/dim]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2)
        ))

    # JD Parsed Content Panel
    if jd_parsed_text:
        console.print("\n")
        safe_jd_name = escape(Path(jd_input).name if Path(jd_input).exists() else "Direct Input")
        jd_header = f"📋 JOB DESCRIPTION PARSED OUTPUT ({safe_jd_name})"
        console.print(Panel(
            Text(jd_parsed_text),
            title=f"[bold blue]{jd_header}[/bold blue]",
            subtitle="[dim]Normalized & Cleaned[/dim]",
            border_style="blue",
            box=box.ROUNDED,
            padding=(1, 2)
        ))

def run_parser_studio():
    resume_file = ""
    resume_parsed = ""
    jd_source = ""
    jd_parsed = ""

    while True:
        console.clear()
        display_banner()

        # Status Panel
        status_table = Table(box=box.SIMPLE, show_header=False)
        status_table.add_column("Item", style="bold")
        status_table.add_column("Value")
        
        status_table.add_row(
            "Current Resume:",
            f"[green]{escape(resume_file)}[/green]" if resume_file else "[dim italic]None selected[/dim italic]"
        )
        jd_display_str = Path(jd_source).name if Path(jd_source).exists() else (jd_source[:40] + '...' if len(jd_source) > 40 else jd_source)
        status_table.add_row(
            "Current JD:",
            f"[blue]{escape(jd_display_str)}[/blue]" if jd_source else "[dim italic]None selected[/dim italic]"
        )
        console.print(Panel(status_table, title="[bold]Current Session State[/bold]", border_style="dim", box=box.ROUNDED))

        console.print("[bold cyan]Select an action:[/bold cyan]")
        console.print("  [bold green][1][/bold green] 📂 [bold]Upload Resume[/bold] (Opens File Picker for PDF/DOCX/TXT)")
        console.print("  [bold blue][2][/bold blue] 📂 [bold]Upload JD File[/bold] (Opens File Picker for PDF/DOCX/TXT)")
        console.print("  [bold yellow][3][/bold yellow] ✍️  [bold]Paste JD Text Directly[/bold]")
        console.print("  [bold magenta][4][/bold magenta] 🚀 [bold]Run Parser & View Output[/bold]")
        console.print("  [bold cyan][5][/bold cyan] 🧪 [bold]Load Sample Resume & JD (Quick Demo)[/bold]")
        console.print("  [bold red][0][/bold red] ❌ [bold]Exit[/bold]\n")

        choice = Prompt.ask("Enter option", choices=["0", "1", "2", "3", "4", "5"], default="1")

        if choice == "1":
            console.print("\n[cyan]Opening file picker dialog to choose Resume...[/cyan]")
            path = open_file_dialog(
                "Upload Resume (PDF, DOCX, TXT)",
                [("Resume files", "*.pdf;*.docx;*.txt"), ("PDF files", "*.pdf"), ("Word Documents", "*.docx"), ("Text files", "*.txt"), ("All files", "*.*")]
            )
            if not path:
                path = Prompt.ask("[yellow]No file picked from window. Enter file path manually (or leave blank to cancel)[/yellow]", default="")
            if path and Path(path).exists():
                resume_file = path
                console.print(f"[bold green]✔ Resume loaded:[/bold green] {resume_file}")
                # Auto parse
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
                [("Document files", "*.pdf;*.docx;*.txt"), ("All files", "*.*")]
            )
            if not path:
                path = Prompt.ask("[yellow]No file picked from window. Enter file path manually (or leave blank to cancel)[/yellow]", default="")
            if path and Path(path).exists():
                jd_source = path
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
            Prompt.ask("\nPress Enter to return to menu...")

        elif choice == "5":
            # Create sample files if they don't exist
            sample_resume_path = Path("data/raw_resumes/sample_resume.txt")
            sample_jd_path = Path("data/raw_jobs/sample_jd.txt")
            
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
                    encoding="utf-8"
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
                    encoding="utf-8"
                )

            resume_file = str(sample_resume_path)
            jd_source = str(sample_jd_path)
            resume_parsed = parse_resume(resume_file)
            jd_parsed = parse_jd(jd_source)

            console.print("[bold green]✔ Loaded sample resume and sample JD.[/bold green]")
            show_parse_results(resume_file, resume_parsed, jd_source, jd_parsed)
            Prompt.ask("\nPress Enter to return to menu...")

        elif choice == "0":
            console.print("[bold yellow]Exiting Parser Studio. Goodbye![/bold yellow]")
            break

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Terminal Resume & JD Parser Studio")
    parser.add_argument("--resume", type=str, help="Path to resume file (PDF/DOCX/TXT)")
    parser.add_argument("--jd", type=str, help="Path to JD file or raw text")
    parser.add_argument("--demo", action="store_true", help="Run immediate demo with sample data")
    args = parser.parse_args()

    if args.demo:
        sample_resume_path = Path("data/raw_resumes/sample_resume.txt")
        sample_jd_path = Path("data/raw_jobs/sample_jd.txt")
        sample_resume_path.parent.mkdir(parents=True, exist_ok=True)
        sample_jd_path.parent.mkdir(parents=True, exist_ok=True)
        
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
            encoding="utf-8"
        )
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
            encoding="utf-8"
        )
        display_banner()
        r_text = parse_resume(str(sample_resume_path))
        j_text = parse_jd(str(sample_jd_path))
        show_parse_results(str(sample_resume_path), r_text, str(sample_jd_path), j_text)
    elif args.resume or args.jd:
        display_banner()
        r_text = parse_resume(args.resume) if args.resume else ""
        j_text = parse_jd(args.jd) if args.jd else ""
        show_parse_results(args.resume or "", r_text, args.jd or "", j_text)
    else:
        run_parser_studio()
