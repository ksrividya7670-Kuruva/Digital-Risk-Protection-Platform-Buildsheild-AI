"""
Minimal seed — used ONLY for verifying that the data model works end-to-end.

Creates:
  1 Brand (synthetic — NovaBank)
  1 SOCIAL_PROFILE Candidate (suspicious Twitter account)
  2 Evidence items
  1 RiskAssessment
  1 Case
  1 CaseNote

ALL DATA IS SYNTHETIC. is_synthetic=True on every evidence record.
No real persons, organisations, or accounts are referenced.

This seed is for MODEL VERIFICATION ONLY.
The full demo dataset (8+ candidates, realistic scenarios) comes in Step 4.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Brand,
    Candidate,
    CandidateType,
    CandidateStatus,
    DataSource,
    Evidence,
    EvidenceType,
    EvidenceSeverity,
    RiskAssessment,
    RiskLevel,
    Case,
    CaseNote,
    CasePriority,
    CaseStatus,
)


async def run_minimal_seed(db: AsyncSession) -> dict:
    """
    Insert one of each entity to verify the full relationship chain.
    Returns a summary dict with the created IDs.
    """

    # ── Brand ──────────────────────────────────────────────────────────────
    brand = Brand(
        id=str(uuid.uuid4()),
        name="NovaBank",
        official_domain="novabank.com",
        official_email_domain="novabank.com",
        description=(
            "Leading digital bank serving over 2 million customers. "
            "Official support: support@novabank.com"
        ),
        industry="Banking",
        twitter_handle="novabankofficial",
        instagram_handle="novabankofficial",
        official_android_package="com.novabank.app",
        official_ios_bundle_id="com.novabank.ios",
        official_developer_name="NovaBank Financial Services Ltd",
        is_active=True,
    )
    db.add(brand)
    await db.flush()  # assigns brand.id before we reference it

    # ── Candidate (suspicious social profile) ─────────────────────────────
    candidate = Candidate(
        id=str(uuid.uuid4()),
        brand_id=brand.id,
        candidate_type=CandidateType.SOCIAL_PROFILE,
        platform="Twitter",
        data_source=DataSource.MOCK,
        name="NovaBank Secure",
        username="NovaBankSecure",
        display_name="NovaBank Secure 🏦✅",
        profile_url="https://twitter.com/NovaBankSecure",
        bio_description=(
            "Official NovaBank customer support. "
            "DM us for help. support@novabank-secure.com"
        ),
        website_url="https://novabank-secure.com",
        contact_email="support@novabank-secure.com",
        follower_count=1240,
        following_count=3,
        account_age_days=14,
        is_verified=False,
        status=CandidateStatus.NEW,
    )
    db.add(candidate)
    await db.flush()

    # ── Evidence ───────────────────────────────────────────────────────────
    ev1 = Evidence(
        id=str(uuid.uuid4()),
        candidate_id=candidate.id,
        evidence_type=EvidenceType.USERNAME_SIMILARITY,
        severity=EvidenceSeverity.HIGH,
        title="Username closely matches official brand name",
        description=(
            "Candidate username 'NovaBankSecure' has high similarity "
            "to official handle 'novabankofficial'. Levenshtein similarity: 0.82."
        ),
        evidence_value="NovaBankSecure ≈ novabankofficial (0.82)",
        similarity_score=0.82,
        source="MOCK",
        is_synthetic=True,
        collected_at=datetime.now(timezone.utc),
    )
    ev2 = Evidence(
        id=str(uuid.uuid4()),
        candidate_id=candidate.id,
        evidence_type=EvidenceType.DOMAIN_RISK,
        severity=EvidenceSeverity.CRITICAL,
        title="Suspicious domain used in profile",
        description=(
            "Profile links to 'novabank-secure.com' which is not the "
            "official domain 'novabank.com'. Domain registered 12 days ago."
        ),
        evidence_value="novabank-secure.com (not official: novabank.com)",
        similarity_score=None,
        source="MOCK",
        is_synthetic=True,
        collected_at=datetime.now(timezone.utc),
    )
    db.add(ev1)
    db.add(ev2)
    await db.flush()

    # ── RiskAssessment ────────────────────────────────────────────────────
    assessment = RiskAssessment(
        id=str(uuid.uuid4()),
        candidate_id=candidate.id,
        total_score=91,
        risk_level=RiskLevel.CRITICAL,
        confidence=0.95,
        identity_similarity_score=22.0,
        visual_similarity_score=18.0,
        content_similarity_score=14.0,
        link_contact_score=15.0,
        anomaly_score=9.0,
        evidence_score=8.0,
        activity_score=5.0,
        detection_summary=(
            "CRITICAL: Strong identity match (username 82% similar), "
            "suspicious lookalike domain (novabank-secure.com), "
            "very young account (14 days), claims to be 'official support'."
        ),
        ai_explanation=None,  # populated later by AIService
        calculated_at=datetime.now(timezone.utc),
    )
    db.add(assessment)
    await db.flush()

    # ── Case ──────────────────────────────────────────────────────────────
    case = Case(
        id=str(uuid.uuid4()),
        candidate_id=candidate.id,
        brand_id=brand.id,
        title="Fake Twitter support account @NovaBankSecure",
        description=(
            "Suspicious Twitter account impersonating NovaBank official support. "
            "Risk score 91/100 CRITICAL. Lookalike domain detected."
        ),
        priority=CasePriority.CRITICAL,
        status=CaseStatus.OPEN,
        assigned_to="analyst@brandshield.demo",
        created_by="system@brandshield.demo",
    )
    db.add(case)
    await db.flush()

    # ── CaseNote ──────────────────────────────────────────────────────────
    note = CaseNote(
        id=str(uuid.uuid4()),
        case_id=case.id,
        author="analyst@brandshield.demo",
        content=(
            "Confirmed: account @NovaBankSecure is not affiliated with NovaBank. "
            "Domain novabank-secure.com registered 2 weeks ago. "
            "Initiating platform takedown request."
        ),
    )
    db.add(note)
    await db.commit()

    return {
        "brand_id": brand.id,
        "brand_name": brand.name,
        "candidate_id": candidate.id,
        "candidate_username": candidate.username,
        "evidence_count": 2,
        "assessment_id": assessment.id,
        "assessment_score": assessment.total_score,
        "assessment_level": assessment.risk_level,
        "case_id": case.id,
        "case_title": case.title,
        "note_id": note.id,
    }
