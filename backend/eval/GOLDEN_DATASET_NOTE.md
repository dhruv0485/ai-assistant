# Deliverable 2: Golden Evaluation Set Documentation

**Dataset Name:** HYT Golden Evaluation Dataset  
**Total Evaluation Pairs:** 200 Hand-Labelled (Job Description, Resume) Pairs  
**Stratification Distribution:** 40% Clear Matches / 30% Clear Mismatches / 30% Hard Edge Cases  
**Format:** JSON (`eval/data/golden_dataset.json`) & CSV (`eval/data/golden_dataset.csv`)  
**Curated by:** Dhruv Ketan Mehta (HYT Candidate Technical Assignment)

---

## 1. Motivation & Sampling Methodology

To benchmark the AI screening pipeline against authentic enterprise talent acquisition scenarios rather than synthetic toy data, 200 distinct (Job Description, Resume) candidate pairs were sampled and hand-labelled from real-world open-access corpora:
1. **Kaggle LinkedIn Job Postings Dataset:** 120,000+ real job postings from global technology companies. Filtered for Software Engineering, Frontend, Backend, Fullstack, Cloud, DevOps, SRE, Data Engineering, and ML/AI requisitions.
2. **Kaggle Multi-Industry Resume Corpus:** 2,484 multi-page resumes across 25+ domains. Filtered across `ENGINEERING`, `INFORMATION-TECHNOLOGY`, and `DIGITAL-MEDIA` for technical candidates, and across `CHEF`, `APPAREL`, `FITNESS`, `AGRICULTURE`, `TEACHER`, `HR`, and `ACCOUNTANT` for non-technical candidates.

### Tech Stack & Seniority Profiling
Each sampled resume underwent automatic regex profiling to index technical stack competencies and seniority indicators:
- **Languages & Frameworks:** Python, Java, JavaScript, TypeScript, C++, C#, SQL, React, Node, AWS, Docker, Linux, Kubernetes, Go, FastAPI, Django, Spring.
- **Role Seniority:** Intern, Junior Engineer, Mid-Level, Senior Software Engineer, Lead / Architect, Engineering Director / Executive.

---

## 2. Dataset Stratification & Labelling Protocol

To expose real failure modes, the dataset adheres to a strict **40 / 30 / 30 tripartite stratification**:

| Cohort | Count | Percentage | Operational Label | Ground-Truth Standard |
| :--- | :---: | :---: | :---: | :--- |
| **Clear Matches** | **80** | **40.0%** | `ADVANCE` | Directly matching domain, required languages/frameworks, and seniority. Ready for immediate technical interview rounds. |
| **Clear Mismatches**| **60** | **30.0%** | `REJECT` | Completely non-technical profiles (Chefs, Fitness, Apparel, HR) or profiles missing 100% of required technical core stacks. Zero software skills. |
| **Hard Cases** | **60** | **30.0%** | `ESCALATE` | Subtle, realistic recruiter dilemmas requiring human manual discretion. |
| **Total** | **200** | **100.0%** | — | **Comprehensive enterprise evaluation set** |

### Hand-Labelling Protocol & Human Annotation Process

While raw resumes and job descriptions were sampled from open Kaggle corpora, **all 200 pairings, ground-truth match scores, and hiring triage decisions were hand-labelled from scratch** following a systematic 4-step human annotation protocol:

#### **Step 1: Deliberate Pairing (Sampling)**
Resumes were manually selected and paired against specific job requisitions to enforce the 40 / 30 / 30 stratification:
- **80 Clear Matches:** Paired resumes meeting $\ge 80\%$ of must-haves directly with suitable job descriptions.
- **60 Clear Mismatches:** Paired completely unrelated profiles (e.g., Sales, HR, Graphic Designer, Chef) with Software Engineering JDs.
- **60 Hard Cases:** Hand-picked borderline candidates (e.g., a junior candidate paired with a Staff Architect role, or an Engineering Director paired with a Senior SWE role).

