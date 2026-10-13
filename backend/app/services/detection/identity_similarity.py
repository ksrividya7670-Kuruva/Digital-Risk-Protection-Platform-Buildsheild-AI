"""
Signal 1 — Identity Similarity (weight: 25%)

Compares the candidate's username and display name against the official
brand identity using deterministic string similarity techniques.

Covers:
  - Username/handle similarity to official handles
  - Display name similarity to brand name
  - Impersonation affix patterns (brand + "official", "support", etc.)
  - Leet-speak / character substitution patterns
  - Brand name embedded in a longer username

Returns raw_score 0.0–1.0.
"""

from __future__ import annotations

from app.services.detection.contracts import SignalResult, SIGNAL_WEIGHTS
from app.services.detection.text_utils import (
    normalize_username,
    normalize_text,
    string_similarity,
    jaccard_similarity,
    token_overlap_ratio,
    has_impersonation_affix,
    text_or_empty,
)

SIGNAL_NAME = "identity_similarity"
WEIGHT = SIGNAL_WEIGHTS[SIGNAL_NAME]

# Common leet-speak substitutions
_LEET_MAP = str.maketrans("013456789@", "oieasgtbga")


def _deleet(text: str) -> str:
    """Convert common leet-speak characters to their letter equivalents."""
    return text.lower().translate(_LEET_MAP)


def calculate(
    *,
    brand_name: str,
    brand_official_handles: list[str],   # all known official handles
    candidate_username: str | None,
    candidate_display_name: str | None,
    candidate_name: str | None,
) -> SignalResult:
    """
    Calculate identity similarity between candidate and brand.

    Strategy:
      1. Compare candidate username against each official handle → take max
      2. Compare candidate display name against brand name
      3. Bonus for impersonation affix pattern
      4. Leet-speak normalization
      5. Brand name embedded in username
      Combine into a single 0.0–1.0 score.
    """

    reasons: list[str] = []
    details: dict = {}

    c_username = text_or_empty(candidate_username)
    c_display  = text_or_empty(candidate_display_name) or text_or_empty(candidate_name)
    b_name     = text_or_empty(brand_name)

    # ── 1. Username similarity against all official handles ──────────────────
    username_scores: list[float] = []

    # Also compare directly against the brand name itself
    all_brand_refs = [b_name] + [h for h in brand_official_handles if h]

    for ref in all_brand_refs:
        if not ref:
            continue
        # Normal similarity
        sim = string_similarity(c_username, ref)
        # Leet-speak normalized similarity
        sim_leet = string_similarity(_deleet(c_username), _deleet(ref))
        username_scores.append(max(sim, sim_leet))

    username_sim = max(username_scores) if username_scores else 0.0
    details["username_similarity"] = round(username_sim, 3)

    if username_sim >= 0.85:
        reasons.append(
            f"Username '{c_username}' is highly similar to official brand identity "
            f"(similarity: {username_sim:.0%})."
        )
    elif username_sim >= 0.60:
        reasons.append(
            f"Username '{c_username}' shows moderate similarity to official brand identity "
            f"(similarity: {username_sim:.0%})."
        )

    # ── 2. Display name similarity ────────────────────────────────────────────
    display_sim = 0.0
    if c_display and b_name:
        display_sim = max(
            string_similarity(c_display, b_name),
            token_overlap_ratio(c_display, b_name),
            jaccard_similarity(c_display, b_name),
        )
        details["display_name_similarity"] = round(display_sim, 3)
        if display_sim >= 0.70:
            reasons.append(
                f"Display name '{c_display}' closely resembles official brand name "
                f"(similarity: {display_sim:.0%})."
            )

    # ── 3. Impersonation affix pattern ────────────────────────────────────────
    affix_bonus = 0.0
    has_affix, matched_affix = has_impersonation_affix(c_username, b_name)
    if has_affix:
        affix_bonus = 0.25  # additive bonus to raw score
        details["impersonation_affix"] = matched_affix
        reasons.append(
            f"Username uses a known impersonation pattern: "
            f"brand name + '{matched_affix}'."
        )

    # ── 4. Brand name embedded check ─────────────────────────────────────────
    embedded_bonus = 0.0
    b_norm = normalize_username(b_name)
    c_norm = normalize_username(c_username)
    if b_norm and len(b_norm) >= 4 and b_norm in c_norm and b_norm != c_norm:
        embedded_bonus = 0.15
        details["brand_name_embedded"] = True
        if not has_affix:  # avoid duplicate reason
            reasons.append(
                f"Official brand name '{b_name}' is embedded within candidate username."
            )

    # ── Combine ───────────────────────────────────────────────────────────────
    # Take the max of username and display similarities, then add bonuses
    base_score = max(username_sim, display_sim * 0.8)  # display weighted slightly less
    raw_score  = min(1.0, base_score + affix_bonus + embedded_bonus)

    if not reasons:
        reasons.append(
            "No significant identity similarity detected between candidate and brand."
        )

    return SignalResult(
        signal_name=SIGNAL_NAME,
        raw_score=raw_score,
        weight=WEIGHT,
        weighted_score=round(raw_score * WEIGHT, 4),
        reason="; ".join(reasons),
        metadata=details,
    )
