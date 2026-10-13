"""
Demo API — seed and reset endpoints (only available when DEMO_MODE=true).

POST /api/v1/demo/seed   → seed demo data (idempotent)
POST /api/v1/demo/reset  → clear and re-seed demo data
GET  /api/v1/demo/status → dataset summary
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.db.database import get_db
from app.demo.seed_demo import seed_all, reset_and_reseed
from app.models import Brand, Candidate, RiskAssessment

router = APIRouter()


def _require_demo_mode():
    if not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo endpoints are disabled. Set DEMO_MODE=true to enable.",
        )


@router.post("/seed", summary="Seed demo dataset (idempotent)")
async def seed_demo(db: AsyncSession = Depends(get_db)):
    _require_demo_mode()
    summary = await seed_all(db)
    return {
        "message": "Demo dataset seeded successfully.",
        "data_note": (
            "ALL data is synthetic. "
            "No real persons, companies, or accounts are represented."
        ),
        **summary,
    }


@router.post("/reset", summary="Reset and re-seed demo dataset")
async def reset_demo(db: AsyncSession = Depends(get_db)):
    _require_demo_mode()
    summary = await reset_and_reseed(db)
    return {
        "message": "Demo dataset reset and re-seeded.",
        "data_note": (
            "ALL data is synthetic. "
            "No real persons, companies, or accounts are represented."
        ),
        **summary,
    }


@router.get("/status", summary="Get demo dataset status")
async def demo_status(db: AsyncSession = Depends(get_db)):
    _require_demo_mode()

    brand_result = await db.execute(
        select(Brand).where(Brand.name == "NovaPay")
    )
    brand = brand_result.scalar_one_or_none()

    if not brand:
        return {
            "seeded": False,
            "message": "Demo dataset not yet seeded. Call POST /api/v1/demo/seed."
        }

    candidate_count = await db.scalar(
        select(func.count(Candidate.id)).where(Candidate.brand_id == brand.id)
    )
    assessment_count = await db.scalar(
        select(func.count(RiskAssessment.id))
        .join(Candidate, RiskAssessment.candidate_id == Candidate.id)
        .where(Candidate.brand_id == brand.id)
    )

    return {
        "seeded": True,
        "brand": brand.name,
        "total_candidates": candidate_count,
        "risk_assessments": assessment_count,
        "data_note": "ALL data is synthetic.",
    }
