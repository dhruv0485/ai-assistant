# eval/baselines.py
"""
Traditional Machine Learning & Heuristic Screening Baselines.

Implements baseline models to compare against the LLM AI screening pipeline:
1. TF-IDF Cosine Similarity Baseline (scikit-learn)
2. BM25 Ranking Baseline (rank_bm25)
3. Skill / Keyword Jaccard Overlap Baseline
4. Random Baseline (lower bound)

Evaluates all 200 golden evaluation pairs and saves predictions to eval/baseline_results.json.
"""

import sys
import os
import re
import json
import random
from pathlib import Path
from typing import Dict, Any, List
import numpy as np
import pandas as pd

# Reconfigure stdout for UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rank_bm25 import BM25Okapi

_EVAL_DIR = Path(__file__).resolve().parent
GOLDEN_JSON = _EVAL_DIR / "data" / "golden_dataset.json"
BASELINE_RESULTS_JSON = _EVAL_DIR / "baseline_results.json"


# Common tech keywords for skill overlap
TECH_ONTOLOGY = {
    "python", "java", "javascript", "typescript", "c++", "c#", "golang", "go", "rust",
    "ruby", "php", "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "react", "angular", "vue", "next.js", "node.js", "express", "django", "fastapi", "flask", "spring", "spring boot",
    "aws", "azure", "gcp", "docker", "kubernetes", "k8s", "terraform", "ci/cd", "jenkins",
    "git", "linux", "rest", "restful", "graphql", "microservices", "kafka", "rabbitmq",
    "html", "css", "tailwind", "pandas", "numpy", "pytorch", "tensorflow", "scikit-learn",
    "machine learning", "deep learning", "nlp", "agile", "scrum", "jira"
}


def score_to_decision(score: float) -> str:
    """Map 0-100 score to decision policy."""
    if score >= 65:
        return "ADVANCE"
    elif score < 30:
        return "REJECT"
    else:
        return "ESCALATE"


def tokenize(text: str) -> List[str]:
    """Simple alphanumeric tokenizer for BM25 and keyword overlap."""
    return re.findall(r'[a-zA-Z0-9_+#.]+', text.lower())


def extract_tech_keywords(text: str) -> set:
    """Extract recognized technical terms from text."""
    text_lower = text.lower()
    found = set()
    for skill in TECH_ONTOLOGY:
        # Match whole word or bounded term
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found.add(skill)
    return found


