"""
Signal 3 — Content / Bio Similarity (weight: 15%)

Compares the candidate's bio/description against the official brand
description using deterministic text techniques.

Also checks for suspicious self-referential claims that impersonators
commonly use ("official", "support", "verified", etc.)

All comparisons are against provided text — no external calls.
"""

from __future__ import annotations

from app.services.detection.contracts import SignalResult, SIGNAL_WEIGHTS
from app.services.detection.text_utils import (
    jaccard_similarity,
    token_overlap_ratio,
    ngram_similarity,
    contains_suspicious_claims,
    keyword_overlap_score,
    normalize_text,
    text_or_empty,
)

SIGNAL_NAME = "content_similarity"
WEIGHT = SIGNAL_WEIGHTS[SIGNAL_NAME]

# Brand-related keywords that impersonators frequently copy
_OFFICIAL_CLAIM_PHRASES = [
    "official", "verified", "real", "genuine", "authentic",
    "support", "help", "customer care", "customer service",
    "helpdesk", "contact us", "dm for help", "dm us",
    "scholarship", "admission", "apply now", "winner",
]


def calculate(
    *,
    brand_name: str,
    brand_description: str | None,
    candidate_bio: str | None,
    candidate_name: str | None,
) -> SignalResult:
    """
    Calculate content similarity between candidate bio and official brand description.
    """
    reasons: list[str] = []
    metadata: dict = {}

    c_bio  = text_or_empty(candidate_bio) or text_or_empty(candidate_name)
    b_desc = text_or_empty(brand_description)
    b_name = text_or_empty(brand_name)

    if not c_bio:
        return SignalResult(
            signal_name=SIGNAL_NAME,
            raw_score=0.0,
            weight=WEIGHT,
            weighted_score=0.0,
            reason="No candidate bio/description available for comparison.",
            metadata={"method": "none"},
        )

    scores: list[float] = []

    # ── 1. Compare bio against official brand description ─────────────────────
    if b_desc:
        jaccard = jaccard_similarity(c_bio, b_desc)
        overlap = token_overlap_ratio(c_bio, b_desc)
        ngram   = ngram_similarity(c_bio, b_desc, n=3)
        desc_sim = round(max(jaccard, overlap * 0.8, ngram * 0.6), 4)
        scores.append(desc_sim)
        metadata["description_similarity"] = desc_sim

        if desc_sim >= 0.50:
            reasons.append(
                f"Candidate bio closely matches official brand description "
                f"(similarity: {desc_sim:.0%})."
            )
        elif desc_sim >= 0.25:
            reasons.append(
                f"Candidate bio has moderate overlap with official brand description "
                f"(similarity: {desc_sim:.0%})."
            )

    # ── 2. Brand name mentions in bio ─────────────────────────────────────────
    brand_mention_score = 0.0
    if b_name and b_name.lower() in c_bio.lower():
        brand_mention_score = 0.35
        scores.append(brand_mention_score)
        metadata["brand_name_in_bio"] = True
        reasons.append(f"Candidate bio explicitly mentions official brand name '{b_name}'.")

    # ── 3. Suspicious claims (official, support, verified, etc.) ─────────────
    has_claims, matched_claims = contains_suspicious_claims(c_bio)
    claim_score = 0.0
    if has_claims:
        claim_score = min(0.60, len(matched_claims) * 0.15)
        scores.append(claim_score)
        metadata["suspicious_claims"] = matched_claims
        reasons.append(
            f"Candidate bio contains terms commonly used in impersonation: "
            f"{', '.join(matched_claims[:4])}."
        )

    # ── 4. Keyword overlap with brand-related terms ───────────────────────────
    # Build brand keywords from name and description
    brand_keywords = [b_name] + (b_desc.split()[:20] if b_desc else [])
    kw_score = keyword_overlap_score(c_bio, brand_keywords[:15]) * 0.4
    if kw_score > 0.1:
        scores.append(kw_score)
        metadata["keyword_overlap"] = round(kw_score, 3)

    # ── Combine ───────────────────────────────────────────────────────────────
    if not scores:
        raw_score = 0.0
    else:
        # Use max of individual signals, capped at 1.0
        raw_score = min(1.0, max(scores) * 0.7 + sum(scores) / len(scores) * 0.3)
        raw_score = round(raw_score, 4)

    if not reasons:
        reasons.append(
            "No significant content similarity detected between candidate and brand."
        )

    return SignalResult(
        signal_name=SIGNAL_NAME,
        raw_score=raw_score,
        weight=WEIGHT,
        weighted_score=round(raw_score * WEIGHT, 4),
        reason="; ".join(reasons),
        metadata=metadata,
    )
