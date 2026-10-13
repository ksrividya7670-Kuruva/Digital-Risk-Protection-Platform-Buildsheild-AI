"""
Threats API router.

A "threat" is a Candidate that has at least one RiskAssessment.

IMPORTANT: /summary is registered BEFORE /{threat_id} to prevent FastAPI
from routing the literal string "summary" as a path parameter.

Endpoints:
  GET /api/v1/threats/summary  — KPI counts for the threat queue header
  GET /api/v1/threats/         — paginated, filtered threat queue
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
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
from app.schemas.analytics import ThreatSummaryResponse

router = APIRouter()

VALID_RISK_LEVELS = {e.value for e in RiskLevel}
VALID_SORT_OPTIONS = {"risk_score_desc", "risk_score_asc", "newest", "oldest"}


def _build_latest_ra_subquery():
    """Subquery returning the most-recent calculated_at per candidate."""
    return (
        select(
            RiskAssessment.candidate_id,
            func.max(RiskAssessment.calculated_at).label("max_calc"),
        )
        .group_by(RiskAssessment.candidate_id)
        .subquery()
    )


@router.get(
    "/summary",
    response_model=ThreatSummaryResponse,
    summary="Threat queue summary",
    description=(
        "Returns aggregated KPI statistics for all threats "
        "(candidates that have a risk assessment). "
        "Powers dashboard KPI cards."
    ),
)
async def threat_summary(db: AsyncSession = Depends(get_db)) -> ThreatSummaryResponse:
    latest_ra_subq = _build_latest_ra_subquery()

    # Base join: RiskAssessment INNER JOIN latest_ra_subq INNER JOIN Candidate
    # This gives us one row per candidate with their current RA.
    base_join = (
        select(RiskAssessment, Candidate)
        .join(
            latest_ra_subq,
            (RiskAssessment.candidate_id == latest_ra_subq.c.candidate_id)
            & (RiskAssessment.calculated_at == latest_ra_subq.c.max_calc),
        )
        .join(Candidate, Candidate.id == RiskAssessment.candidate_id)
    )

    # Total threats
    total_result = await db.execute(select(func.count()).select_from(base_join.subquery()))
    total = total_result.scalar_one() or 0

    # Per-risk-level counts
    risk_level_rows = await db.execute(
        select(RiskAssessment.risk_level, func.count(RiskAssessment.id))
        .join(
            latest_ra_subq,
            (RiskAssessment.candidate_id == latest_ra_subq.c.candidate_id)
            & (RiskAssessment.calculated_at == latest_ra_subq.c.max_calc),
        )
        .group_by(RiskAssessment.risk_level)
    )
    risk_counts: dict[str, int] = {row[0]: row[1] for row in risk_level_rows.fetchall()}

    # Social vs app threat counts
    type_rows = await db.execute(
        select(Candidate.candidate_type, func.count(Candidate.id))
        .join(
            latest_ra_subq,
            Candidate.id == latest_ra_subq.c.candidate_id,
        )
        .group_by(Candidate.candidate_type)
    )
    type_counts: dict[str, int] = {row[0]: row[1] for row in type_rows.fetchall()}

    # Aggregate score stats
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
    avg_score_raw, max_score_raw = score_row.one()
    avg_score = round(float(avg_score_raw or 0.0), 2)
    max_score = int(max_score_raw or 0)

    # Open cases
    open_statuses = [CaseStatus.OPEN, CaseStatus.INVESTIGATING, CaseStatus.ESCALATED]
    open_result = await db.execute(
        select(func.count(Case.id)).where(Case.status.in_(open_statuses))
    )
    open_cases = open_result.scalar_one() or 0

    return ThreatSummaryResponse(
        total=total,
        critical=risk_counts.get(RiskLevel.CRITICAL, 0),
        high=risk_counts.get(RiskLevel.HIGH, 0),
        medium=risk_counts.get(RiskLevel.MEDIUM, 0),
        low=risk_counts.get(RiskLevel.LOW, 0),
        social_threats=type_counts.get(CandidateType.SOCIAL_PROFILE, 0),
        app_threats=type_counts.get(CandidateType.MOBILE_APP, 0),
        avg_score=avg_score,
        max_score=max_score,
        open_cases=open_cases,
    )


@router.get(
    "/",
    summary="List threats",
    description=(
        "Returns a paginated threat queue — candidates that have a risk assessment. "
        "Default sort is highest risk first."
    ),
)
async def list_threats(
    risk_level: Optional[str] = Query(None, description="LOW | MEDIUM | HIGH | CRITICAL"),
    candidate_type: Optional[str] = Query(None, description="SOCIAL_PROFILE | MOBILE_APP"),
    platform: Optional[str] = Query(None, description="e.g. Twitter, Instagram, Google Play"),
    status: Optional[str] = Query(None, description="Candidate status filter"),
    min_score: Optional[int] = Query(None, ge=0, le=100, description="Minimum risk score"),
    sort: str = Query("risk_score_desc", description="risk_score_desc | risk_score_asc | newest | oldest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    if risk_level is not None and risk_level not in VALID_RISK_LEVELS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid risk_level '{risk_level}'. Must be one of: {sorted(VALID_RISK_LEVELS)}",
        )
    if sort not in VALID_SORT_OPTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid sort '{sort}'. Must be one of: {sorted(VALID_SORT_OPTIONS)}",
        )

    latest_ra_subq = _build_latest_ra_subquery()

    # INNER JOIN — only candidates that HAVE an RA
    base_q = (
        select(Candidate, RiskAssessment)
        .join(
            latest_ra_subq,
            Candidate.id == latest_ra_subq.c.candidate_id,
        )
        .join(
            RiskAssessment,
            (RiskAssessment.candidate_id == latest_ra_subq.c.candidate_id)
            & (RiskAssessment.calculated_at == latest_ra_subq.c.max_calc),
        )
    )

    # Filters
    if risk_level is not None:
        base_q = base_q.where(RiskAssessment.risk_level == risk_level)
    if candidate_type is not None:
        base_q = base_q.where(Candidate.candidate_type == candidate_type)
    if platform is not None:
        base_q = base_q.where(Candidate.platform == platform)
    if status is not None:
        base_q = base_q.where(Candidate.status == status)
    if min_score is not None:
        base_q = base_q.where(RiskAssessment.total_score >= min_score)

    # Total count
    count_q = select(func.count()).select_from(base_q.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar_one() or 0

    # Sort
    if sort == "risk_score_desc":
        base_q = base_q.order_by(RiskAssessment.total_score.desc())
    elif sort == "risk_score_asc":
        base_q = base_q.order_by(RiskAssessment.total_score.asc())
    elif sort == "newest":
        base_q = base_q.order_by(Candidate.created_at.desc())
    else:  # oldest
        base_q = base_q.order_by(Candidate.created_at.asc())

    # Paginate
    base_q = base_q.offset((page - 1) * page_size).limit(page_size)

    rows = await db.execute(base_q)

    items = []
    for candidate, ra in rows.all():
        # Extract top reasons: first 2 sentences from detection_summary
        top_reasons: List[str] = []
        if ra.detection_summary:
            sentences = [s.strip() for s in ra.detection_summary.split(".") if s.strip()]
            top_reasons = sentences[:2]

        items.append(
            {
                "id": candidate.id,
                "name": candidate.name,
                "platform": candidate.platform,
                "candidate_type": candidate.candidate_type,
                "risk_score": ra.total_score,
                "risk_level": ra.risk_level,
                "confidence": ra.confidence,
                "top_reasons": top_reasons,
                "status": candidate.status,
                "discovered_at": candidate.created_at.isoformat() if candidate.created_at else None,
            }
        )

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
    }
