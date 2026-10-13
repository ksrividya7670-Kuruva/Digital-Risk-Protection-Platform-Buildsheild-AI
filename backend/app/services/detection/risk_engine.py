"""
Risk Engine — Orchestrator for all seven detection signals.

This module:
  1. Accepts a brand + candidate + evidence data bundle
  2. Calls each of the seven signal calculators
  3. Aggregates weighted scores into a final total (0–100)
  4. Classifies the risk level
  5. Calculates a confidence score (independent of risk)
  6. Generates a deterministic human-readable explanation
  7. Returns a DetectionResult ready for DB persistence

CRITICAL RULES:
  - No LLM calls here. This module is 100% deterministic.
  - No external HTTP requests.
  - Every number in the output is traceable to a signal calculation.
  - Missing data → signal scores 0, never inflated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.services.detection.contracts import (
    DetectionResult,
    SignalResult,
    SIGNAL_WEIGHTS,
    classify_risk,
    calculate_confidence,
)
from app.services.detection.text_utils import contains_suspicious_claims, text_or_empty
from app.services.detection import (
    identity_similarity,
    visual_similarity,
    content_similarity,
    link_risk,
    account_anomaly,
    evidence_score,
    activity_anomaly,
)
from app.services.detection.evidence_score import EvidenceItem


@dataclass
class CandidateBundle:
    """
    All data the risk engine needs to score one candidate.
    Assembled by DetectionService from the database.
    """
    # IDs
    candidate_id: str
    brand_id: str
    candidate_type: str                    # "SOCIAL_PROFILE" | "MOBILE_APP"

    # Brand identity
    brand_name: str
    brand_description: Optional[str]
    brand_official_handles: list[str]      # all known handles across platforms
    brand_official_domain: Optional[str]
    brand_official_email_domain: Optional[str]
    brand_logo_hash: Optional[str]
    brand_official_developer_name: Optional[str]

    # Candidate identity
    candidate_username: Optional[str]
    candidate_display_name: Optional[str]
    candidate_name: Optional[str]
    candidate_bio: Optional[str]
    candidate_website: Optional[str]
    candidate_email: Optional[str]
    candidate_icon_hash: Optional[str]

    # Social-specific
    follower_count: Optional[int] = None
    following_count: Optional[int] = None
    account_age_days: Optional[int] = None
    is_verified: Optional[bool] = None

    # App-specific
    package_name: Optional[str] = None
    developer_name: Optional[str] = None
    developer_email: Optional[str] = None
    app_version: Optional[str] = None
    install_count: Optional[int] = None

    # Evidence records from DB
    evidence_items: list[EvidenceItem] = field(default_factory=list)


def run(bundle: CandidateBundle) -> DetectionResult:
    """
    Execute all seven signal calculators and produce a DetectionResult.
    This function is deterministic: same input always produces same output.
    """

    # Pre-compute whether the candidate claims to be official
    bio_text = text_or_empty(bundle.candidate_bio)
    name_text = text_or_empty(bundle.candidate_name) + " " + text_or_empty(bundle.candidate_display_name)
    claims_official = contains_suspicious_claims(bio_text + " " + name_text)[0]

    # Extract visual evidence scores from evidence items
    visual_evidence_scores = [
        item.similarity_score
        for item in bundle.evidence_items
        if item.evidence_type in ("LOGO_SIMILARITY", "ICON_SIMILARITY")
        and item.similarity_score is not None
    ]

    # ── Run all seven signals ─────────────────────────────────────────────────

    sig_identity = identity_similarity.calculate(
        brand_name=bundle.brand_name,
        brand_official_handles=bundle.brand_official_handles,
        candidate_username=bundle.candidate_username,
        candidate_display_name=bundle.candidate_display_name,
        candidate_name=bundle.candidate_name,
    )

    sig_visual = visual_similarity.calculate(
        brand_logo_hash=bundle.brand_logo_hash,
        candidate_icon_hash=bundle.candidate_icon_hash,
        evidence_visual_scores=visual_evidence_scores,
    )

    sig_content = content_similarity.calculate(
        brand_name=bundle.brand_name,
        brand_description=bundle.brand_description,
        candidate_bio=bundle.candidate_bio,
        candidate_name=bundle.candidate_name,
    )

    sig_link = link_risk.calculate(
        brand_name=bundle.brand_name,
        official_domain=bundle.brand_official_domain,
        official_developer_name=bundle.brand_official_developer_name,
        official_email_domain=bundle.brand_official_email_domain,
        candidate_website=bundle.candidate_website,
        candidate_email=bundle.candidate_email,
        candidate_package_name=bundle.package_name,
        candidate_developer_name=bundle.developer_name,
        candidate_developer_email=bundle.developer_email,
    )

    sig_anomaly = account_anomaly.calculate(
        candidate_type=bundle.candidate_type,
        account_age_days=bundle.account_age_days,
        follower_count=bundle.follower_count,
        following_count=bundle.following_count,
        is_verified=bundle.is_verified,
        bio_description=bundle.candidate_bio,
        display_name=bundle.candidate_display_name,
        developer_name=bundle.developer_name,
        official_developer_name=bundle.brand_official_developer_name,
        install_count=bundle.install_count,
        app_version=bundle.app_version,
        claims_to_be_official=claims_official,
    )

    sig_evidence = evidence_score.calculate(
        evidence_items=bundle.evidence_items,
    )

    sig_activity = activity_anomaly.calculate(
        candidate_type=bundle.candidate_type,
        account_age_days=bundle.account_age_days,
        follower_count=bundle.follower_count,
        following_count=bundle.following_count,
        install_count=bundle.install_count,
        bio_description=bundle.candidate_bio,
    )

    signals = [
        sig_identity,
        sig_visual,
        sig_content,
        sig_link,
        sig_anomaly,
        sig_evidence,
        sig_activity,
    ]

    # ── Calculate total score ─────────────────────────────────────────────────
    total_float = sum(s.weighted_score for s in signals)
    total_score = max(0, min(100, round(total_float)))

    # ── Classify risk level ───────────────────────────────────────────────────
    risk_level = classify_risk(total_score)

    # ── Calculate confidence (independent of score) ───────────────────────────
    confidence = calculate_confidence(signals, len(bundle.evidence_items))

    # ── Build reasons and explanation ─────────────────────────────────────────
    reasons = _build_reasons(signals, total_score, risk_level)
    explanation = _build_explanation(signals, total_score, risk_level, bundle.brand_name)

    return DetectionResult(
        candidate_id=bundle.candidate_id,
        brand_id=bundle.brand_id,
        total_score=total_score,
        risk_level=risk_level,
        confidence=confidence,
        signals=signals,
        reasons=reasons,
        explanation=explanation,
        identity_similarity_score=sig_identity.weighted_score,
        visual_similarity_score=sig_visual.weighted_score,
        content_similarity_score=sig_content.weighted_score,
        link_contact_score=sig_link.weighted_score,
        anomaly_score=sig_anomaly.weighted_score,
        evidence_score_val=sig_evidence.weighted_score,
        activity_score=sig_activity.weighted_score,
    )


def _build_reasons(signals: list[SignalResult], total_score: int, risk_level: str) -> list[str]:
    """
    Build a list of the top firing reasons ordered by signal contribution.
    Only includes signals that actually fired (weighted_score > 0).
    """
    firing = sorted(
        [s for s in signals if s.weighted_score > 0],
        key=lambda s: s.weighted_score,
        reverse=True,
    )
    reasons: list[str] = []
    for sig in firing[:5]:  # top 5 contributors
        pct = round((sig.weighted_score / max(total_score, 1)) * 100)
        reasons.append(
            f"[{sig.signal_name.replace('_', ' ').title()} — "
            f"{sig.weighted_score:.1f}/{sig.weight}pts] {sig.reason}"
        )
    return reasons


def _build_explanation(
    signals: list[SignalResult],
    total_score: int,
    risk_level: str,
    brand_name: str,
) -> str:
    """
    Generate a concise, deterministic explanation of the risk finding.
    Based ONLY on signals that actually fired.
    No LLM, no hallucination.
    """
    firing_names = [
        s.signal_name.replace("_", " ")
        for s in signals
        if s.weighted_score > (s.weight * 0.3)  # fired at >30% of max
    ]

    if not firing_names:
        return (
            f"Risk score {total_score}/100 ({risk_level}). "
            f"No strong individual signals fired. "
            f"Candidate shows low similarity to '{brand_name}'."
        )

    level_phrase = {
        "CRITICAL": "strongly suspected of impersonating",
        "HIGH":     "shows strong indicators of impersonating",
        "MEDIUM":   "shows moderate indicators of resembling",
        "LOW":      "shows limited similarity to",
    }[risk_level]

    top_signals = ", ".join(firing_names[:3])
    suffix = f" and {len(firing_names) - 3} other signals" if len(firing_names) > 3 else ""

    return (
        f"Risk score {total_score}/100 ({risk_level}). "
        f"This candidate {level_phrase} '{brand_name}' "
        f"based on: {top_signals}{suffix}."
    )
