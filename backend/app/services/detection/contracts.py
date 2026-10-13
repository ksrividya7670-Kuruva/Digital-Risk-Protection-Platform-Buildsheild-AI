"""
Detection engine contracts — shared data structures.

These are pure Python dataclasses, not ORM models.
They represent the internal output of the detection engine
before being persisted to the database.

RULE: The LLM never touches these structures.
      All values are produced by deterministic signal calculators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ── Risk level thresholds ─────────────────────────────────────────────────────
# Defined once here; imported everywhere. No magic numbers elsewhere.

RISK_THRESHOLDS = {
    "CRITICAL": 80,
    "HIGH": 60,
    "MEDIUM": 40,
    "LOW": 0,
}

# ── Signal weights — must sum to exactly 100 ─────────────────────────────────
# Initial engineering proposal for the hackathon MVP.
# These are NOT prescribed by the hackathon challenge specification.
# They are tunable and should be revisited with real-world data.

SIGNAL_WEIGHTS = {
    "identity_similarity":  25,
    "visual_similarity":    20,
    "content_similarity":   15,
    "link_risk":            15,
    "account_anomaly":      10,
    "evidence_score":       10,
    "activity_anomaly":      5,
}

assert sum(SIGNAL_WEIGHTS.values()) == 100, (
    f"Signal weights must sum to 100, got {sum(SIGNAL_WEIGHTS.values())}"
)


@dataclass
class SignalResult:
    """
    Output of a single signal calculator.

    raw_score    : 0.0–1.0  — how suspicious this signal is (pre-weighting)
    weighted_score: 0.0–max_weight — contribution to final total score
    reason       : Human-readable explanation of the signal finding
    metadata     : Optional extra detail (for debugging / display)
    """
    signal_name: str
    raw_score: float          # 0.0 → 1.0
    weight: int               # signal weight (e.g. 25 for identity)
    weighted_score: float     # raw_score * weight  → contributes to 0–100 total
    reason: str
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Clamp to valid ranges
        self.raw_score = max(0.0, min(1.0, self.raw_score))
        self.weighted_score = round(self.raw_score * self.weight, 4)


@dataclass
class DetectionResult:
    """
    Complete output of the detection engine for one candidate.

    This is the authoritative result before DB persistence.
    The AI explanation layer reads this structure — it never modifies
    the numerical fields.
    """
    candidate_id: str
    brand_id: str

    # Aggregate score
    total_score: int           # 0–100, rounded integer
    risk_level: str            # LOW / MEDIUM / HIGH / CRITICAL
    confidence: float          # 0.0–1.0, independent of risk_score

    # Individual signals
    signals: list[SignalResult] = field(default_factory=list)

    # Deterministic explanation (engine-generated, not LLM)
    reasons: list[str] = field(default_factory=list)
    explanation: str = ""

    # Component scores (convenience — mirrors DB columns)
    identity_similarity_score: float = 0.0
    visual_similarity_score: float = 0.0
    content_similarity_score: float = 0.0
    link_contact_score: float = 0.0
    anomaly_score: float = 0.0
    evidence_score_val: float = 0.0
    activity_score: float = 0.0


def classify_risk(score: float) -> str:
    """Map a numeric score 0–100 to a risk level string."""
    if score >= RISK_THRESHOLDS["CRITICAL"]:
        return "CRITICAL"
    if score >= RISK_THRESHOLDS["HIGH"]:
        return "HIGH"
    if score >= RISK_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    return "LOW"


def calculate_confidence(signals: list[SignalResult], evidence_count: int) -> float:
    """
    Calculate a confidence value that is INDEPENDENT of the risk score.

    Confidence reflects how much evidence we have to support the assessment.
    A high-risk candidate with only one weak signal has low confidence.
    A low-risk candidate with many independent signals has high confidence.

    Scale: 0.0 (no evidence) → 1.0 (strong multi-signal evidence)
    """
    if not signals:
        return 0.0

    # Count signals that actually fired (raw_score > 0.1)
    fired = [s for s in signals if s.raw_score > 0.1]
    signal_count_factor = min(len(fired) / len(signals), 1.0)

    # Average raw score of fired signals (how strong are they)
    if fired:
        avg_strength = sum(s.raw_score for s in fired) / len(fired)
    else:
        avg_strength = 0.0

    # Evidence count bonus (having DB evidence raises confidence)
    evidence_factor = min(evidence_count / 5.0, 1.0)  # saturates at 5+ items

    # Weighted combination
    confidence = (
        0.40 * signal_count_factor +
        0.40 * avg_strength +
        0.20 * evidence_factor
    )
    return round(min(confidence, 1.0), 3)
