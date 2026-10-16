# src/skill_ontology.py
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np
from sentence_transformers import SentenceTransformer, util

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from config import EMBED_MODEL
except ImportError:
    EMBED_MODEL = "all-MiniLM-L6-v2"

# Load once at module level — avoid reloading on every call
_embedder = SentenceTransformer(EMBED_MODEL)

def load_ontology(path: str = "data/skill_ontology/skills.json") -> dict:
    """
    Load the technical skills ontology JSON file.
    Resolves path relative to current working directory or project root.
    """
    target = Path(path)
    if not target.exists():
        fallback = _PROJECT_ROOT / path
        if fallback.exists():
            target = fallback
        else:
            raise FileNotFoundError(f"Skill ontology file not found at '{path}' or '{fallback}'")

    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)

def flatten_ontology(ontology: dict) -> dict:
    """
    Returns flat dict: alias → canonical_skill
    e.g. "postgres"   → "postgresql"
         "k8s"        → "kubernetes"
    Ensures all canonical skills map to themselves with top priority.
    """
    flat = {}
    all_canonicals = set()

    for category, skills in ontology.items():
        if not isinstance(skills, dict):
            continue
        for canonical, aliases in skills.items():
            canon_lower = canonical.lower().strip()
            all_canonicals.add(canon_lower)
            flat[canon_lower] = canon_lower
            if isinstance(aliases, list):
                for alias in aliases:
                    if isinstance(alias, str):
                        flat[alias.lower().strip()] = canon_lower

    # Canonical skill names take precedence over being listed as an alias elsewhere
    for canon in all_canonicals:
        flat[canon] = canon

    return flat

def build_category_map(ontology: dict) -> dict:
    """
    Build lookup mapping: canonical_skill (and aliases) → technical category name
    e.g. "python"     → "programming_languages"
         "kubernetes" → "devops_sre"
         "postgresql" → "databases"
    """
    cat_map = {}
    canonical_cats = {}

    for category, skills in ontology.items():
        if not isinstance(skills, dict):
            continue
        for canonical, aliases in skills.items():
            canon_lower = canonical.lower().strip()
            canonical_cats[canon_lower] = category
            cat_map[canon_lower] = category
            if isinstance(aliases, list):
                for alias in aliases:
                    if isinstance(alias, str):
                        cat_map[alias.lower().strip()] = category

    # Ensure canonical skills retain their own primary category
    for canon, cat in canonical_cats.items():
        cat_map[canon] = cat

    return cat_map

def build_canonical_aliases(ontology: dict) -> dict:
    """
    Returns dict: canonical_skill → set of alias strings (all lowercase).
    Used for bidirectional ontology matching.
    """
    aliases_map = {}
    for category, skills in ontology.items():
        if not isinstance(skills, dict):
            continue
        for canonical, aliases in skills.items():
            canon_lower = canonical.lower().strip()
            alias_set = set()
            if isinstance(aliases, list):
                for a in aliases:
                    if isinstance(a, str):
                        alias_set.add(a.lower().strip())
            aliases_map[canon_lower] = alias_set
    return aliases_map

