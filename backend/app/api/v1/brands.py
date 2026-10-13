"""
Brands API router.

Endpoints:
  GET /api/v1/brands/                  — list all active monitored brands
  GET /api/v1/brands/{brand_id}        — get one brand by ID
  GET /api/v1/brands/{brand_id}/summary — aggregated threat statistics for a brand
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models import (
    Brand,
    Candidate,
    CandidateType,
    Case,
    CaseStatus,
    RiskAssessment,
    RiskLevel,
)
from app.schemas.brand import BrandResponse, BrandSummaryResponse

router = APIRouter()


@router.get(
    "/",
    response_model=list[BrandResponse],
    summary="List monitored brands",
    description="Returns all active monitored brands ordered by name.",
)
async def list_brands(db: AsyncSession = Depends(get_db)) -> list[BrandResponse]:
    result = await db.execute(select(Brand).where(Brand.is_active == True).order_by(Brand.name))  # noqa: E712
    return list(result.scalars().all())


@router.get(
    "/{brand_id}",
    response_model=BrandResponse,
    summary="Get brand by ID",
    description="Returns a single monitored brand. Returns 404 if the brand does not exist.",
)
async def get_brand(brand_id: str, db: AsyncSession = Depends(get_db)) -> BrandResponse:
    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = result.scalar_one_or_none()
    if brand is None:
        raise HTTPException(status_code=404, detail=f"Brand '{brand_id}' not found")
    return brand


@router.get(
    "/{brand_id}/summary",
    response_model=BrandSummaryResponse,
    summary="Brand threat summary",
    description=(
        "Returns aggregated threat and candidate statistics for one brand. "
        "All counts are derived from live database queries."
    ),
)
async def brand_summary(
    brand_id: str,
    db: AsyncSession = Depends(get_db),
) -> BrandSummaryResponse:
    # Verify brand exists
    brand_result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = brand_result.scalar_one_or_none()
    if brand is None:
        raise HTTPException(status_code=404, detail=f"Brand '{brand_id}' not found")

    # ── Candidate counts ─────────────────────────────────────
    total_result = await db.execute(
        select(func.count(Candidate.id)).where(Candidate.brand_id == brand_id)
    )
    total_candidates = total_result.scalar_one() or 0

    social_result = await db.execute(
        select(func.count(Candidate.id)).where(
            Candidate.brand_id == brand_id,
            Candidate.candidate_type == CandidateType.SOCIAL_PROFILE,
        )
    )
    social_candidates = social_result.scalar_one() or 0

    app_result = await db.execute(
        select(func.count(Candidate.id)).where(
            Candidate.brand_id == brand_id,
            Candidate.candidate_type == CandidateType.MOBILE_APP,
        )
    )
    app_candidates = app_result.scalar_one() or 0

    # ── Risk level counts via latest-RA subquery ─────────────
    latest_ra_subq = (
        select(
            RiskAssessment.candidate_id,
            func.max(RiskAssessment.calculated_at).label("max_calc"),
        )
        .group_by(RiskAssessment.candidate_id)
        .subquery()
    )

    risk_rows = await db.execute(
        select(RiskAssessment.risk_level, func.count(RiskAssessment.id))
        .join(
            latest_ra_subq,
            (RiskAssessment.candidate_id == latest_ra_subq.c.candidate_id)
            & (RiskAssessment.calculated_at == latest_ra_subq.c.max_calc),
        )
        .join(Candidate, Candidate.id == RiskAssessment.candidate_id)
        .where(Candidate.brand_id == brand_id)
        .group_by(RiskAssessment.risk_level)
    )
    risk_counts: dict[str, int] = {row[0]: row[1] for row in risk_rows.fetchall()}

    # ── Open cases ───────────────────────────────────────────
    open_statuses = [CaseStatus.OPEN, CaseStatus.INVESTIGATING, CaseStatus.ESCALATED]
    open_result = await db.execute(
        select(func.count(Case.id)).where(
            Case.brand_id == brand_id,
            Case.status.in_(open_statuses),
        )
    )
    open_cases = open_result.scalar_one() or 0

    return BrandSummaryResponse(
        brand_id=brand.id,
        brand_name=brand.name,
        total_candidates=total_candidates,
        social_candidates=social_candidates,
        app_candidates=app_candidates,
        critical_threats=risk_counts.get(RiskLevel.CRITICAL, 0),
        high_threats=risk_counts.get(RiskLevel.HIGH, 0),
        medium_threats=risk_counts.get(RiskLevel.MEDIUM, 0),
        low_threats=risk_counts.get(RiskLevel.LOW, 0),
        open_cases=open_cases,
    )