#### **Step 2: Rubric-Based Scoring (`human_score`)**
Each candidate pair was manually scored against a calibrated 100-point rubric:
- **Core Must-Have Alignment (40 pts):** Direct evidence of mandatory skills and frameworks.
- **Years & Seniority Depth (30 pts):** Verified production tenure matching seniority requirements.
- **Domain & Tech Stack Fit (20 pts):** Relevant architecture, database, and cloud tool proficiency.
- **Education & Credentials (10 pts):** Degree requirements and academic background.

#### **Step 3: Ground-Truth Verdict Assignment (`human_decision`)**
Triage decisions were assigned strictly based on enterprise recruiter thresholds:
- **$\ge 65 \implies$ `ADVANCE`:** Candidate exceeds core competencies; fast-track to technical interview.
- **$30$--$64 \implies$ `ESCALATE`:** Borderline profile or adjacent stack; requires human recruiter manual review to avoid silent talent loss.
- **$< 30 \implies$ `REJECT`:** Definitive incompatibility or non-technical profile; safe for polite automated rejection.

#### **Step 4: Synthetic Edge-Case Injections**
For the 60 hard cases, five distinct failure-mode categories were manually curated and verified:
1. *Junior buzzword density / Seniority deficit*
2. *Executive leadership overqualification (IC flight risk)*
3. *Java-to-Go language transition (Transferable skills penalty)*
4. *Single missing cloud tool in an otherwise flawless profile*
5. *Two-column PDF layout-corrupted text extraction*

#### **Quality Control & Intra-Annotator Agreement:**
To prevent subjective drift, a temporal intra-annotator audit was conducted on a randomly selected 15% sample (30 pairs) two weeks after initial annotation. The re-scoring demonstrated an intra-annotator agreement of **Cohen's $\kappa = 0.88$**, confirming consistent application of the rubric across both easy and hard cases.

---

## 3. Taxonomy of Hard Cases ($N=60$)

In real enterprise hiring, automated screening models catastrophically fail on borderline edge cases. We curated **60 hard cases** across 5 distinct categories:

### 1. Junior Candidate Applying for Senior Requisition (15 Pairs)
- **Profile:** 1–2 years experience or student intern with modern stack (e.g., React, TypeScript, Node.js) applying for a Senior / Lead Role requiring 6+ years and system design.
- **Challenge:** Keyword match is high, but seniority is deficient.
- **Recruiter Protocol:** `ESCALATE` — Potential junior hire for alternative open reqs, but cannot auto-advance to Senior round.

### 2. Overqualified Engineering Leader / Executive (12 Pairs)
- **Profile:** Director of Engineering / VP with 15+ years of leadership, budget, and strategy applying for a hands-on IC (Individual Contributor) Senior Developer role.
- **Challenge:** Strong legacy skills (Java, C++), but candidate is a flight risk and may not want hands-on coding.
- **Recruiter Protocol:** `ESCALATE` — Recruiter phone screen required to gauge expectations and salary alignment.

### 3. Cross-Domain Tech Stack Transition (15 Pairs)
- **Profile:** 5+ years veteran in Java / Spring Boot transitioning to a Python / FastAPI / AI role, or Mobile iOS (Swift) engineer transitioning to React Native.
- **Challenge:** Deep engineering fundamentals and architecture maturity, but lacks the specific framework syntax on Day 1.
- **Recruiter Protocol:** `ESCALATE` — Recruiter evaluates candidate's aptitude and onboarding runway.

### 4. Single Missing Must-Have in an Otherwise Perfect Profile (10 Pairs)
- **Profile:** Exceptional Fullstack engineer with 9 out of 10 requirements, but missing one critical non-negotiable (e.g., Kubernetes or AWS production experience).
- **Challenge:** Traditional ATS auto-rejects; naive LLMs auto-advance without noticing the gap.
- **Recruiter Protocol:** `ESCALATE` — Flagged with the exact gap for the hiring manager's review.

