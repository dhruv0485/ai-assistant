# AI Screening Assistant — Hunt Your Tribe
> **Enterprise Candidate Resume Screening, Skill Ontology Normalization & Counterfactual Fairness Engine**  
> Developed for **Hunt Your Tribe** — Graduate 2027 Take-Home Technical Assignment.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%2F%20Vite-61DAFB.svg)](https://vitejs.dev)
[![Gemini](https://img.shields.io/badge/Production%20Primary-Google%20Gemini-blue.svg)](https://ai.google.dev/)
[![Groq](https://img.shields.io/badge/Evaluation%20%26%20Fallback-Groq%20Qwen--3.8--27B-orange.svg)](https://groq.com)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

---

## 🤖 Production Model Architecture vs. Evaluation Infrastructure

> [!IMPORTANT]
> ### Backend Production Model Cascade:
> In the live backend system (`config.py`, `pipeline.py`, `worker.py`), **Google Gemini** models serve as the primary screening engines, supported by a multi-tier fallback cascade:
> - **Pass 1 Extraction Chain:**
>   1. `gemini-3.1-flash-lite` *(Primary Workhorse)*
>   2. `gemini-3.5-flash` *(Fallback 1)*
>   3. `gemini-3.6-flash` *(Fallback 2)*
>   4. `gemini-3.8-flash` *(Fallback 3)*
>   5. **`groq/qwen/qwen3.8-27b`** *(Fallback 4 — Cross-Cloud LPU Resilience)*
> - **Pass 2 Evidence Scoring Chain:**
>   1. `gemini-3.1-flash-lite` *(Primary Evidence Scorer)*
>   2. **`groq/qwen/qwen3.8-27b`** *(Pass 2 Fallback)*
>
> ### Why Groq Qwen-3.8-27B was Chosen for the 200-Pair Evaluation:
> While Gemini powers the live system, **Groq Qwen-3.8-27B was specifically utilized for the 200-pair evaluation harness**. During batch evaluation of 200 long-context (JD, Resume) pairs, Google Gemini's free tier continually encountered **severe demand spikes and API resource exhaustion errors (`HTTP 429: RESOURCE_EXHAUSTED`)**. Groq's generous rate limits and high-speed LPU inference allowed continuous, uninterrupted batch screening without API throttling.

---

## 🏆 Headline Results Summary

All headline evaluation benchmarks are pre-computed and verifiable in **under 2 minutes**:

| Metric | AI Pipeline (Groq Qwen-3.8-27B) | Baseline: BM25 | Baseline: Random | Baseline: Keyword Overlap | Baseline: TF-IDF |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Binary Decision Accuracy ($N=140$)** | **78.57%** | 49.29% | 46.43% | 45.00% | 42.86% |
| **Binary Macro F1** | **78.46%** | 45.02% | 46.10% | 34.07% | 30.00% |
| **ADVANCE Precision** | **100.00%** *(Zero False Positives)* | 71.43% | 55.10% | 100.00% | 0.00% |
| **REJECT Recall** | **100.00%** *(Zero Non-Tech Leaks)* | 90.00% | 63.33% | 100.00% | 100.00% |
| **Ranking Quality (NDCG@5)** | **0.9653** | 0.8920 | 0.8120 | 0.8930 | 0.8359 |
| **Mean Average Precision (MAP)** | **0.8717** | 0.7420 | 0.6370 | 0.7500 | 0.6410 |
| **Operational 3-Class Accuracy ($N=200$)**| **68.50%** *(0 qualified lost)* | — | — | — | — |
| **LLM-as-Judge Explanation Quality** | **81.20 / 100** | — | — | — | — |
| **Counterfactual Demographic Bias** | **0.0% Flag Rate** ($\Delta \le 5$ pts) | — | — | — | — |

---

## ⚡ 15-Minute Headline Reproduction Guide

Follow these steps to reproduce all headline metrics on your local machine in under 15 minutes.

### Step 1: Environment Setup (2 Minutes)
Ensure Python 3.10+ is installed. Navigate to the backend directory and activate the virtual environment:

```powershell
# Navigate to backend directory
cd hyt_screening/backend

# Activate the existing virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1
```

### Step 2: Reproduce Headline Metrics & Confusion Matrix (15 Seconds)
Run the automated evaluation harness against the pre-computed 200-pair evaluation dataset:

```powershell
python eval/metrics.py
```
**Expected Output:**
- Prints the exact **2x2 Binary Confusion Matrix** ($\text{TP}=50$, $\text{FN}=30$, $\text{FP}=0$, $\text{TN}=60$).
- Outputs **78.57% Binary Accuracy**, **78.46% Macro F1**, **100.0% ADVANCE Precision**, and **100.0% REJECT Recall**.
- Computes ranking metrics: **NDCG@3 = 0.9483**, **NDCG@5 = 0.9653**, **MAP = 0.8717**, **MRR = 0.9067**.
- Generates `eval/metrics_report.json`.

### Step 3: Reproduce Industry Baselines Comparison (30 Seconds)
Compare the AI pipeline directly against traditional search and lexical baselines (BM25, TF-IDF, Keyword Jaccard, Random):

```powershell
python eval/baselines.py
```
**Expected Output:**
- Evaluates all 140 clear-cut pairs across BM25, TF-IDF, Keyword Overlap, and Random baselines.
- Verifies that traditional keyword matching achieves only **42.9% to 49.3% accuracy** (worse than a coin flip), proving a **+29.3% absolute lift** from our LLM pipeline.

### Step 4: Reproduce LLM-as-Judge Explanation Audit (30 Seconds)
Run the independent LLM judge rubric across the 5 dimensions of explanation defensibility:

```powershell
python eval/judge.py
```
**Expected Output:**
- Outputs mean rubric scores: **Groundedness 3.80/5**, **Completeness 4.20/5**, **Actionability 4.60/5**, **Objectivity 5.00/5**, **Decision Alignment 4.88/5**.
- Computes the **Overall Explanation Quality Index: 81.2 / 100**.

### Step 5 (Optional): Live Batch Screening via Groq API (5–10 Minutes)
To rerun the full screening pipeline live from scratch using the Groq API key:

```powershell
# Screen 5 sample pairs live
python eval/build_golden_set.py --screen --limit 5 --sleep 2.0

# Or run full 200 pairs live (requires ~10-15 minutes due to rate limits)
python eval/build_golden_set.py --screen --limit 200 --sleep 2.5
```

---

## 🏛️ System Architecture Overview

The platform is designed around an evidence-grounded, two-pass decoupled architecture:

```
[Candidate / HR Frontend] (React 18 / Vite / TanStack)
           │
           ▼
[Supabase Infrastructure] (PostgreSQL Auth & Encrypted S3 Resumes)
           │
           ▼
[FastAPI Backend Daemon] (worker.py / pipeline.py)
   │
   ├─► 1. Document Ingestion (pdfplumber / python-docx)
   ├─► 2. Regex PII Masking (Redacts email, phone, address)
   ├─► 3. Pass 1: Structured Extraction (Primary: Gemini 3.1 Flash-Lite → Gemini Fallbacks → Groq Qwen Fallback)
   ├─► 4. FAISS Vector Normalization (Matches 130 canonical Lovable JD templates)
   ├─► 5. Semantic Skill Ontology (Maps 38 categories & 6,796 Lovable aliases)
   ├─► 6. Pass 2: Evidence Scoring (Primary: Gemini 3.1 Flash-Lite → Groq Qwen Fallback)
   ├─► 7. Counterfactual Fairness Audit (Perturbs Name, College, Gender; Delta <= 5 pts)
   └─► 8. Calibrated Policy Engine (ADVANCE >= 12 | ESCALATE 5-11 | REJECT < 5)
```

### Knowledge Base Assets
- `data/skill_ontology/jd_templates.json`: **130 standardized role templates** across 14 technical domains synthesized using **Lovable**.
- `data/skill_ontology/skills.json`: **38 technical categories**, **631 canonical concepts (340+ core engineering skills)**, and **6,796 aliases** curated using **Lovable**.

