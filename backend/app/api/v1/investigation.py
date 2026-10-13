"""
AI Investigation API router.

Endpoints:
  POST /api/v1/investigation/candidates/{candidate_id}/analyze
    → Full structured investigation summary for a candidate.

  POST /api/v1/investigation/candidates/{candidate_id}/ask
    → Answer a natural-language analyst question about a candidate.

Both endpoints:
  - Load candidate, brand, evidence, and risk assessment from the DB.
  - Pass a structured, read-only context to the AI service.
  - Never allow the AI to modify risk_score, risk_level, or confidence.
  - Fall back to template output if AI provider is unavailable.
  - Return 404 if the candidate does not exist.
  - Return 422 if no risk assessment has been run yet (analyze first).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.models import Candidate, RiskAssessment
from app.schemas.investigation import (
    AskRequest,
    AskResponse,
    InvestigationContext,
    InvestigationResult,
)
from app.services.ai_investigation import get_investigator

router = APIRouter()


async def _load_context(
    candidate_id: str,
    db: AsyncSession,
) -> InvestigationContext:
    """
    Load everything needed for investigation from the DB.
    Returns an InvestigationContext ready for the AI service.
    Raises HTTPException 404/422 on missing data.
    """
    # Load candidate + brand + evidence in one query
    result = await db.execute(
        select(Candidate)
        .where(Candidate.id == candidate_id)
        .options(
            selectinload(Candidate.brand),
            selectinload(Candidate.evidence_items),
        )
    )
    candidate = result.scalar_one_or_none()
    if candidate is None:
        raise HTTPException(status_code=404, detail=f"Candidate '{candidate_id}' not found.")

    # Latest risk assessment
    ra_result = await db.execute(
        select(RiskAssessment)
        .where(RiskAssessment.candidate_id == candidate_id)
        .order_by(
            RiskAssessment.calculated_at.desc(),
            RiskAssessment.created_at.desc(),
            RiskAssessment.id.desc(),
        )
        .limit(1)
    )
    ra: Optional[RiskAssessment] = ra_result.scalar_one_or_none()

    if ra is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"No risk assessment found for candidate '{candidate_id}'. "
                "Run POST /api/v1/detection/candidates/{id}/analyze first."
            ),
        )

    brand = candidate.brand

    # Rebuild signal list from RA columns
    from app.api.v1.candidates import SIGNAL_MAP
    signals = []
    for sig_name, col_attr, weight in SIGNAL_MAP:
        ws = getattr(ra, col_attr, None) or 0.0
        raw = (ws / weight) if weight > 0 else 0.0
        raw = max(0.0, min(1.0, raw))
        signals.append({
            "signal_name": sig_name,
            "raw_score": round(raw, 4),
            "weight": weight,
            "weighted_score": round(ws, 4),
        })

    # Parse top reasons from detection_summary
    top_reasons: list[str] = []
    if ra.detection_summary:
        # Split into sentences; take first 3 meaningful ones
        for part in ra.detection_summary.split("."):
            part = part.strip()
            if len(part) > 15:
                top_reasons.append(part)
            if len(top_reasons) >= 4:
                break

    # Serialize evidence to plain dicts
    evidence_dicts = [
        {
            "title": ev.title,
            "description": ev.description,
            "evidence_type": ev.evidence_type.value if hasattr(ev.evidence_type, "value") else str(ev.evidence_type),
            "severity": ev.severity.value if hasattr(ev.severity, "value") else str(ev.severity),
            "evidence_value": ev.evidence_value,
            "is_synthetic": ev.is_synthetic,
            "source": ev.source,
            "source_url": ev.source_url,
        }
        for ev in candidate.evidence_items
    ]

    return InvestigationContext(
        candidate_id=candidate.id,
        candidate_type=candidate.candidate_type.value if hasattr(candidate.candidate_type, "value") else str(candidate.candidate_type),
        platform=candidate.platform,
        name=candidate.name,
        username=candidate.username,
        data_source=(
            candidate.data_source.value
            if hasattr(candidate.data_source, "value")
            else str(candidate.data_source)
        ),
        profile_url=candidate.profile_url,
        bio_description=candidate.bio_description,
        website_url=candidate.website_url,
        candidate_metadata={
            key: value
            for key, value in {
                "display_name": candidate.display_name,
                "follower_count": candidate.follower_count,
                "following_count": candidate.following_count,
                "account_age_days": candidate.account_age_days,
                "is_verified": candidate.is_verified,
                "package_name": candidate.package_name,
                "developer_name": candidate.developer_name,
                "app_version": candidate.app_version,
                "install_count": candidate.install_count,
                "app_rating": candidate.app_rating,
            }.items()
            if value is not None
        },
        brand_name=brand.name if brand else "Unknown",
        brand_domain=brand.official_domain if brand else None,
        risk_score=ra.total_score,
        risk_level=ra.risk_level.value if hasattr(ra.risk_level, "value") else str(ra.risk_level),
        confidence=ra.confidence or 0.0,
        signals=signals,
        top_reasons=top_reasons,
        evidence=evidence_dicts,
    )


@router.post(
    "/candidates/{candidate_id}/analyze",
    response_model=InvestigationResult,
    summary="AI investigation analysis",
    description=(
        "Generates an explainability report from the latest stored deterministic "
        "risk assessment, its signals, candidate metadata, and stored evidence. "
        "A configured AI provider may write the summary; otherwise an evidence-based "
        "template is returned. Provider output is schema-validated and cannot alter "
        "the score, risk level, confidence, key findings, or evidence summary. "
        "No risk assessment is created or changed by this endpoint."
    ),
)
async def analyze_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
) -> InvestigationResult:
    ctx = await _load_context(candidate_id, db)
    investigator = get_investigator()
    result = await investigator.investigate(ctx)
    # Double-check invariant: AI cannot change score/level
    result.risk_score = ctx.risk_score
    result.risk_level = ctx.risk_level
    return result


@router.post(
    "/candidates/{candidate_id}/ask",
    response_model=AskResponse,
    summary="Ask the AI analyst a question",
    description=(
        "Answers an analyst question using only the candidate's latest stored "
        "assessment, signals, metadata, and evidence. Falls back to a deterministic "
        "answer if no AI provider is configured or it fails. The endpoint does not "
        "change any detection or scoring data."
    ),
)
async def ask_about_candidate(
    candidate_id: str,
    body: AskRequest,
    db: AsyncSession = Depends(get_db),
) -> AskResponse:
    ctx = await _load_context(candidate_id, db)
    investigator = get_investigator()
    return await investigator.ask(ctx, body.question)
