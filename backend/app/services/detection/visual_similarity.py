"""
Signal 2 — Visual / Logo Similarity (weight: 20%)

Deterministic visual similarity without heavy ML dependencies.

MVP strategy:
  - If a pre-computed perceptual hash is available on BOTH the brand logo
    and the candidate icon, compare them using Hamming distance.
  - If evidence records of type LOGO_SIMILARITY or ICON_SIMILARITY exist,
    use the similarity_score stored in those records.
  - If neither is available, return score=0 with a clear explanation.

Architecture note:
  The perceptual hash comparison slot is designed so that a real imagehash
  library can be plugged in later without changing the interface.
  For now, hash comparison uses pure Python Hamming distance on hex strings.
"""

from __future__ import annotations

from app.services.detection.contracts import SignalResult, SIGNAL_WEIGHTS

SIGNAL_NAME = "visual_similarity"
WEIGHT = SIGNAL_WEIGHTS[SIGNAL_NAME]

# Hamming distance threshold below which hashes are considered "similar"
HASH_SIMILARITY_THRESHOLD = 10  # out of 64 bits for pHash


def _hamming_distance(hash_a: str, hash_b: str) -> int:
    """
    Compute Hamming distance between two hex-encoded perceptual hashes.
    Pure Python — no imagehash dependency.
    """
    try:
        int_a = int(hash_a, 16)
        int_b = int(hash_b, 16)
        xor = int_a ^ int_b
        return bin(xor).count("1")
    except (ValueError, TypeError):
        return 64  # treat invalid hashes as maximally different


def _hash_similarity(hash_a: str, hash_b: str) -> float:
    """
    Convert Hamming distance to a 0.0–1.0 similarity score.
    Distance 0  → 1.0 (identical)
    Distance 64 → 0.0 (completely different)
    """
    distance = _hamming_distance(hash_a, hash_b)
    return max(0.0, 1.0 - (distance / 64.0))


def calculate(
    *,
    brand_logo_hash: str | None,
    candidate_icon_hash: str | None,
    evidence_visual_scores: list[float],  # from DB evidence records
) -> SignalResult:
    """
    Calculate visual similarity between candidate icon and brand logo.

    Priority:
      1. Pre-computed hash comparison (if both hashes present)
      2. Evidence-backed visual scores (from DB evidence)
      3. No data → score = 0, clearly explained
    """
    reasons: list[str] = []
    metadata: dict = {}

    # ── 1. Hash comparison ────────────────────────────────────────────────────
    if brand_logo_hash and candidate_icon_hash:
        sim = _hash_similarity(brand_logo_hash, candidate_icon_hash)
        metadata["hash_similarity"] = round(sim, 3)
        metadata["method"] = "perceptual_hash"

        if sim >= 0.90:
            reasons.append(
                f"Candidate icon is nearly identical to official brand logo "
                f"(hash similarity: {sim:.0%})."
            )
        elif sim >= 0.70:
            reasons.append(
                f"Candidate icon is visually similar to official brand logo "
                f"(hash similarity: {sim:.0%})."
            )
        elif sim >= 0.40:
            reasons.append(
                f"Candidate icon shows partial visual resemblance to brand logo "
                f"(hash similarity: {sim:.0%})."
            )
        else:
            reasons.append(
                f"Candidate icon does not closely resemble official brand logo "
                f"(hash similarity: {sim:.0%})."
            )
        return SignalResult(
            signal_name=SIGNAL_NAME,
            raw_score=sim,
            weight=WEIGHT,
            weighted_score=round(sim * WEIGHT, 4),
            reason="; ".join(reasons),
            metadata=metadata,
        )

    # ── 2. Evidence-backed scores ─────────────────────────────────────────────
    if evidence_visual_scores:
        # Take the maximum from available visual evidence records
        max_score = max(evidence_visual_scores)
        avg_score = sum(evidence_visual_scores) / len(evidence_visual_scores)
        # Use max to avoid under-reporting, tempered by average
        raw_score = round(0.7 * max_score + 0.3 * avg_score, 4)
        metadata["method"] = "evidence_records"
        metadata["evidence_count"] = len(evidence_visual_scores)
        metadata["max_evidence_score"] = round(max_score, 3)

        if raw_score >= 0.75:
            reasons.append(
                f"Evidence records indicate high visual similarity to brand logo "
                f"(score: {raw_score:.0%})."
            )
        elif raw_score >= 0.40:
            reasons.append(
                f"Evidence records indicate moderate visual similarity to brand logo "
                f"(score: {raw_score:.0%})."
            )
        else:
            reasons.append(
                f"Evidence records indicate low visual similarity to brand logo "
                f"(score: {raw_score:.0%})."
            )
        return SignalResult(
            signal_name=SIGNAL_NAME,
            raw_score=raw_score,
            weight=WEIGHT,
            weighted_score=round(raw_score * WEIGHT, 4),
            reason="; ".join(reasons),
            metadata=metadata,
        )

    # ── 3. No visual data available ───────────────────────────────────────────
    return SignalResult(
        signal_name=SIGNAL_NAME,
        raw_score=0.0,
        weight=WEIGHT,
        weighted_score=0.0,
        reason="No visual evidence available — logo/icon comparison could not be performed.",
        metadata={"method": "none"},
    )
