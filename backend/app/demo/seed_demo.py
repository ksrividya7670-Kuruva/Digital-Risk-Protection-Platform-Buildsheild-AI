"""
BrandShield AI — Demo Dataset Seeder

Seeds the NovaPay synthetic demo dataset into the database.

Safe to run repeatedly:
  - On first run: creates brand + all candidates + evidence + risk assessments
  - On re-run: detects existing NovaPay brand and skips re-creation; 
    re-runs detection on existing candidates to refresh scores.

Usage (from backend/ directory, venv activated):
    python -m app.demo.seed_demo

Or call seed_all() from the FastAPI /api/v1/demo/seed endpoint.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.demo.demo_data import NOVAPAY_BRAND, ALL_CANDIDATES, CandidateDef, EvidenceDef
from app.models import (
    Brand, Candidate, Evidence,
    CandidateType, CandidateStatus, DataSource,
    EvidenceType, EvidenceSeverity,
    RiskLevel,
)
from app.services import detection_service


# ─────────────────────────────────────────────────────────────────────────────
# Public entry points
# ─────────────────────────────────────────────────────────────────────────────

async def seed_all(db: AsyncSession) -> dict:
    """
    Seed the full demo dataset. Safe to call multiple times.
    Returns a summary dict with counts and score statistics.
    """
    brand = await _get_or_create_brand(db)
    candidate_ids = await _seed_candidates(db, brand)
    results = await _run_detection_on_all(db, candidate_ids)
    summary = _build_summary(results)
    return summary


async def reset_and_reseed(db: AsyncSession) -> dict:
    """
    Delete all demo data (candidates under the NovaPay brand) and re-seed.
    WARNING: deletes all NovaPay candidate/evidence/assessment data.
    """
    # Find and delete existing NovaPay brand (cascades to candidates, evidence, etc.)
    existing = await db.execute(
        select(Brand).where(Brand.name == "NovaPay")
    )
    brand = existing.scalar_one_or_none()
    if brand:
        await db.delete(brand)
        await db.commit()
    return await seed_all(db)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _get_or_create_brand(db: AsyncSession) -> Brand:
    """Return existing NovaPay brand or create it."""
    result = await db.execute(
        select(Brand).where(Brand.name == "NovaPay")
    )
    brand = result.scalar_one_or_none()
    if brand:
        return brand

    brand = Brand(
        id=str(uuid.uuid4()),
        **NOVAPAY_BRAND,
    )
    db.add(brand)
    await db.flush()
    return brand


async def _seed_candidates(db: AsyncSession, brand: Brand) -> list[str]:
    """
    Create all candidate + evidence records.
    Skips candidates that already exist (matched by label in display_name prefix).
    Returns list of candidate IDs to process.
    """
    candidate_ids: list[str] = []

    for cdef in ALL_CANDIDATES:
        # Check if this candidate already exists (use label as a marker in display_name)
        marker = f"[{cdef.label}]"
        existing = await db.execute(
            select(Candidate).where(
                Candidate.brand_id == brand.id,
                Candidate.display_name.like(f"%{marker}%"),
            )
        )
        existing_cand = existing.scalar_one_or_none()

        if existing_cand:
            candidate_ids.append(existing_cand.id)
            continue

        candidate = await _create_candidate(db, brand.id, cdef, marker)
        await _create_evidence(db, candidate.id, cdef.evidence)
        candidate_ids.append(candidate.id)

    await db.commit()
    return candidate_ids


async def _create_candidate(
    db: AsyncSession, brand_id: str, cdef: CandidateDef, label_marker: str
) -> Candidate:
    """Build and insert one Candidate record."""
    # Embed label marker in display_name for idempotent re-seeding
    display_name = cdef.display_name or cdef.name or ""
    if label_marker not in display_name:
        display_name = f"{display_name} {label_marker}".strip()

    candidate = Candidate(
        id=str(uuid.uuid4()),
        brand_id=brand_id,
        candidate_type=CandidateType(cdef.candidate_type),
        platform=cdef.platform,
        data_source=DataSource.MOCK,
        name=cdef.name,
        username=cdef.username,
        display_name=display_name,
        bio_description=cdef.bio_description,
        website_url=cdef.website_url,
        contact_email=cdef.contact_email,
        profile_url=cdef.profile_url,
        icon_url=cdef.icon_url,
        icon_perceptual_hash=cdef.icon_perceptual_hash,
        follower_count=cdef.follower_count,
        following_count=cdef.following_count,
        account_age_days=cdef.account_age_days,
        is_verified=cdef.is_verified,
        package_name=cdef.package_name,
        developer_name=cdef.developer_name,
        developer_email=cdef.developer_email,
        app_version=cdef.app_version,
        install_count=cdef.install_count,
        app_rating=cdef.app_rating,
        status=CandidateStatus.NEW,
    )
    db.add(candidate)
    await db.flush()
    return candidate


async def _create_evidence(
    db: AsyncSession, candidate_id: str, evidence_list: list[EvidenceDef]
) -> None:
    """Insert evidence records for a candidate."""
    for edef in evidence_list:
        ev = Evidence(
            id=str(uuid.uuid4()),
            candidate_id=candidate_id,
            evidence_type=EvidenceType(edef.evidence_type),
            severity=EvidenceSeverity(edef.severity),
            title=edef.title,
            description=edef.description,
            evidence_value=edef.evidence_value,
            source=edef.source,
            source_url=edef.source_url,
            similarity_score=edef.similarity_score,
            is_synthetic=True,   # ALL demo evidence MUST be marked synthetic
            collected_at=datetime.now(timezone.utc),
        )
        db.add(ev)


async def _run_detection_on_all(
    db: AsyncSession, candidate_ids: list[str]
) -> list[dict]:
    """Run detection engine on all candidates and collect results."""
    results = []
    for cid in candidate_ids:
        try:
            result = await detection_service.analyze_candidate(db, cid)
            results.append({
                "candidate_id": cid,
                "score": result.total_score,
                "level": result.risk_level,
                "confidence": result.confidence,
                "explanation": result.explanation[:100],
            })
        except Exception as exc:
            results.append({
                "candidate_id": cid,
                "error": str(exc),
                "score": 0,
                "level": "ERROR",
                "confidence": 0.0,
                "explanation": "",
            })
    return results


def _build_summary(results: list[dict]) -> dict:
    """Build a summary dict from detection results."""
    scores = [r["score"] for r in results if "error" not in r]
    levels = [r["level"] for r in results if "error" not in r]

    return {
        "total_candidates": len(results),
        "errors": sum(1 for r in results if "error" in r),
        "critical": levels.count("CRITICAL"),
        "high": levels.count("HIGH"),
        "medium": levels.count("MEDIUM"),
        "low": levels.count("LOW"),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "max_score": max(scores) if scores else 0,
        "min_score": min(scores) if scores else 0,
        "results": results,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

async def _cli_main() -> None:
    """Run the seeder from the command line."""
    import sys
    import os
    # Ensure backend/ is in sys.path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from app.db.database import AsyncSessionLocal, create_all_tables, engine
    from app.db.database import Base
    import app.models  # noqa: register all models

    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        reset = "--reset" in sys.argv
        if reset:
            print("🗑  Resetting demo data...")
            summary = await reset_and_reseed(db)
        else:
            print("🌱  Seeding demo data...")
            summary = await seed_all(db)

    print("\n══════════════════════════════════════════")
    print("  BrandShield AI — Demo Dataset Seeded")
    print("══════════════════════════════════════════")
    print(f"  Total candidates : {summary['total_candidates']}")
    print(f"  CRITICAL         : {summary['critical']}")
    print(f"  HIGH             : {summary['high']}")
    print(f"  MEDIUM           : {summary['medium']}")
    print(f"  LOW              : {summary['low']}")
    print(f"  Errors           : {summary['errors']}")
    print(f"  Average score    : {summary['avg_score']}")
    print(f"  Highest score    : {summary['max_score']}")
    print(f"  Lowest score     : {summary['min_score']}")
    print("══════════════════════════════════════════\n")

    # Show per-candidate breakdown
    print("  Candidate breakdown:")
    print(f"  {'Label':<10} {'Score':>5}  {'Level':<10}  {'Confidence':>10}")
    print("  " + "─" * 44)
    for r in summary["results"]:
        if "error" in r:
            print(f"  {'ERROR':<10} {'?':>5}  {'ERROR':<10}  {'?':>10}")
        else:
            print(
                f"  {r['candidate_id'][:8]:<10} "
                f"{r['score']:>5}  "
                f"{r['level']:<10}  "
                f"{r['confidence']:>10.3f}"
            )


if __name__ == "__main__":
    asyncio.run(_cli_main())
