"""
Signal 5 — Account / App Anomaly (weight: 10%)

Deterministic anomaly detection using candidate metadata fields.
No invented data — if a field is None, it simply doesn't contribute.

Social profile signals:
  - Very young account age (< 30 days)
  - Suspicious follower/following ratio (many following, very few followers)
  - Unverified but claims to be official
  - Very low follower count despite claiming to be a brand

Mobile app signals:
  - Developer mismatch with official developer name
  - Very low install count for a "brand" app
  - Very new app (age < 30 days)

General:
  - Missing core profile fields (empty bio, no website) despite claiming brand status
"""

from __future__ import annotations
from typing import Optional

from app.services.detection.contracts import SignalResult, SIGNAL_WEIGHTS
from app.services.detection.text_utils import (
    contains_suspicious_claims,
    string_similarity,
    text_or_empty,
)

SIGNAL_NAME = "account_anomaly"
WEIGHT = SIGNAL_WEIGHTS[SIGNAL_NAME]


def calculate(
    *,
    candidate_type: str,                      # "SOCIAL_PROFILE" or "MOBILE_APP"
    # Social profile fields
    account_age_days: Optional[int],
    follower_count: Optional[int],
    following_count: Optional[int],
    is_verified: Optional[bool],
    bio_description: Optional[str],
    display_name: Optional[str],
    # App fields
    developer_name: Optional[str],
    official_developer_name: Optional[str],
    install_count: Optional[int],
    app_version: Optional[str],
    # Shared
    claims_to_be_official: bool,              # derived from bio/name containing "official"
) -> SignalResult:
    """
    Calculate anomaly score from candidate metadata.
    Only uses data that is actually present — no inference from absences
    except where explicitly noted.
    """
    reasons: list[str] = []
    metadata: dict = {}
    anomaly_components: list[float] = []

    if candidate_type == "SOCIAL_PROFILE":
        anomaly_components, reasons, metadata = _social_anomalies(
            account_age_days=account_age_days,
            follower_count=follower_count,
            following_count=following_count,
            is_verified=is_verified,
            bio_description=bio_description,
            claims_to_be_official=claims_to_be_official,
        )
    elif candidate_type == "MOBILE_APP":
        anomaly_components, reasons, metadata = _app_anomalies(
            developer_name=developer_name,
            official_developer_name=official_developer_name,
            install_count=install_count,
            account_age_days=account_age_days,
            app_version=app_version,
            claims_to_be_official=claims_to_be_official,
        )

    if not anomaly_components:
        return SignalResult(
            signal_name=SIGNAL_NAME,
            raw_score=0.0,
            weight=WEIGHT,
            weighted_score=0.0,
            reason="Insufficient account/app metadata available for anomaly detection.",
            metadata=metadata,
        )

    # Weighted average of individual anomaly signals (not max — anomalies compound)
    raw_score = round(
        min(1.0, sum(anomaly_components) / max(len(anomaly_components), 1)),
        4
    )
    # Boost if multiple anomalies fire
    if len(anomaly_components) >= 3:
        raw_score = min(1.0, raw_score * 1.25)
        metadata["multi_anomaly_boost"] = True

    return SignalResult(
        signal_name=SIGNAL_NAME,
        raw_score=raw_score,
        weight=WEIGHT,
        weighted_score=round(raw_score * WEIGHT, 4),
        reason="; ".join(reasons) if reasons else "No anomalies detected.",
        metadata=metadata,
    )


def _social_anomalies(
    *,
    account_age_days: Optional[int],
    follower_count: Optional[int],
    following_count: Optional[int],
    is_verified: Optional[bool],
    bio_description: Optional[str],
    claims_to_be_official: bool,
) -> tuple[list[float], list[str], dict]:
    components: list[float] = []
    reasons: list[str] = []
    metadata: dict = {}

    # ── Account age ───────────────────────────────────────────────────────────
    if account_age_days is not None:
        metadata["account_age_days"] = account_age_days
        if account_age_days < 7:
            components.append(0.90)
            reasons.append(
                f"Account is extremely new ({account_age_days} days old)."
            )
        elif account_age_days < 30:
            components.append(0.70)
            reasons.append(
                f"Account was created recently ({account_age_days} days ago)."
            )
        elif account_age_days < 90:
            components.append(0.30)

    # ── Follower/following ratio ───────────────────────────────────────────────
    if follower_count is not None and following_count is not None:
        metadata["follower_count"] = follower_count
        metadata["following_count"] = following_count
        if following_count > 0:
            ratio = follower_count / following_count
            metadata["follower_ratio"] = round(ratio, 2)
            if follower_count < 100 and claims_to_be_official:
                # Claims to be brand but has almost no followers
                components.append(0.75)
                reasons.append(
                    f"Account claims to be official but has only {follower_count} followers."
                )
            if following_count > 10 * max(follower_count, 1):
                # Following far more accounts than followers — spam-like
                components.append(0.45)
                reasons.append(
                    f"Suspicious follower ratio: following {following_count} accounts "
                    f"but only {follower_count} followers."
                )

    # ── Verification vs. official claim ────────────────────────────────────────
    if claims_to_be_official and is_verified is False:
        components.append(0.55)
        reasons.append(
            "Account claims to be an official brand presence but lacks platform verification."
        )
        metadata["claims_official_unverified"] = True

    # ── Empty bio claiming officialness ────────────────────────────────────────
    if claims_to_be_official and not text_or_empty(bio_description):
        components.append(0.40)
        reasons.append("Account claims to be official but has an empty bio/description.")

    return components, reasons, metadata


def _app_anomalies(
    *,
    developer_name: Optional[str],
    official_developer_name: Optional[str],
    install_count: Optional[int],
    account_age_days: Optional[int],
    app_version: Optional[str],
    claims_to_be_official: bool,
) -> tuple[list[float], list[str], dict]:
    components: list[float] = []
    reasons: list[str] = []
    metadata: dict = {}

    # ── Developer mismatch ────────────────────────────────────────────────────
    if developer_name and official_developer_name:
        dev_sim = string_similarity(developer_name, official_developer_name)
        metadata["developer_similarity"] = round(dev_sim, 3)
        metadata["candidate_developer"] = developer_name
        metadata["official_developer"] = official_developer_name

        if dev_sim < 0.30:
            components.append(0.80)
            reasons.append(
                f"App developer '{developer_name}' is very different from "
                f"official developer '{official_developer_name}'."
            )
        elif dev_sim < 0.60:
            components.append(0.50)
            reasons.append(
                f"App developer '{developer_name}' does not closely match "
                f"official developer '{official_developer_name}'."
            )

    # ── Install count anomaly ─────────────────────────────────────────────────
    if install_count is not None:
        metadata["install_count"] = install_count
        if install_count < 100 and claims_to_be_official:
            components.append(0.60)
            reasons.append(
                f"App claims to be official but has very few installs ({install_count})."
            )
        elif install_count < 1000:
            components.append(0.25)

    # ── App age ───────────────────────────────────────────────────────────────
    if account_age_days is not None:
        metadata["app_age_days"] = account_age_days
        if account_age_days < 30:
            components.append(0.55)
            reasons.append(
                f"App was published very recently ({account_age_days} days ago)."
            )

    # ── Version anomaly (1.0.0 for a claimed official app is suspicious) ─────
    if app_version and app_version.strip() in ("1.0", "1.0.0", "0.1", "0.1.0"):
        if claims_to_be_official:
            components.append(0.30)
            reasons.append(
                f"App version is {app_version!r} — unusually early for a claimed official app."
            )

    return components, reasons, metadata
