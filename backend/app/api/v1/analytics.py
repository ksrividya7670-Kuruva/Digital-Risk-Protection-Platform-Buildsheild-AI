"""
Analytics API router.

Endpoints:
  GET /api/v1/analytics/overview   — dashboard analytics overview
  GET /api/v1/analytics/trends     — threat discovery trend (last 30 days)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models import (
    Candidate,
    CandidateType,
    Case,
    CaseStatus,
    RiskAssessment,
    RiskLevel,
)
from app.schemas.analytics import AnalyticsOverview, ThreatTrend

router = APIRouter()


def _build_latest_ra_subquery():
    """Subquery: most-recent calculated_at per candidate."""
    return (
        select(
            RiskAssessment.candidate_id,
            func.max(RiskAssessment.calculated_at).label("max_calc"),
        )
        .group_by(RiskAssessment.candidate_id)
        .subquery()
    )


@router.get(
    "/overview",
    response_model=AnalyticsOverview,
    summary="Analytics overview",
    description=(
        "Returns all data needed for the dashboard analytics page: "
        "candidate counts, risk distribution, score statistics, "
        "open cases, and breakdowns by platform and type."
    ),
)
async def analytics_overview(db: AsyncSession = Depends(get_db)) -> AnalyticsOverview:
    # ── Candidate counts ─────────────────────────────────────
    total_result = await db.execute(select(func.count(Candidate.id)))
    total_candidates = total_result.scalar_one() or 0

    social_result = await db.execute(
        select(func.count(Candidate.id)).where(
            Candidate.candidate_type == CandidateType.SOCIAL_PROFILE
        )
    )
    social_candidates = social_result.scalar_one() or 0

    app_result = await db.execute(
        select(func.count(Candidate.id)).where(
            Candidate.candidate_type == CandidateType.MOBILE_APP
        )
    )
    app_candidates = app_result.scalar_one() or 0

    # ── Risk distribution via latest-RA subquery ─────────────
    latest_ra_subq = _build_latest_ra_subquery()

    risk_rows = await db.execute(
        select(RiskAssessment.risk_level, func.count(RiskAssessment.id))
        .join(
            latest_ra_subq,
            (RiskAssessment.candidate_id == latest_ra_subq.c.candidate_id)
            & (RiskAssessment.calculated_at == latest_ra_subq.c.max_calc),
        )
        .group_by(RiskAssessment.risk_level)
    )
    risk_counts: dict[str, int] = {row[0]: row[1] for row in risk_rows.fetchall()}

    # Score stats
    score_row = await db.execute(
        select(
            func.avg(RiskAssessment.total_score),
            func.max(RiskAssessment.total_score),
        )
        .join(
            latest_ra_subq,
            (RiskAssessment.candidate_id == latest_ra_subq.c.candidate_id)
            & (RiskAssessment.calculated_at == latest_ra_subq.c.max_calc),
        )
    )
    avg_raw, max_raw = score_row.one()
    avg_score = round(float(avg_raw or 0.0), 2)
    max_score = int(max_raw or 0)

    # ── Open cases ───────────────────────────────────────────
    open_statuses = [CaseStatus.OPEN, CaseStatus.INVESTIGATING, CaseStatus.ESCALATED]
    open_result = await db.execute(
        select(func.count(Case.id)).where(Case.status.in_(open_statuses))
    )
    open_cases = open_result.scalar_one() or 0

    # ── By platform ──────────────────────────────────────────
    platform_rows = await db.execute(
        select(Candidate.platform, func.count(Candidate.id)).group_by(Candidate.platform)
    )
    by_platform: dict[str, int] = {row[0]: row[1] for row in platform_rows.fetchall()}

    # ── By type ──────────────────────────────────────────────
    type_rows = await db.execute(
        select(Candidate.candidate_type, func.count(Candidate.id)).group_by(
            Candidate.candidate_type
        )
    )
    by_type: dict[str, int] = {row[0]: row[1] for row in type_rows.fetchall()}

    return AnalyticsOverview(
        total_candidates=total_candidates,
        social_candidates=social_candidates,
        app_candidates=app_candidates,
        critical=risk_counts.get(RiskLevel.CRITICAL, 0),
        high=risk_counts.get(RiskLevel.HIGH, 0),
        medium=risk_counts.get(RiskLevel.MEDIUM, 0),
        low=risk_counts.get(RiskLevel.LOW, 0),
        avg_score=avg_score,
        max_score=max_score,
        open_cases=open_cases,
        by_platform=by_platform,
        by_type=by_type,
    )


@router.get(
    "/trends",
    response_model=List[ThreatTrend],
    summary="Threat discovery trend (last 30 days)",
    description=(
        "Groups candidate discoveries by calendar day for the past 30 days. "
        "Returns an empty list if no data exists — historical data is never fabricated."
    ),
)
async def threat_trends(db: AsyncSession = Depends(get_db)) -> List[ThreatTrend]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    rows = await db.execute(
        select(
            func.date(Candidate.created_at).label("day"),
            func.count(Candidate.id).label("cnt"),
        )
        .where(Candidate.created_at >= cutoff)
        .group_by(func.date(Candidate.created_at))
        .order_by(func.date(Candidate.created_at))
    )

    return [ThreatTrend(date=str(row.day), count=row.cnt) for row in rows.fetchall()]