# Subsumption / Implication graph:
# When a candidate has a specific tool/framework, it implies mastery of broader paradigm skills.
# Crucial for recruitment screening so candidates aren't penalized when JDs ask for general concepts.
IMPLIED_SKILLS: Dict[str, List[str]] = {
    # Backend Frameworks -> RESTful APIs & Paradigms
    "fastapi": ["restful apis", "backend development", "api development", "python web frameworks"],
    "flask": ["restful apis", "backend development", "api development", "python web frameworks"],
    "django": ["backend development", "web development", "python web frameworks"],
    "django rest framework": ["restful apis", "backend development", "django", "api development"],
    "express": ["restful apis", "backend development", "node.js", "api development"],
    "express.js": ["restful apis", "backend development", "node.js", "api development"],
    "nestjs": ["restful apis", "backend development", "typescript", "api development"],
    "spring boot": ["restful apis", "backend development", "microservices", "api development"],
    "asp.net core": ["restful apis", "backend development", "api development"],
    "laravel": ["restful apis", "backend development", "api development", "php"],
    "symfony": ["restful apis", "backend development", "api development", "php"],
    "ruby on rails": ["restful apis", "backend development", "api development"],
    "gin": ["restful apis", "backend development", "go", "api development"],
    "fiber": ["restful apis", "backend development", "go", "api development"],

    # Version Control
    "git": ["version control"],
    "github": ["version control", "git"],
    "gitlab": ["version control", "git", "ci/cd"],
    "bitbucket": ["version control", "git"],
    "svn": ["version control"],

    # Relational Databases & SQL
    "postgresql": ["relational databases", "sql", "databases"],
    "mysql": ["relational databases", "sql", "databases"],
    "sqlite": ["relational databases", "sql", "databases"],
    "oracle database": ["relational databases", "sql", "databases"],
    "sql server": ["relational databases", "sql", "databases"],
    "mariadb": ["relational databases", "sql", "databases"],

    # NoSQL & In-Memory
    "mongodb": ["nosql", "databases"],
    "dynamodb": ["nosql", "databases"],
    "redis": ["caching", "in-memory database", "databases"],
    "memcached": ["caching", "in-memory database"],

    # Containers & DevOps
    "docker": ["containerization", "devops"],
    "podman": ["containerization", "devops"],
    "kubernetes": ["container orchestration", "devops", "cloud native"],
    "helm": ["container orchestration", "kubernetes", "devops"],

    # CI/CD
    "github actions": ["ci/cd", "continuous integration", "devops"],
    "gitlab ci": ["ci/cd", "continuous integration", "devops"],
    "jenkins": ["ci/cd", "continuous integration", "devops"],
    "circleci": ["ci/cd", "continuous integration", "devops"],
    "argo cd": ["ci/cd", "continuous deployment", "devops"],

    # Cloud
    "aws": ["cloud computing", "cloud platforms"],
    "google cloud platform": ["cloud computing", "cloud platforms"],
    "azure": ["cloud computing", "cloud platforms"],

    # Testing
    "pytest": ["unit testing", "automated testing", "testing"],
    "unittest": ["unit testing", "automated testing", "testing"],
    "jest": ["unit testing", "automated testing", "testing"],
    "mocha": ["unit testing", "automated testing", "testing"],
    "junit": ["unit testing", "automated testing", "testing"],
    "cypress": ["end-to-end testing", "automated testing", "testing"],
    "selenium": ["automated testing", "testing"],

    # Messaging / Queues
    "kafka": ["message brokers", "event driven architecture", "message queues"],
    "rabbitmq": ["message brokers", "event driven architecture", "message queues"],
    "celery": ["asynchronous task queues", "background jobs"],

    # AI / ML
    "pytorch": ["deep learning", "machine learning"],
    "tensorflow": ["deep learning", "machine learning"],
    "langchain": ["llm orchestration", "generative ai"],
    "llamaindex": ["llm orchestration", "rag", "generative ai"],
}

# Pre-build at import time
_ontology = load_ontology()
_flat_map = flatten_ontology(_ontology)
_category_map = build_category_map(_ontology)
_canonical_aliases = build_canonical_aliases(_ontology)
_all_canonical = sorted(list(set(_flat_map.values())))
_canonical_embs = _embedder.encode(_all_canonical, convert_to_tensor=True)

# Common noise prefix patterns in candidate & JD skill mentions
_NOISE_PREFIX_RE = re.compile(
    r"^(?:strong\s+knowledge\s+of|solid\s+understanding\s+of|hands[- ]on\s+(?:experience\s+with|with)?|"
    r"experience\s+(?:with|in)?|familiarity\s+with|knowledge\s+of|proficient\s+in|working\s+with|"
    r"expertise\s+in|understanding\s+of|deep\s+knowledge\s+of|skills?\s+in|building\s+|"
    r"developing\s+|designing\s+|implementing\s+|maintaining\s+)\s*",
    re.IGNORECASE
)

