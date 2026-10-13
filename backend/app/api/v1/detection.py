"""
Detection API — minimal endpoints to trigger and retrieve risk assessments.

POST /api/v1/detection/candidates/{candidate_id}/analyze
  → Run the detection engine for a candidate; persist and return result.

GET  /api/v1/detection/candidates/{candidate_id}/risk
  → Retrieve the latest persisted RiskAssessment for a candidate.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.detection import DetectionResultSchema, RiskAssessmentSchema
from app.services import detection_service

router = APIRouter()


@router.post(
    "/candidates/{candidate_id}/analyze",
    response_model=DetectionResultSchema,
    summary="Run detection engine for a candidate",
    description=(
        "Executes all seven deterministic signal calculators against the candidate "
        "and its associated brand. Persists the RiskAssessment and returns the full result. "
        "Safe to call multiple times — recalculation replaces the previous assessment."
    ),
    status_code=status.HTTP_200_OK,
)
async def analyze_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
) -> DetectionResultSchema:
    try:
        result = await detection_service.analyze_candidate(db, candidate_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    return DetectionResultSchema(
        candidate_id=result.candidate_id,
        brand_id=result.brand_id,
        total_score=result.total_score,
        risk_level=result.risk_level,
        confidence=result.confidence,
        signals=[
            {
                "signal_name": s.signal_name,
                "raw_score": s.raw_score,
                "weight": s.weight,
                "weighted_score": s.weighted_score,
                "reason": s.reason,
                "metadata": s.metadata,
            }
            for s in result.signals
        ],
        reasons=result.reasons,
        explanation=result.explanation,
        identity_similarity_score=result.identity_similarity_score,
        visual_similarity_score=result.visual_similarity_score,
        content_similarity_score=result.content_similarity_score,
        link_contact_score=result.link_contact_score,
        anomaly_score=result.anomaly_score,
        evidence_score_val=result.evidence_score_val,
        activity_score=result.activity_score,
    )


@router.get(
    "/candidates/{candidate_id}/risk",
    response_model=RiskAssessmentSchema,
    summary="Get latest risk assessment for a candidate",
    description=(
        "Returns the most recent persisted RiskAssessment for the candidate. "
        "Returns 404 if no assessment has been run yet."
    ),
)
async def get_risk_assessment(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
) -> RiskAssessmentSchema:
    ra = await detection_service.get_latest_assessment(db, candidate_id)
    if ra is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No risk assessment found for candidate '{candidate_id}'. "
                "Run POST /analyze first."
            ),
        )
    return RiskAssessmentSchema.model_validate(ra)