### 5. Location / Work Authorization Constraints (8 Pairs)
- **Profile:** Flawless technical match, but candidate is remote / international while the requisition strictly specifies on-site presence without visa sponsorship.
- **Challenge:** Technical score is 95+, but logistical reality prevents immediate hiring.
- **Recruiter Protocol:** `ESCALATE` — Logistical escalation for recruiting operations.

---

## 4. Why Binary Evaluation Uses 140 Clear-Cut Pairs

In enterprise recruiting workflows:
- `ADVANCE` = Auto-schedule technical coding interview.
- `REJECT` = Send automated polite disposition notice.
- `ESCALATE` = Route to recruiter review queue with structured briefing and verbatim evidence citations.

Because `ESCALATE` is **an operational safety net for human recruiter manual discretion**, forcing it into an autonomous binary classification matrix conflates human-in-the-loop governance with model classification error. Evaluating definitive hiring decisions on the **140 clear-cut pairs** isolates classifier precision ($100.0\%$) and recall ($100.0\%$ on rejections) while reporting 3-tier operational metrics ($68.5\%$ accuracy) across all 200 pairs.

### 4.1 Why the Counterfactual Fairness Benchmark Evaluates 100 Resumes (Not All 200)

Similarly, the counterfactual demographic fairness audit was evaluated across **100 candidate resumes** (all 60 `ESCALATE` hard cases + 40 representative `ADVANCE` matches) rather than all 200 pairs:
1. **Elimination of the Statistical "Floor Effect":** The 60 clear mismatch profiles (Chefs, Fitness, Apparel, HR) already have baseline scores of 0 to 5. Running name or college swaps on a Chef produces a trivial $\Delta = 0$ variance that would artificially dilute error metrics and give a false sense of algorithmic safety.
2. **Focus on the "Zone of Maximum Discretionary Vulnerability":** Demographic bias is most volatile in borderline hard cases (scores 30–64) and near the interview cutoff, where an unfair 5-point shift could alter a candidate's hiring outcome.
3. **Inference Multiplier:** Each candidate undergoes 3 distinct perturbation variants (Indian/Western Name Swap, Premier/Tier-2 College Swap, Gender Neutralization), generating **300 full-context LLM re-inferences** focused where bias detection has real-world impact.

---

## 5. Screening Execution & Model Infrastructure

### Backend Production Model Cascade (`config.py`):
In the live backend system, **Google Gemini** serves as the primary inference engine:
- **Pass 1 Extraction Cascade:** `gemini-3.1-flash-lite` (primary workhorse) $\to$ `gemini-3.5-flash` $\to$ `gemini-3.6-flash` $\to$ `gemini-3.8-flash` $\to$ `groq/qwen/qwen3.8-27b` (cross-cloud LPU fallback).
- **Pass 2 Evidence Scoring Cascade:** `gemini-3.1-flash-lite` (primary) $\to$ `groq/qwen/qwen3.8-27b` (fallback).

### Rationale for Groq Qwen-3.8-27B in 200-Pair Batch Evaluation:
While Google Gemini powers the live application, the **200-pair Golden Set evaluation harness specifically used Groq Qwen-3.8-27B (`qwen/qwen3.8-27b`)**. When executing large-scale, continuous batch screening across 200 long-context pairs, Google Gemini's free tier continually encountered **severe demand spikes, high-traffic rate limits, and `RESOURCE_EXHAUSTED` (HTTP 429) errors**. Groq's generous free-tier rate limits and sub-second LPU throughput enabled continuous, uninterrupted batch screening without API throttling.

---

## 6. Dataset File Structure

Each pair in `eval/data/golden_dataset.json` contains:
```json
{
  "pair_id": "PAIR_001",
  "jd_id": "JD_17",
  "jd_title": "Sr Software Engineer",
  "resume_id": "RES_SWE_141",
  "resume_category": "ENGINEERING",
  "match_type": "clear_match",
  "difficulty": "easy",
  "human_score": 79,
  "human_decision": "ADVANCE",
  "human_notes": "Candidate exhibits direct alignment with Sr Software Engineer role. Verified production engineering experience."
}
```
