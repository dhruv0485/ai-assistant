# src/jd_normalizer.py
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from config import EMBED_MODEL
except ImportError:
    EMBED_MODEL = "all-MiniLM-L6-v2"

_embedder = SentenceTransformer(EMBED_MODEL)
_templates: List[Dict[str, Any]] = []
_index: Optional[faiss.IndexFlatL2] = None

def build_rich_text(t: dict) -> str:
    """Format a template dictionary into a rich semantic string for embedding."""
    must = ", ".join(t.get("must_haves", []))
    nice = ", ".join(t.get("nice_to_haves", []))
    tmpl_text = t.get("template_text", "")
    return f"{tmpl_text}. Required: {must}. Preferred: {nice}"

build_template_text = build_rich_text

def build_jd_index(path: str = "data/skill_ontology/jd_templates.json"):
    """
    Loads standardized role templates from JSON and builds a FAISS FlatL2 vector index.
    """
    global _templates, _index
    target = Path(path)
    if not target.exists():
        fallback = _PROJECT_ROOT / path
        if fallback.exists():
            target = fallback
        else:
            raise FileNotFoundError(f"JD templates file not found at '{path}' or '{fallback}'")

    with open(target, "r", encoding="utf-8") as f:
        _templates = json.load(f)

    texts = [build_rich_text(t) for t in _templates]
    embs = _embedder.encode(texts, convert_to_numpy=True).astype("float32")

    _index = faiss.IndexFlatL2(embs.shape[1])
    _index.add(embs)
    print(f"[jd_normalizer] Built FAISS index with {len(_templates)} templates")

def normalize_jd(jd_text: str, top_k: int = 1) -> dict:
    """
    Find the closest standard JD template for a given raw JD text using FAISS.
    Returns the matched canonical role, similarity score, canonical must-haves,
    nice-to-haves, and minimum required years of experience.
    """
    if _index is None or not _templates:
        build_jd_index()

    if not jd_text or not isinstance(jd_text, str) or not jd_text.strip():
        return {
            "matched_role": None,
            "similarity": 0.0,
            "canonical_musts": [],
            "canonical_nices": [],
            "min_years": 0
        }

    query_emb = _embedder.encode([jd_text[:2000]], convert_to_numpy=True).astype("float32")
    distances, indices = _index.search(query_emb, max(top_k, 1))

    best_idx = indices[0][0]
    best_dist = distances[0][0]
    best_template = _templates[best_idx]
    similarity = float(1 / (1 + best_dist))  # convert L2 distance to similarity score in (0, 1]

    result = {
        "matched_role": best_template["role"],
        "similarity": round(similarity, 3),
        "canonical_musts": best_template.get("must_haves", []),
        "canonical_nices": best_template.get("nice_to_haves", []),
        "min_years": best_template.get("min_years", 0)
    }

    if top_k > 1:
        top_matches = []
        for i, d in zip(indices[0], distances[0]):
            t = _templates[i]
            sim = float(1 / (1 + d))
            top_matches.append({
                "role": t["role"],
                "similarity": round(sim, 3),
                "min_years": t.get("min_years", 0),
                "canonical_musts": t.get("must_haves", []),
                "canonical_nices": t.get("nice_to_haves", [])
            })
        result["top_matches"] = top_matches

    return result

def get_all_template_roles() -> List[str]:
    """Returns a list of all 130 standardized role names in the ontology."""
    if not _templates:
        build_jd_index()
    return [t["role"] for t in _templates]

def get_template_by_role(role: str) -> Optional[dict]:
    """Fetch canonical requirements for a specific standard role name."""
    if not _templates:
        build_jd_index()
    for t in _templates:
        if t["role"].lower() == role.lower():
            return t
    return None

# Build index on import
build_jd_index()
