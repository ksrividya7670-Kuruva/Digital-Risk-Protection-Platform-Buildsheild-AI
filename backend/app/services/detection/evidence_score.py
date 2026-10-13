"""
Signal 6 — Evidence / Reputation Score (weight: 10%)

Aggregates risk contribution from evidence records already stored in the DB.

Rules:
  - Evidence score is ZERO if no evidence records exist.
    (Absence of evidence ≠ evidence of absence of threat.)
  - Each evidence record contributes based on its severity and similarity_score.
  - The final score is the weighted mean of individual evidence contributions,
    boosted by evidence count (more evidence = higher confidence in the signal).
  - This signal reflects STORED evidence only — the engine never manufactures it.
"""

from __future__ import annotations
from typing import NamedTuple

from app.services.detection.contracts import SignalResult, SIGNAL_WEIGHTS

SIGNAL_NAME = "evidence_score"
WEIGHT = SIGNAL_WEIGHTS[SIGNAL_NAME]

# Base contribution per severity level (0.0–1.0 scale)
_SEVERITY_BASE = {
    "CRITICAL": 1.00,
    "HIGH":     0.75,
    "MEDIUM":   0.50,
    "LOW":      0.25,
}


class EvidenceItem(NamedTuple):
    evidence_type: str
    severity: str
    similarity_score: float | None   # 0.0–1.0 if available, else None
    title: str


def calculate(*, evidence_items: list[EvidenceItem]) -> SignalResult:
    """
    Aggregate stored evidence into a single risk signal.
    """
    if not evidence_items:
        return SignalResult(
            signal_name=SIGNAL_NAME,
            raw_score=0.0,
            weight=WEIGHT,
            weighted_score=0.0,
            reason=(
                "No evidence records found. "
                "Score is zero — absence of evidence does not indicate safety."
            ),
            metadata={"evidence_count": 0},
        )

    individual_scores: list[float] = []
    reasons: list[str] = []
    metadata: dict = {
        "evidence_count": len(evidence_items),
        "evidence_types": [],
    }

    for item in evidence_items:
        base = _SEVERITY_BASE.get(item.severity.upper(), 0.25)
        # If we have a similarity_score, blend it with the severity base
        if item.similarity_score is not None:
            score = 0.5 * base + 0.5 * float(item.similarity_score)
        else:
            score = base
        individual_scores.append(score)
        metadata["evidence_types"].append(item.evidence_type)

        if item.severity.upper() in ("CRITICAL", "HIGH"):
            reasons.append(
                f"{item.severity} evidence: {item.title}."
            )

    # Weighted mean — all pieces count equally
    mean_score = sum(individual_scores) / len(individual_scores)

    # Count bonus: more independent evidence raises the signal
    count_bonus = min(0.20, (len(evidence_items) - 1) * 0.05)
    raw_score = round(min(1.0, mean_score + count_bonus), 4)

    if not reasons:
        reasons.append(
            f"{len(evidence_items)} evidence record(s) with low-to-medium severity found."
        )

    metadata["mean_evidence_score"] = round(mean_score, 3)
    metadata["count_bonus"] = round(count_bonus, 3)

    return SignalResult(
        signal_name=SIGNAL_NAME,
        raw_score=raw_score,
        weight=WEIGHT,
        weighted_score=round(raw_score * WEIGHT, 4),
        reason="; ".join(reasons),
        metadata=metadata,
    )