# Common noise suffix patterns
_NOISE_SUFFIX_RE = re.compile(
    r"\s*(?:development|programming|engineering|architecture|technologies|technology|"
    r"frameworks?|libraries|library|tools?|concepts?|principles?|systems?|services?)\s*$",
    re.IGNORECASE
)

def normalize_skill(skill: str) -> str:
    """
    Map any skill string to its canonical ontology name.
    Multi-tier resolution:
    1. Exact match in ontology flat map
    2. Punctuation and noise prefix/suffix stripping
    3. Multi-word compound splitting and sliding-window n-grams
    4. SBERT semantic similarity fallback (threshold: 0.68)
    """
    if not skill or not isinstance(skill, str):
        return ""

    raw = skill.lower().strip()
    if not raw:
        return ""

    # Tier 1: Direct exact match
    if raw in _flat_map:
        return _flat_map[raw]

    # Clean surrounding punctuation (brackets, parentheses, quotes, bullets, colons)
    clean = re.sub(r"^[\s\-\*\•\(\[\{,\.:;]+|[\s\-\*\•\)\]\},:;]+$", "", raw).strip()
    if clean in _flat_map:
        return _flat_map[clean]

    # Tier 2: Strip common noise prefixes ("familiarity with restful api" -> "restful api")
    stripped_prefix = _NOISE_PREFIX_RE.sub("", clean).strip()
    if stripped_prefix and stripped_prefix in _flat_map:
        return _flat_map[stripped_prefix]

    # Strip noise suffix ("react development" -> "react")
    stripped_suffix = _NOISE_SUFFIX_RE.sub("", stripped_prefix if stripped_prefix else clean).strip()
    if stripped_suffix and stripped_suffix in _flat_map:
        return _flat_map[stripped_suffix]

    # Tier 3: Sliding-window n-gram compound splitting (longest to shortest)
    # Handles "razorpay rest apis", "aws lambda functions", "git version control system"
    for candidate_str in [stripped_suffix, stripped_prefix, clean]:
        if not candidate_str:
            continue
        parts = candidate_str.split()
        n = len(parts)
        if n > 1:
            for length in range(n - 1, 0, -1):
                # Try right-aligned first (English noun phrases are right-headed)
                for start in reversed(range(n - length + 1)):
                    gram = " ".join(parts[start : start + length])
                    if gram in _flat_map:
                        return _flat_map[gram]

    # Tier 4: SBERT semantic match — find closest canonical skill
    eval_text = stripped_suffix or stripped_prefix or clean
    skill_emb = _embedder.encode(eval_text, convert_to_tensor=True)
    scores = util.cos_sim(skill_emb, _canonical_embs)[0]
    best_idx = int(scores.argmax())
    best_score = float(scores[best_idx])

    # Only map if similarity is high enough (threshold: 0.68)
    if best_score >= 0.68:
        return _all_canonical[best_idx]

    return clean  # return cleaned original if no good match

def get_skill_category(skill: str) -> Optional[str]:
    """
    Returns the technical job category for a given skill (e.g. 'databases',
    'cloud_computing', 'devops_sre', 'programming_languages').
    Normalizes the skill first before category lookup.
    """
    if not skill or not isinstance(skill, str):
        return None
    canonical = normalize_skill(skill)
    return _category_map.get(canonical.lower().strip())

def get_all_categories() -> List[str]:
    """Returns the list of all technical skill categories defined in the ontology."""
    return list(_ontology.keys())

def get_category_skills(category: str) -> Dict[str, List[str]]:
    """Returns all canonical skills and aliases within a given technical category."""
    return _ontology.get(category, {})

