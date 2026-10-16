# src/decision.py
import sys
from pathlib import Path
from typing import Dict, Any

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import ADVANCE_THRESHOLD, ESCALATE_THRESHOLD

def make_decision(score_result: dict, jd_extracted: dict) -> dict:
    """
    Policy:
    >= 65             → ADVANCE    (auto-shortlist)
    40-64, HIGH conf  → ESCALATE   (human review)
    40-64, LOW conf   → ESCALATE   (ambiguous resume)
    < 40              → REJECT     (with note — never silently drop)
    
    Key rule: when in doubt, ESCALATE. Never hard-reject a borderline case.
    """
    score      = score_result.get("score", 0)
    confidence = score_result.get("confidence", "HIGH")
    gaps       = score_result.get("gaps", [])

    # Check must-have blockers
    must_haves_met = score_result.get("must_have_met", [])
    critical_gaps  = [m for m in must_haves_met if not m.get("met")]

    # Hard blocker: missing more than half of must-haves + low score
    hard_blocked = (
        len(must_haves_met) > 0
        and len(critical_gaps) > len(must_haves_met) / 2
        and score < ESCALATE_THRESHOLD
    )

    if hard_blocked:
        decision = "REJECT"
        reason   = f"Missing {len(critical_gaps)} critical requirements: " + \
                   ", ".join([g.get("skill", "") for g in critical_gaps[:3]])

    elif score >= ADVANCE_THRESHOLD and confidence == "HIGH":
        decision = "ADVANCE"
        strengths = score_result.get("strengths", [])
        reason   = f"Strong match (score {score}). " + \
                   (strengths[0] if strengths else "Meets core requirements.")

    elif score >= ADVANCE_THRESHOLD and confidence == "LOW":
        # High score but uncertain — let human verify
        decision = "ESCALATE"
        reason   = f"High score ({score}) but ambiguous resume — confidence LOW. " + \
                   "Recommend human review to verify claims."

    elif score >= ESCALATE_THRESHOLD:
        decision = "ESCALATE"
        reason   = f"Partial match (score {score}). Gaps: {', '.join(gaps[:2])}. " + \
                   "Human review recommended."
    else:
        decision = "REJECT"
        reason   = f"Weak match (score {score}). Key gaps: {', '.join(gaps[:3])}."

    return {
        "decision":       decision,
        "reason":         reason,
        "score":          score,
        "confidence":     confidence,
        "critical_gaps":  [g.get("skill", "") for g in critical_gaps]
    }
