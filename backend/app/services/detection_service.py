"""
DetectionService — Database integration for the risk engine.

Responsibilities:
  1. Load a Candidate + its Brand + its Evidence from the DB
  2. Assemble a CandidateBundle
  3. Call risk_engine.run()
  4. Persist (or update) the RiskAssessment record
  5. Return the DetectionResult

This service is the bridge between the DB layer and the pure detection engine.
It is the ONLY place that touches both SQLAlchemy and the detection engine.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Brand,
    Candidate,
    Evidence,
    RiskAssessment,
    RiskLevel,
)
from app.services.detection.risk_engine import run as engine_run, CandidateBundle
from app.services.detection.evidence_score import EvidenceItem
from app.services.detection.contracts import DetectionResult


async def analyze_candidate(
    db: AsyncSession,
    candidate_id: str,
) -> DetectionResult:
    """
    Run the full detection engine for one candidate and persist the result.

    If a RiskAssessment already exists for this candidate, it is replaced
    with the new calculation (recalculation is always deterministic).

    Returns the DetectionResult (does NOT include AI explanation — that
    comes from a separate AIService call in a later step).
    """

    # ── Load candidate with brand and evidence ────────────────────────────────
    result = await db.execute(
        select(Candidate)
        .where(Candidate.id == candidate_id)
        .options(
            selectinload(Candidate.brand),
            selectinload(Candidate.evidence_items),
        )
    )
    candidate: Candidate | None = result.scalar_one_or_none()

    if candidate is None:
        raise ValueError(f"Candidate '{candidate_id}' not found.")

    brand: Brand = candidate.brand
    evidence_list: list[Evidence] = candidate.evidence_items

    # ── Build CandidateBundle ─────────────────────────────────────────────────
    # Collect all official handles from the brand record
    official_handles = [
        h for h in [
            brand.twitter_handle,
            brand.instagram_handle,
            brand.facebook_handle,
            brand.linkedin_handle,
            brand.youtube_handle,
            brand.tiktok_handle,
            brand.name,
        ]
        if h
    ]

    evidence_items = [
        EvidenceItem(
            evidence_type=ev.evidence_type.value if hasattr(ev.evidence_type, "value") else str(ev.evidence_type),
            severity=ev.severity.value if hasattr(ev.severity, "value") else str(ev.severity),
            similarity_score=ev.similarity_score,
            title=ev.title,
        )
        for ev in evidence_list
    ]

    bundle = CandidateBundle(
        candidate_id=candidate.id,
        brand_id=brand.id,
        candidate_type=(
            candidate.candidate_type.value
            if hasattr(candidate.candidate_type, "value")
            else str(candidate.candidate_type)
        ),
        brand_name=brand.name,
        brand_description=brand.description,
        brand_official_handles=official_handles,
        brand_official_domain=brand.official_domain,
        brand_official_email_domain=brand.official_email_domain,
        brand_logo_hash=brand.logo_perceptual_hash,
        brand_official_developer_name=brand.official_developer_name,
        candidate_username=candidate.username,
        candidate_display_name=candidate.display_name,
        candidate_name=candidate.name,
        candidate_bio=candidate.bio_description,
        candidate_website=candidate.website_url,
        candidate_email=candidate.contact_email,
        candidate_icon_hash=candidate.icon_perceptual_hash,
        follower_count=candidate.follower_count,
        following_count=candidate.following_count,
        account_age_days=candidate.account_age_days,
        is_verified=candidate.is_verified,
        package_name=candidate.package_name,
        developer_name=candidate.developer_name,
        developer_email=candidate.developer_email,
        app_version=candidate.app_version,
        install_count=candidate.install_count,
        evidence_items=evidence_items,
    )

    # ── Run detection engine ──────────────────────────────────────────────────
    detection: DetectionResult = engine_run(bundle)

    # ── Persist RiskAssessment ────────────────────────────────────────────────
    # Check for existing assessment (replace on recalculation)
    existing = await db.execute(
        select(RiskAssessment)
        .where(RiskAssessment.candidate_id == candidate_id)
        .order_by(RiskAssessment.calculated_at.desc())
        .limit(1)
    )
    existing_ra: RiskAssessment | None = existing.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if existing_ra:
        # Update existing — keeps history clean for the MVP
        existing_ra.total_score = detection.total_score
        existing_ra.risk_level = RiskLevel(detection.risk_level)
        existing_ra.confidence = detection.confidence
        existing_ra.identity_similarity_score = detection.identity_similarity_score
        existing_ra.visual_similarity_score = detection.visual_similarity_score
        existing_ra.content_similarity_score = detection.content_similarity_score
        existing_ra.link_contact_score = detection.link_contact_score
        existing_ra.anomaly_score = detection.anomaly_score
        existing_ra.evidence_score = detection.evidence_score_val
        existing_ra.activity_score = detection.activity_score
        existing_ra.detection_summary = detection.explanation
        existing_ra.calculated_at = now
        existing_ra.updated_at = now
        # Reset AI fields — AI must regenerate after a rescan
        existing_ra.ai_explanation = None
        existing_ra.ai_investigation_steps = None
        existing_ra.ai_generated_at = None
    else:
        import uuid
        new_ra = RiskAssessment(
            id=str(uuid.uuid4()),
            candidate_id=candidate.id,
            total_score=detection.total_score,
            risk_level=RiskLevel(detection.risk_level),
            confidence=detection.confidence,
            identity_similarity_score=detection.identity_similarity_score,
            visual_similarity_score=detection.visual_similarity_score,
            content_similarity_score=detection.content_similarity_score,
            link_contact_score=detection.link_contact_score,
            anomaly_score=detection.anomaly_score,
            evidence_score=detection.evidence_score_val,
            activity_score=detection.activity_score,
            detection_summary=detection.explanation,
            calculated_at=now,
        )
        db.add(new_ra)

    await db.commit()
    return detection


async def get_latest_assessment(
    db: AsyncSession,
    candidate_id: str,
) -> RiskAssessment | None:
    """Fetch the most recent RiskAssessment for a candidate."""
    result = await db.execute(
        select(RiskAssessment)
        .where(RiskAssessment.candidate_id == candidate_id)
        .order_by(RiskAssessment.calculated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