def match_skills(jd_skills: List[str], resume_skills: List[str], threshold: float = 0.68) -> dict:
    """
    Semantically match JD requirements against resume skills.
    Multi-tier evaluation:
    1. Exact canonical equality (score: 1.0)
    2. Subsumption / Implication graph (score: 0.95)
       e.g., FastAPI / Flask / Express implies RESTful APIs; Git implies Version Control
    3. Ontology alias containment (score: 0.95)
    4. Substring / compound containment (score: 0.95)
    5. SBERT cosine similarity (score: >= threshold)
    """
    if not jd_skills:
        return {
            "matches": [],
            "gaps": [],
            "match_rate": 0.0
        }

    results = []

    # Clean and filter empty skills
    clean_resume = [s.strip() for s in resume_skills if s and isinstance(s, str) and s.strip()]

    # Pre-normalize resume skills to avoid redundant lookups
    resume_canonical_pairs = [(res_skill, normalize_skill(res_skill)) for res_skill in clean_resume]

    for jd_skill in jd_skills:
        if not jd_skill or not isinstance(jd_skill, str) or not jd_skill.strip():
            continue

        jd_clean = jd_skill.strip()
        jd_canonical = normalize_skill(jd_clean)
        jd_emb = _embedder.encode(jd_canonical, convert_to_tensor=True)

        best_match = None
        best_score = 0.0
        match_found = False

        jd_canon_lower = jd_canonical.lower().strip()
        jd_clean_lower = jd_clean.lower().strip()
        jd_aliases = _canonical_aliases.get(jd_canon_lower, set())

        for res_skill, res_canonical in resume_canonical_pairs:
            res_canon_lower = res_canonical.lower().strip()
            res_skill_lower = res_skill.lower().strip()

            # Rule 1: Exact canonical equality
            if jd_canon_lower == res_canon_lower:
                score = 1.0
            # Rule 2: Subsumption / Implication
            # e.g. candidate has fastapi, JD requires restful apis
            elif (
                res_canon_lower in IMPLIED_SKILLS and jd_canon_lower in IMPLIED_SKILLS[res_canon_lower]
            ) or (
                res_skill_lower in IMPLIED_SKILLS and jd_canon_lower in IMPLIED_SKILLS[res_skill_lower]
            ):
                score = 0.95
            # Rule 3: Ontology alias lookup
            # JD canonical lists the candidate's skill or canonical as an alias
            elif (
                res_canon_lower in jd_aliases
                or res_skill_lower in jd_aliases
            ):
                score = 0.95
            # Rule 4: Substring / compound containment
            # e.g. "rest apis" in "razorpay rest apis"
            # Require minimum length of 4 or whole word boundary to prevent false substring matches (e.g. "go" in "mongodb")
            elif (
                (len(jd_canon_lower) >= 4 and jd_canon_lower in res_skill_lower)
                or (len(jd_clean_lower) >= 4 and jd_clean_lower in res_skill_lower)
                or bool(re.search(r'\b' + re.escape(jd_canon_lower) + r'\b', res_skill_lower))
                or bool(re.search(r'\b' + re.escape(jd_clean_lower) + r'\b', res_skill_lower))
            ):
                score = 0.95
            else:
                # Rule 5: Semantic cosine embedding similarity
                res_emb = _embedder.encode(res_canonical, convert_to_tensor=True)
                score = float(util.cos_sim(jd_emb, res_emb))

            if score > best_score:
                best_score = score
                best_match = res_skill

            if best_score >= 1.0:
                break

        results.append({
            "jd_skill": jd_skill,
            "jd_canonical": jd_canonical,
            "resume_match": best_match,
            "similarity": round(best_score, 3),
            "matched": best_score >= threshold
        })

    matched = [r for r in results if r["matched"]]
    missing = [r for r in results if not r["matched"]]

    return {
        "matches": matched,
        "gaps": missing,
        "match_rate": round(len(matched) / max(len(results), 1), 3)
    }
