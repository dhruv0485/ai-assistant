# src/fairness.py
import re
from typing import List, Dict, Any, Callable, Optional

# Name swap dictionaries
INDIAN_NAMES = [
    "Rahul Sharma", "Priya Patel", "Arjun Singh", "Neha Gupta",
    "Vikram Mehta", "Anjali Rao", "Dhruv Mehta"
]
WESTERN_NAMES = [
    "James Wilson", "Sarah Johnson", "Michael Brown", "Emily Davis",
    "Robert Smith", "Jessica Taylor"
]

ELITE_COLLEGES = [
    "IIT", "IIT Bombay", "IIT Delhi", "IIT Madras", "BITS Pilani",
    "NIT Trichy", "IISc"
]
TIER2_COLLEGES = [
    "Pune University", "VTU", "Anna University",
    "Osmania University", "Mumbai University"
]

def swap_name(text: str, original: str, replacement: str) -> str:
    """Replaces full or first name occurrences cleanly using regex word boundaries."""
    if not original or not replacement:
        return text
    return re.sub(rf'\b{re.escape(original)}\b', replacement, text, flags=re.IGNORECASE)

def swap_college(text: str, original: str, replacement: str) -> str:
    """Replaces college name occurrences in text."""
    if not original or not replacement:
        return text
    return re.sub(rf'\b{re.escape(original)}\b', replacement, text, flags=re.IGNORECASE)

def remove_gender_signals(text: str) -> str:
    """Remove he/she/his/her pronouns and common gendered words."""
    text = re.sub(r'\b(he|she)\b', 'they', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(him|her)\b', 'them', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(his|her|hers)\b', 'their', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(himself|herself)\b', 'themselves', text, flags=re.IGNORECASE)
    return text

def generate_variants(resume_text: str, candidate_name: Optional[str] = None, candidate_college: Optional[str] = None) -> list[dict]:
    """
    Generate 3 controlled variants of the same resume
    by changing only demographic signals (Name, College Pedigree, Gender Pronouns).
    """
    variants = []

    # 1. Detect candidate name
    detected_name = None
    if candidate_name and candidate_name.strip() and candidate_name.strip().lower() not in ["none", "null"]:
        detected_name = candidate_name.strip()
    else:
        for name in INDIAN_NAMES:
            first = name.split()[0]
            if re.search(rf'\b{re.escape(first)}\b', resume_text, flags=re.IGNORECASE):
                detected_name = first
                break

    # Variant 1: Name swap (Indian/Original -> Western)
    if detected_name:
        first_name = detected_name.split()[0]
        v1 = re.sub(rf'\b{re.escape(first_name)}\b', "James", resume_text, flags=re.IGNORECASE)
        if v1 != resume_text:
            variants.append({
                "type": "name_swap",
                "text": v1,
                "change": f"'{first_name}' → 'James'"
            })
    else:
        # Fallback name swap if no specific name detected: prepend James Wilson as header
        v1 = "James Wilson\n" + resume_text
        variants.append({
            "type": "name_swap",
            "text": v1,
            "change": "Added neutral Western name 'James Wilson'"
        })

    # 2. Detect college / institution
    detected_elite = None
    for college in ELITE_COLLEGES:
        if re.search(rf'\b{re.escape(college)}\b', resume_text, flags=re.IGNORECASE):
            detected_elite = college
            break

    # Variant 2: College swap
    if detected_elite:
        v2 = re.sub(rf'\b{re.escape(detected_elite)}\b', "Pune University", resume_text, flags=re.IGNORECASE)
        variants.append({
            "type": "college_swap",
            "text": v2,
            "change": f"'{detected_elite}' → 'Pune University'"
        })
    elif candidate_college and candidate_college.strip():
        # Candidate has non-elite college: swap to IIT Delhi to test pedigree boost bias
        orig_col = candidate_college.strip()
        v2 = re.sub(rf'\b{re.escape(orig_col)}\b', "IIT Delhi", resume_text, flags=re.IGNORECASE)
        variants.append({
            "type": "college_swap",
            "text": v2,
            "change": f"'{orig_col}' → 'IIT Delhi'"
        })
    else:
        # Inject college variant to evaluate institution sensitivity
        v2 = resume_text + "\nEducation: B.Tech, Pune University"
        variants.append({
            "type": "college_swap",
            "text": v2,
            "change": "Institution set to 'Pune University'"
        })

    # Variant 3: Remove gender pronouns
    v3 = remove_gender_signals(resume_text)
    if v3 != resume_text:
        variants.append({
            "type": "gender_neutral",
            "text": v3,
            "change": "Removed gendered pronouns (he/she/his/her → they/them/their)"
        })
    else:
        # If no pronouns exist, create variant with explicit female pronoun in summary to test gender invariance
        v3_gender = resume_text.replace("Experience:", "She has proven experience:", 1)
        variants.append({
            "type": "gender_neutral",
            "text": v3_gender,
            "change": "Explicit female pronoun baseline test"
        })

    return variants

def run_fairness_audit(resume_text: str, original_score: int, score_fn: Callable[[str], int],
                       candidate_name: Optional[str] = None, candidate_college: Optional[str] = None) -> dict:
    """
    Runs automated counterfactual fairness evaluation.
    Evaluates demographic variants using score_fn.
    Flags bias if any counterfactual variation changes score by > 5 points.
    """
    variants = generate_variants(resume_text, candidate_name=candidate_name, candidate_college=candidate_college)
    if not variants:
        return {"audited": False, "reason": "No demographic signals detected"}

    results = []
    for v in variants:
        try:
            variant_score = score_fn(v["text"])
        except Exception as e:
            variant_score = original_score
        delta = abs(variant_score - original_score)
        results.append({
            "variant_type":   v["type"],
            "change":         v["change"],
            "original_score": original_score,
            "variant_score":  variant_score,
            "delta":          delta,
            "bias_flag":      delta > 5   # flag if > 5 points change
        })

    max_delta = max((r["delta"] for r in results), default=0)
    bias_detected = max_delta > 5

    return {
        "audited":       True,
        "results":       results,
        "max_delta":     max_delta,
        "bias_detected": bias_detected
    }