# -------------------------------------------------------------------------
# Baseline 1: TF-IDF Cosine Similarity
# -------------------------------------------------------------------------
def run_tfidf_baseline(pairs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compute TF-IDF cosine similarity between Resume and JD text."""
    corpus = []
    for p in pairs:
        corpus.append(p["jd_text"])
        corpus.append(p["resume_text"])

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=5000,
        sublinear_tf=True
    )
    vectorizer.fit(corpus)

    results = []
    for p in pairs:
        jd_vec = vectorizer.transform([p["jd_text"]])
        res_vec = vectorizer.transform([p["resume_text"]])
        sim = float(cosine_similarity(jd_vec, res_vec)[0][0])

        # Raw cosine similarity is typically 0.05 to 0.50
        # Calibrate similarity to 0-100 scale:
        scaled_score = int(np.clip((sim - 0.06) / 0.35 * 100, 5, 95))
        decision = score_to_decision(scaled_score)

        results.append({
            "pair_id": p["pair_id"],
            "raw_similarity": round(sim, 4),
            "score": scaled_score,
            "decision": decision
        })
    return results


# -------------------------------------------------------------------------
# Baseline 2: BM25 Token Ranking
# -------------------------------------------------------------------------
def run_bm25_baseline(pairs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compute BM25 Okapi relevance score."""
    tokenized_resumes = [tokenize(p["resume_text"]) for p in pairs]
    bm25 = BM25Okapi(tokenized_resumes)

    raw_scores = []
    for idx, p in enumerate(pairs):
        query_tokens = tokenize(p["jd_title"] + " " + p["jd_text"][:500])
        # Score the specific resume against JD query
        all_scores = bm25.get_scores(query_tokens)
        score = float(all_scores[idx])
        raw_scores.append(score)

    # Normalize BM25 scores to 0-100
    min_s = min(raw_scores) if raw_scores else 0
    max_s = max(raw_scores) if raw_scores else 1
    denom = max(max_s - min_s, 1e-6)

    results = []
    for idx, p in enumerate(pairs):
        norm = (raw_scores[idx] - min_s) / denom
        scaled_score = int(np.clip(norm * 100, 5, 95))
        decision = score_to_decision(scaled_score)
        results.append({
            "pair_id": p["pair_id"],
            "raw_bm25": round(raw_scores[idx], 2),
            "score": scaled_score,
            "decision": decision
        })
    return results


# -------------------------------------------------------------------------
# Baseline 3: Skill / Keyword Jaccard Overlap
# -------------------------------------------------------------------------
def run_keyword_overlap_baseline(pairs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compute tech skill Jaccard overlap and JD skill coverage ratio."""
    results = []
    for p in pairs:
        jd_skills = extract_tech_keywords(p["jd_title"] + " " + p["jd_text"])
        res_skills = extract_tech_keywords(p["resume_text"])

        intersection = jd_skills & res_skills
        union = jd_skills | res_skills

        jaccard = len(intersection) / len(union) if union else 0.0
        coverage = len(intersection) / len(jd_skills) if jd_skills else 0.0

        # Composite score weighting recall / coverage higher than pure jaccard
        raw_composite = (0.7 * coverage) + (0.3 * jaccard)
        scaled_score = int(np.clip(raw_composite * 100, 5, 95))
        decision = score_to_decision(scaled_score)

        results.append({
            "pair_id": p["pair_id"],
            "jd_skills_count": len(jd_skills),
            "res_skills_count": len(res_skills),
            "overlap_count": len(intersection),
            "jaccard": round(jaccard, 3),
            "coverage": round(coverage, 3),
            "score": scaled_score,
            "decision": decision
        })
    return results


# -------------------------------------------------------------------------
# Baseline 4: Random Baseline
# -------------------------------------------------------------------------
def run_random_baseline(pairs: List[Dict[str, Any]], seed: int = 42) -> List[Dict[str, Any]]:
    """Random score generation for statistical lower-bound comparison."""
    random.seed(seed)
    results = []
    for p in pairs:
        score = random.randint(10, 90)
        decision = score_to_decision(score)
        results.append({
            "pair_id": p["pair_id"],
            "score": score,
            "decision": decision
        })
    return results


def evaluate_baselines(save_output: bool = True) -> Dict[str, Any]:
    """Execute all baselines on golden dataset and compare accuracy against human labels."""
    if not GOLDEN_JSON.exists():
        raise FileNotFoundError(f"Golden dataset not found at {GOLDEN_JSON}. Run build_golden_set.py first.")

    pairs = json.loads(GOLDEN_JSON.read_text(encoding="utf-8"))
    print(f"Running Baselines on {len(pairs)} Golden Dataset Pairs...")

    tfidf_preds = run_tfidf_baseline(pairs)
    bm25_preds = run_bm25_baseline(pairs)
    keyword_preds = run_keyword_overlap_baseline(pairs)
    random_preds = run_random_baseline(pairs)

    # Calculate basic accuracy against human_decision
    human_decisions = [p["human_decision"] for p in pairs]
    human_scores = [p["human_score"] for p in pairs]

    def _calc_acc(preds):
        correct = sum(1 for p, h in zip(preds, human_decisions) if p["decision"] == h)
        mae = float(np.mean([abs(p["score"] - h) for p, h in zip(preds, human_scores)]))
        return {
            "accuracy": round(correct / len(pairs), 4),
            "mae": round(mae, 2)
        }

    metrics_summary = {
        "tfidf": _calc_acc(tfidf_preds),
        "bm25": _calc_acc(bm25_preds),
        "keyword_overlap": _calc_acc(keyword_preds),
        "random": _calc_acc(random_preds)
    }

    full_output = {
        "metrics_summary": metrics_summary,
        "predictions": {
            "tfidf": tfidf_preds,
            "bm25": bm25_preds,
            "keyword_overlap": keyword_preds,
            "random": random_preds
        }
    }

    if save_output:
        BASELINE_RESULTS_JSON.write_text(json.dumps(full_output, indent=2), encoding="utf-8")
        print(f"✔ Saved baseline predictions to {BASELINE_RESULTS_JSON}")

    print("\n" + "="*50)
    print("TRADITIONAL BASELINE PERFORMANCE ON GOLDEN SET:")
    print("="*50)
    print(f"{'Baseline Model':<22} | {'Decision Accuracy':<18} | {'Score MAE':<10}")
    print("-" * 55)
    for model_name, m in metrics_summary.items():
        print(f"{model_name:<22} | {m['accuracy']*100:6.2f}%            | {m['mae']:6.2f} pts")
    print("="*50)

    return full_output


if __name__ == "__main__":
    evaluate_baselines(save_output=True)
