"""
Candidates API router.

Endpoints:
  GET /api/v1/candidates/           — paginated, filtered list of candidates
  GET /api/v1/candidates/{id}       — full investigation-ready candidate detail
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.models import (
    Brand,
    Candidate,
    CandidateStatus,
    CandidateType,
    RiskAssessment,
)
from app.schemas.candidate import CandidateDetail, CandidateListItem, EvidenceItem, SignalItem

router = APIRouter()

# Signal name → (RA column attr name, max weight)
SIGNAL_MAP = [
    ("identity_similarity", "identity_similarity_score", 25),
    ("visual_similarity",   "visual_similarity_score",   20),
    ("content_similarity",  "content_similarity_score",  15),
    ("link_risk",           "link_contact_score",        15),
    ("account_anomaly",     "anomaly_score",             10),
    ("evidence_score",      "evidence_score",            10),
    ("activity_anomaly",    "activity_score",             5),
]

VALID_CANDIDATE_TYPES = {e.value for e in CandidateType}
VALID_CANDIDATE_STATUSES = {e.value for e in CandidateStatus}
VALID_SORT_OPTIONS = {"risk_score_desc", "risk_score_asc", "newest", "oldest"}


def _build_latest_ra_subquery():
    """Return a subquery that selects the most-recent calculated_at per candidate."""
    return (
        select(
            RiskAssessment.candidate_id,
            func.max(RiskAssessment.calculated_at).label("max_calc"),
        )
        .group_by(RiskAssessment.candidate_id)
        .subquery()
    )


@router.get(
    "/",
    summary="List candidates",
    description=(
        "Returns a paginated list of candidates. "
        "Supports filtering by brand, type, platform, status, risk level, and score range."
    ),
)
async def list_candidates(
    brand_id: Optional[str] = Query(None, description="Filter by brand ID"),
    candidate_type: Optional[str] = Query(None, description="SOCIAL_PROFILE or MOBILE_APP"),
    platform: Optional[str] = Query(None, description="e.g. Twitter, Instagram, Google Play"),
    status: Optional[str] = Query(None, description="NEW, REVIEWING, CONFIRMED_THREAT, BENIGN, FALSE_POSITIVE"),
    risk_level: Optional[str] = Query(None, description="LOW, MEDIUM, HIGH, CRITICAL"),
    min_score: Optional[int] = Query(None, ge=0, le=100, description="Minimum risk score (0-100)"),
    max_score: Optional[int] = Query(None, ge=0, le=100, description="Maximum risk score (0-100)"),
    sort: str = Query("risk_score_desc", description="risk_score_desc | risk_score_asc | newest | oldest"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    # Validate enum-like filters
    if candidate_type is not None and candidate_type not in VALID_CANDIDATE_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid candidate_type '{candidate_type}'. Must be one of: {sorted(VALID_CANDIDATE_TYPES)}",
        )
    if status is not None and status not in VALID_CANDIDATE_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{status}'. Must be one of: {sorted(VALID_CANDIDATE_STATUSES)}",
        )
    if sort not in VALID_SORT_OPTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid sort '{sort}'. Must be one of: {sorted(VALID_SORT_OPTIONS)}",
        )

    latest_ra_subq = _build_latest_ra_subquery()

    # Build base query: Candidate LEFT JOINed to latest RiskAssessment
    base_q = (
        select(Candidate, RiskAssessment)
        .outerjoin(
            latest_ra_subq,
            Candidate.id == latest_ra_subq.c.candidate_id,
        )
        .outerjoin(
            RiskAssessment,
            (RiskAssessment.candidate_id == latest_ra_subq.c.candidate_id)
            & (RiskAssessment.calculated_at == latest_ra_subq.c.max_calc),
        )
    )

    # Apply filters
    if brand_id is not None:
        base_q = base_q.where(Candidate.brand_id == brand_id)
    if candidate_type is not None:
        base_q = base_q.where(Candidate.candidate_type == candidate_type)
    if platform is not None:
        base_q = base_q.where(Candidate.platform == platform)
    if status is not None:
        base_q = base_q.where(Candidate.status == status)
    if risk_level is not None:
        base_q = base_q.where(RiskAssessment.risk_level == risk_level)
    if min_score is not None:
        base_q = base_q.where(RiskAssessment.total_score >= min_score)
    if max_score is not None:
        base_q = base_q.where(RiskAssessment.total_score <= max_score)

    # Count total (re-use same filters)
    count_q = select(func.count()).select_from(base_q.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar_one() or 0

    # Apply sort
    if sort == "risk_score_desc":
        base_q = base_q.order_by(RiskAssessment.total_score.desc().nulls_last())
    elif sort == "risk_score_asc":
        base_q = base_q.order_by(RiskAssessment.total_score.asc().nulls_last())
    elif sort == "newest":
        base_q = base_q.order_by(Candidate.created_at.desc())
    else:  # oldest
        base_q = base_q.order_by(Candidate.created_at.asc())

    # Paginate
    base_q = base_q.offset((page - 1) * page_size).limit(page_size)

    rows = await db.execute(base_q)
    items: List[CandidateListItem] = []
    for candidate, ra in rows.all():
        items.append(
            CandidateListItem(
                id=candidate.id,
                brand_id=candidate.brand_id,
                candidate_type=candidate.candidate_type,
                platform=candidate.platform,
                name=candidate.name,
                username=candidate.username,
                risk_score=ra.total_score if ra else None,
                risk_level=ra.risk_level if ra else None,
                confidence=ra.confidence if ra else None,
                status=candidate.status,
                data_source=candidate.data_source,
                discovered_at=candidate.created_at,
            )
        )

    return {
        "items": [item.model_dump() for item in items],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get(
    "/{candidate_id}",
    response_model=CandidateDetail,
    summary="Get candidate detail",
    description=(
        "Returns the full investigation-ready candidate record. "
        "Includes profile metadata, the current risk assessment, "
        "signal breakdown, and all evidence."
    ),
)
async def get_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
) -> CandidateDetail:
    # Load candidate with evidence eagerly
    result = await db.execute(
        select(Candidate)
        .where(Candidate.id == candidate_id)
        .options(
            selectinload(Candidate.evidence_items),
            selectinload(Candidate.brand),
        )
    )
    candidate = result.scalar_one_or_none()
    if candidate is None:
        raise HTTPException(status_code=404, detail=f"Candidate '{candidate_id}' not found")

    # Fetch latest risk assessment
    latest_ra_subq = _build_latest_ra_subquery()
    ra_result = await db.execute(
        select(RiskAssessment)
        .join(
            latest_ra_subq,
            (RiskAssessment.candidate_id == latest_ra_subq.c.candidate_id)
            & (RiskAssessment.calculated_at == latest_ra_subq.c.max_calc),
        )
        .where(RiskAssessment.candidate_id == candidate_id)
    )
    ra = ra_result.scalar_one_or_none()

    # Reconstruct signal breakdown
    signals: List[SignalItem] = []
    if ra is not None:
        for signal_name, col_attr, weight in SIGNAL_MAP:
            weighted_val = getattr(ra, col_attr, None) or 0.0
            raw = (weighted_val / weight) if weight > 0 else 0.0
            raw = max(0.0, min(1.0, raw))
            reason = ra.detection_summary or f"{signal_name.replace('_', ' ').title()} signal"
            signals.append(
                SignalItem(
                    signal_name=signal_name,
                    raw_score=round(raw, 4),
                    weight=weight,
                    weighted_score=round(weighted_val, 4),
                    reason=reason,
                )
            )

    # Map evidence items
    evidence: List[EvidenceItem] = [
        EvidenceItem(
            id=ev.id,
            evidence_type=ev.evidence_type,
            severity=ev.severity,
            title=ev.title,
            description=ev.description,
            evidence_value=ev.evidence_value,
            similarity_score=ev.similarity_score,
            source=ev.source,
            source_url=ev.source_url,
            is_synthetic=ev.is_synthetic,
            collected_at=ev.collected_at,
        )
        for ev in candidate.evidence_items
    ]

    brand_name: Optional[str] = candidate.brand.name if candidate.brand else None

    return CandidateDetail(
        id=candidate.id,
        brand_id=candidate.brand_id,
        brand_name=brand_name,
        candidate_type=candidate.candidate_type,
        platform=candidate.platform,
        name=candidate.name,
        username=candidate.username,
        display_name=candidate.display_name,
        profile_url=candidate.profile_url,
        bio_description=candidate.bio_description,
        website_url=candidate.website_url,
        contact_email=candidate.contact_email,
        icon_url=candidate.icon_url,
        follower_count=candidate.follower_count,
        following_count=candidate.following_count,
        account_age_days=candidate.account_age_days,
        is_verified=candidate.is_verified,
        package_name=candidate.package_name,
        developer_name=candidate.developer_name,
        developer_email=candidate.developer_email,
        app_version=candidate.app_version,
        install_count=candidate.install_count,
        app_rating=candidate.app_rating,
        status=candidate.status,
        data_source=candidate.data_source,
        discovered_at=candidate.created_at,
        risk_score=ra.total_score if ra else None,
        risk_level=ra.risk_level if ra else None,
        confidence=ra.confidence if ra else None,
        detection_summary=ra.detection_summary if ra else None,
        ai_explanation=ra.ai_explanation if ra else None,
        signals=signals,
        evidence=evidence,
    )
