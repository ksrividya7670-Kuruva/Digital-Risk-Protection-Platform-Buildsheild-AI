"""
Signal 7 — Activity Anomaly (weight: 5%)

Lightweight deterministic activity signal using available candidate metadata.

Key rule:
  If no activity data is available, return score=0 with a clear explanation.
  Missing activity data NEVER inflates the risk score.

Available activity indicators (all optional):
  - follower_count spike relative to account_age
  - very high following_count on a new account (follow-farming)
  - install_count relative to app_age for mobile apps
  - bio/description contains urgency or time-pressure language
"""

from __future__ import annotations
from typing import Optional

from app.services.detection.contracts import SignalResult, SIGNAL_WEIGHTS
from app.services.detection.text_utils import text_or_empty

SIGNAL_NAME = "activity_anomaly"
WEIGHT = SIGNAL_WEIGHTS[SIGNAL_NAME]

# Words suggesting urgency / artificial pressure — used in scam accounts
_URGENCY_TERMS = [
    "urgent", "limited time", "expires", "act now", "last chance",
    "today only", "24 hours", "48 hours", "hurry", "immediately",
    "dm now", "contact now", "apply now", "click now",
    "free", "giveaway", "prize", "reward", "winner",
]


def calculate(
    *,
    candidate_type: str,
    account_age_days: Optional[int],
    follower_count: Optional[int],
    following_count: Optional[int],
    install_count: Optional[int],
    bio_description: Optional[str],
) -> SignalResult:
    """
    Calculate activity anomaly score. Returns 0 if no data available.
    """
    reasons: list[str] = []
    metadata: dict = {}
    components: list[float] = []

    # ── Follower growth rate anomaly ──────────────────────────────────────────
    if account_age_days is not None and follower_count is not None and account_age_days > 0:
        daily_growth = follower_count / account_age_days
        metadata["daily_follower_growth"] = round(daily_growth, 1)

        if daily_growth > 500:
            components.append(0.80)
            reasons.append(
                f"Unusually rapid follower growth: ~{daily_growth:.0f} followers/day "
                f"— may indicate artificial inflation."
            )
        elif daily_growth > 100:
            components.append(0.45)
            reasons.append(
                f"High follower growth rate: ~{daily_growth:.0f} followers/day."
            )

    # ── Follow-farming: following >> followers on new account ─────────────────
    if (
        account_age_days is not None and account_age_days < 60
        and following_count is not None and following_count > 500
        and follower_count is not None and follower_count < 200
    ):
        components.append(0.55)
        reasons.append(
            f"New account ({account_age_days} days) following {following_count} accounts "
            f"with only {follower_count} followers — typical follow-farming pattern."
        )
        metadata["follow_farming"] = True

    # ── App install anomaly ────────────────────────────────────────────────────
    if candidate_type == "MOBILE_APP" and account_age_days is not None and install_count is not None:
        if account_age_days > 0:
            daily_installs = install_count / account_age_days
            metadata["daily_installs"] = round(daily_installs, 1)
            if daily_installs > 1000 and account_age_days < 14:
                components.append(0.60)
                reasons.append(
                    f"App gained ~{daily_installs:.0f} installs/day in its first "
                    f"{account_age_days} days — unusually rapid adoption."
                )

    # ── Urgency language in bio ────────────────────────────────────────────────
    bio = text_or_empty(bio_description).lower()
    if bio:
        urgency_hits = [term for term in _URGENCY_TERMS if term in bio]
        if urgency_hits:
            urgency_score = min(0.70, len(urgency_hits) * 0.15)
            components.append(urgency_score)
            metadata["urgency_terms"] = urgency_hits[:5]
            reasons.append(
                f"Bio/description contains urgency or pressure language: "
                f"{', '.join(urgency_hits[:3])}."
            )

    # ── Return ────────────────────────────────────────────────────────────────
    if not components:
        return SignalResult(
            signal_name=SIGNAL_NAME,
            raw_score=0.0,
            weight=WEIGHT,
            weighted_score=0.0,
            reason="Insufficient activity data for anomaly detection.",
            metadata=metadata,
        )

    raw_score = round(min(1.0, sum(components) / len(components)), 4)

    return SignalResult(
        signal_name=SIGNAL_NAME,
        raw_score=raw_score,
        weight=WEIGHT,
        weighted_score=round(raw_score * WEIGHT, 4),
        reason="; ".join(reasons),
        metadata=metadata,
    )
