# AI Screening Assistant — Complete Setup & Run Guide

This guide provides end-to-end instructions for configuring the environment, installing dependencies, and running both the **Frontend** and **Backend** services of the **AI Screening Assistant** (Hunt Your Tribe Take-Home Technical Assignment).

---

## 📋 Table of Contents
1. [System Architecture Overview](#system-architecture-overview)
2. [Prerequisites & System Requirements](#prerequisites--system-requirements)
3. [Environment Configuration (`.env` Files)](#environment-configuration-env-files)
   - [Backend `.env`](#1-backend-environment-file-hytscreeningbackendenv)
   - [Frontend `.env`](#2-frontend-environment-file-hytscreeningfrontendenv)
4. [Backend Setup & Run Instructions](#backend-setup--run-instructions)
   - [Virtual Environment & Dependencies](#step-1-create--activate-python-virtual-environment)
   - [Running the Background Polling Worker](#step-2-run-the-async-screening-worker-daemon)
   - [Running the CLI Screening Pipeline](#step-3-run-interactive-cli-screening-optional)
   - [Running the Evaluation Harness](#step-4-run-the-evaluation--benchmarking-suite)
5. [Frontend Setup & Run Instructions](#frontend-setup--run-instructions)
   - [Dependencies Installation](#step-1-install-node-dependencies)
   - [Starting the Development Server](#step-2-start-vite-dev-server)
   - [Available Portal Routes](#step-3-access-the-portals)
6. [End-to-End Operational Flow](#end-to-end-operational-flow)
7. [Troubleshooting & Common FAQs](#troubleshooting--common-faqs)

---

## 🏛️ System Architecture Overview

The application consists of two decoupled, production-ready tiers:
- **Frontend (`hyt_screening/frontend`):** Built with **React 18**, **Vite**, **TanStack Router**, and **TailwindCSS**. Provides dual experiences: a **Candidate Portal** (instant self-evaluation, resume upload) and an **HR Command Center** (pipeline HUD, job requisition studio, evidence audit drawer).
- **Backend (`hyt_screening/backend`):** Built in **Python 3.10+**. Features an asynchronous polling daemon (`worker.py`), a 9-step evidence-grounded screening pipeline, FAISS dense vector retrieval, an extensive 6,796-alias semantic ontology, counterfactual fairness audits, and a multi-tiered resilient LLM inference cascade (Google Gemini primary with Groq Qwen fallback).
- **Database & Storage:** **Supabase PostgreSQL** for relational persistence and Supabase encrypted Storage buckets for candidate resumes.

---

## 💻 Prerequisites & System Requirements

Before beginning, ensure you have the following installed on your machine:
- **Python:** Version 3.10 or higher (`python --version`)
- **Node.js:** Version 18.x or 20.x+ (`node -v`) with `npm` (or `bun`)
- **Operating System:** Windows, macOS, or Linux (Windows PowerShell commands provided below)
- **API Keys:**
  - Google Gemini API Key ([Google AI Studio](https://aistudio.google.com/))
  - Groq Cloud API Key ([Groq Console](https://console.groq.com/))
  - Supabase Project URL & Keys ([Supabase Dashboard](https://supabase.com/))

---

## 🔑 Environment Configuration (`.env` Files)

The project relies on two `.env` files: one in the backend directory and one in the frontend directory.

### 1. Backend Environment File (`hyt_screening/backend/.env`)

Navigate to `hyt_screening/backend` and create or edit `.env`:

```env
# =============================================================================
# LLM Inference Cascade API Keys
# =============================================================================
# Primary Production Workhorse (Pass 1 Extraction & Pass 2 Evidence Scoring)
GEMINI_API_KEY=your_gemini_api_key_here

# Groq Cloud API Key (Powers ultra-fast LPU fallback and batch evaluation on Qwen-3.8-27B)
GROQ_API_KEY=your_groq_api_key_here

# Optional: Auxiliary Fallback Provider
OPENROUTER_API_KEY=your_openrouter_api_key_here

# =============================================================================
# Supabase Relational Database & S3 Storage Credentials
# =============================================================================
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_jwt_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_secret_here

# Optional Database Admin Credentials
SUPABASE_SECRET_KEY=your_supabase_secret_key_here
SUPABASE_DB_PASSWORD=your_supabase_db_password_here
```

#### Field Explanations:
| Variable | Required | Description |
| :--- | :---: | :--- |
| `GEMINI_API_KEY` | **Yes** | Used by `gemini-3.1-flash-lite`, `gemini-3.5-flash`, `gemini-3.6-flash`, and `gemini-3.8-flash` in the live multi-tier screening cascade. |
| `GROQ_API_KEY` | **Yes** | Powers `qwen/qwen3.8-27b` on Groq LPU inference. Serves as the cross-cloud fallback during Gemini rate limits and was used for continuous 200-pair evaluation without `HTTP 429` interruptions. |
| `SUPABASE_URL` | **Yes** | URL endpoint of your Supabase instance. |
| `SUPABASE_SERVICE_ROLE_KEY` | **Yes** | Elevated service role key required by `worker.py` to watch `applications`, stream resume bytes, and write screening results and fairness audits back to the database. |

---

### 2. Frontend Environment File (`hyt_screening/frontend/.env`)

Navigate to `hyt_screening/frontend` and create or edit `.env`:

```env
# =============================================================================
# Supabase Client-Side Configuration (Vite)
# =============================================================================
VITE_SUPABASE_URL=https://your-project-ref.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_jwt_here
VITE_SUPABASE_PUBLISHABLE_KEY=your_supabase_publishable_key_here
```

#### Field Explanations:
| Variable | Required | Description |
| :--- | :---: | :--- |
| `VITE_SUPABASE_URL` | **Yes** | Public Supabase endpoint for client-side queries and uploads. |
| `VITE_SUPABASE_ANON_KEY` | **Yes** | Public Anonymous JWT key for authenticated and public access. |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Optional | Additional client key for Supabase v2 integrations. |

---

## ⚙️ Backend Setup & Run Instructions

All backend commands should be run from `hyt_screening/backend`.

### Step 1: Create & Activate Python Virtual Environment

Open a terminal (PowerShell on Windows):

```powershell
# Navigate to backend directory
cd c:\Users\Dhruv\Desktop\ai_screen\hyt_screening\backend

# Create virtual environment (if not already created)
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Linux / macOS:
# source venv/bin/activate
```

> [!TIP]
> If Windows PowerShell blocks script execution with an `Execution_Policies` warning, run:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> .\venv\Scripts\Activate.ps1
> ```

### Step 2: Install Python Dependencies

With the virtual environment active, install all required packages:

```powershell
pip install -r requirements.txt
```

### Step 3: Run the Async Screening Worker Daemon

The worker watches Supabase in real-time, picks up `pending` applications, runs them through the 9-step screening pipeline, and persists verdicts and evidence:

```powershell
python worker.py
```

**What the worker does live in terminal:**
- Connects to Supabase PostgreSQL and Storage buckets.
- Polls for applications with `status = "pending"`.
- Executes PDF text extraction and regex PII masking.
- Calls Pass 1 structured extraction via Gemini (or Groq fallback).
- Executes FAISS dense vector template matching ($O(1)$ Inner Product).
- Scores candidate with sentence-level citations (Pass 2).
- Runs counterfactual fairness perturbation audit ($\Delta \le 5$ pts).
- Saves verdict (`ADVANCE`, `ESCALATE`, `REJECT`) directly back to Supabase.

---

### Step 4: Run Interactive CLI Screening (Optional)

To test a single resume file against a job description directly via the terminal:

```powershell
python pipeline.py
```
Or for rich formatted terminal tables:
```powershell
python parser_cli.py
```

---

### Step 5: Run the Evaluation & Benchmarking Suite

To reproduce all headline metrics from the assignment report (under 2 minutes):

```powershell
# 1. 2x2 Confusion Matrix, Accuracy (78.57%), NDCG@5 (0.9653), MAP (0.8717)
python eval/metrics.py

# 2. Comparative Baselines (BM25, TF-IDF, Keyword Overlap, Random)
python eval/baselines.py

# 3. LLM-as-Judge 5-Dimension Explanation Quality Rubric (81.2 / 100)
python eval/judge.py
```

---

## 🎨 Frontend Setup & Run Instructions

All frontend commands should be run from `hyt_screening/frontend`.

### Step 1: Install Node Dependencies

Open a new terminal window:

```powershell
# Navigate to frontend directory
cd c:\Users\Dhruv\Desktop\ai_screen\hyt_screening\frontend

# Install dependencies using npm (or bun)
npm install
# Or: bun install
```

### Step 2: Start Vite Dev Server

Start the local development server:

```powershell
npm run dev
# Or: bun run dev
```

The application will start locally at **`http://localhost:5173`** (or the port shown in your terminal).

---

### Step 3: Access the Portals

Open your browser to test the full system:

| Route | Role | Description |
| :--- | :---: | :--- |
| **`http://localhost:5173/`** | Candidate | **Instant Self-Score Evaluator:** Upload a resume PDF/Word and paste a job description for live instant scoring. |
| **`http://localhost:5173/openings`** | Candidate | **Job Explorer:** Browse open requisitions with required competencies and experience criteria. |
| **`http://localhost:5173/apply/:id`** | Candidate | **Job Application Flow:** Apply to a specific job opening with resume upload and document preview. |
| **`http://localhost:5173/hr`** | Recruiter | **Talent Pipeline HUD:** View candidate ranking by match score, filtering by verdict (`ADVANCE`, `ESCALATE`, `REJECT`), and fairness audit flags. |
| **`http://localhost:5173/hr/create-job`** | Recruiter | **Requisition Studio:** Create standardized job postings with must-have and nice-to-have weighting. |
| **`http://localhost:5173/hr/jobs/:id`** | Recruiter | **Evidence Audit Drawer:** Inspect verbatim extracted sentence proof, confidence variance, and recruiter override controls. |

---

## 🔄 End-to-End Operational Flow

```
[Candidate Browser]
       │
       ▼ (1. Uploads PDF/DOCX Resume & Submits Application)
[Supabase Storage & PostgreSQL] (status: "pending")
       │
       ▼ (2. Polling Daemon detects pending row)
[Backend worker.py]
       │
       ├──> 1. Document Ingestion (pdfplumber / python-docx)
       ├──> 2. PII Masking (Redacts phone, email, address)
       ├──> 3. Pass 1 Structured Extraction (Gemini 3.1 Flash-Lite / Fallback)
       ├──> 4. FAISS Normalization (Matches 130 Lovable canonical templates)
       ├──> 5. Semantic Skill Ontology (38 categories, 6,796 aliases)
       ├──> 6. Pass 2 Evidence-Grounded Scoring (Verbatim resume citations)
       ├──> 7. Counterfactual Fairness Audit (Perturbs Name/College, Delta <= 5 pts)
       └──> 8. Calibrated Policy Verdict (ADVANCE >= 65, ESCALATE 30-64, REJECT < 30)
       │
       ▼ (3. Writes score, verdict, citations, fairness audit back)
[Supabase Database] (status: "completed")
       │
       ▼ (4. Real-time update)
[Recruiter HR Command Center] (Displays ranking, verified evidence & audit flags)
```

---

## 🛠️ Troubleshooting & Common FAQs

### 1. `Execution_Policies` error on Windows PowerShell
**Problem:** `Activate.ps1 cannot be loaded because running scripts is disabled on this system.`  
**Solution:** Run the following command in PowerShell before activating:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 2. Google Gemini Rate Limit (`HTTP 429: RESOURCE_EXHAUSTED`)
**Problem:** High traffic spikes on the free Gemini tier.  
**Solution:** The system includes automatic multi-tier fallback configured in `config.py`. If Gemini experiences a demand spike, inference automatically cascades:
`gemini-3.1-flash-lite` $\to$ `gemini-3.5-flash` $\to$ `gemini-3.6-flash` $\to$ `gemini-3.8-flash` $\to$ **`Groq Qwen-3.8-27B`**. Ensure your `GROQ_API_KEY` is set in `backend/.env`.

### 3. Port Conflicts on Frontend
**Problem:** Port `5173` is already in use.  
**Solution:** Vite will automatically prompt you to use the next available port (e.g., `5174`). Alternatively, specify a port:
```powershell
npm run dev -- --port 3000
```

### 4. Supabase Permission / RLS Errors
**Problem:** Worker cannot update candidate records.  
**Solution:** Ensure you are using the `SUPABASE_SERVICE_ROLE_KEY` (secret) in `backend/.env`, not the public anonymous key. The service role key bypasses Row-Level Security for worker write operations.
