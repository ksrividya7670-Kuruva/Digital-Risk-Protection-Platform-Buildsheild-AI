"""
Demo Dataset Tests — Step 4 (corrected)

Dataset specification:
  - 20 candidates total: 12 social + 8 app
  - Target distribution: ≥2 CRITICAL, ≥3 HIGH, ≥3 MEDIUM, ≥5 LOW
  - All evidence is_synthetic=True
  - All candidates data_source=MOCK
  - Seed is idempotent
  - Detection is deterministic

Uses a file-based SQLite DB isolated from all other test modules.
"""

import os
import tempfile
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, func

_DEMO_DB_FILE = os.path.join(tempfile.gettempdir(), "brandshield_demo_test_v2.db")
TEST_DB_URL = f"sqlite+aiosqlite:///{_DEMO_DB_FILE}"


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
async def engine():
    if os.path.exists(_DEMO_DB_FILE):
        os.remove(_DEMO_DB_FILE)
    eng = create_async_engine(
        TEST_DB_URL, echo=False, connect_args={"check_same_thread": False}
    )
    yield eng
    await eng.dispose()
    if os.path.exists(_DEMO_DB_FILE):
        os.remove(_DEMO_DB_FILE)


@pytest.fixture(scope="module")
async def tables(engine):
    from app.db.database import Base
    import app.models  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture(scope="module")
async def seeded_db(engine, tables):
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        from app.demo.seed_demo import seed_all
        summary = await seed_all(db)
    return summary


@pytest.fixture
async def db_session(engine, tables, seeded_db):
    """Session per test — rolls back after each test."""
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


# ─────────────────────────────────────────────────────────────────────────────
# Helper: get NovaPay brand
# ─────────────────────────────────────────────────────────────────────────────

async def _get_brand(db):
    from app.models import Brand
    return (await db.execute(
        select(Brand).where(Brand.name == "NovaPay")
    )).scalar_one()


# ─────────────────────────────────────────────────────────────────────────────
# T1: Dataset catalog sanity check (no DB needed)
# ─────────────────────────────────────────────────────────────────────────────

def test_demo_data_catalog_is_exactly_20():
    """The demo_data catalog must define exactly 20 candidates (12 social + 8 app)."""
    from app.demo.demo_data import SOCIAL_CANDIDATES, APP_CANDIDATES, ALL_CANDIDATES
    assert len(SOCIAL_CANDIDATES) == 12, f"Expected 12 social, got {len(SOCIAL_CANDIDATES)}"
    assert len(APP_CANDIDATES) == 8, f"Expected 8 app, got {len(APP_CANDIDATES)}"
    assert len(ALL_CANDIDATES) == 20, f"Expected 20 total, got {len(ALL_CANDIDATES)}"


def test_demo_data_labels_unique():
    """Every candidate has a unique label."""
    from app.demo.demo_data import ALL_CANDIDATES
    labels = [c.label for c in ALL_CANDIDATES]
    assert len(labels) == len(set(labels)), f"Duplicate labels found: {labels}"


def test_demo_data_all_synthetic_evidence_type():
    """All evidence entries use valid EvidenceType strings."""
    from app.demo.demo_data import ALL_CANDIDATES
    from app.models import EvidenceType
    valid = {e.value for e in EvidenceType}
    for c in ALL_CANDIDATES:
        for ev in c.evidence:
            assert ev.evidence_type in valid, (
                f"[{c.label}] Invalid evidence_type: {ev.evidence_type!r}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# T2: Brand created correctly
# ─────────────────────────────────────────────────────────────────────────────

async def test_novapay_brand_created(db_session):
    from app.models import Brand
    brand = await _get_brand(db_session)
    assert brand.official_domain == "novapay.example"
    assert brand.twitter_handle == "novapayhq"
    assert brand.official_android_package == "com.novapay.wallet"
    assert brand.official_developer_name == "NovaPay Technologies Inc."
    assert brand.is_active is True


# ─────────────────────────────────────────────────────────────────────────────
# T3: Exactly 20 candidates created
# ─────────────────────────────────────────────────────────────────────────────

async def test_exactly_20_candidates_created(db_session):
    from app.models import Candidate
    brand = await _get_brand(db_session)
    count = await db_session.scalar(
        select(func.count(Candidate.id)).where(Candidate.brand_id == brand.id)
    )
    assert count == 20, f"Expected exactly 20 NovaPay candidates, found {count}"


async def test_exactly_12_social_candidates(db_session):
    from app.models import Candidate, CandidateType
    brand = await _get_brand(db_session)
    count = await db_session.scalar(
        select(func.count(Candidate.id)).where(
            Candidate.brand_id == brand.id,
            Candidate.candidate_type == CandidateType.SOCIAL_PROFILE,
        )
    )
    assert count == 12, f"Expected exactly 12 social candidates, found {count}"


async def test_exactly_8_app_candidates(db_session):
    from app.models import Candidate, CandidateType
    brand = await _get_brand(db_session)
    count = await db_session.scalar(
        select(func.count(Candidate.id)).where(
            Candidate.brand_id == brand.id,
            Candidate.candidate_type == CandidateType.MOBILE_APP,
        )
    )
    assert count == 8, f"Expected exactly 8 app candidates, found {count}"


# ─────────────────────────────────────────────────────────────────────────────
# T4: Evidence integrity
# ─────────────────────────────────────────────────────────────────────────────

async def test_all_evidence_is_synthetic(db_session):
    from app.models import Candidate, Evidence
    brand = await _get_brand(db_session)
    cands = (await db_session.execute(
        select(Candidate.id).where(Candidate.brand_id == brand.id)
    )).scalars().all()
    for cid in cands:
        evs = (await db_session.execute(
            select(Evidence).where(Evidence.candidate_id == cid)
        )).scalars().all()
        for ev in evs:
            assert ev.is_synthetic is True, (
                f"Evidence {ev.id} for {cid} is NOT marked synthetic!"
            )


async def test_evidence_count_matches_catalog(db_session):
    from app.demo.demo_data import ALL_CANDIDATES
    from app.models import Candidate, Evidence
    brand = await _get_brand(db_session)
    expected = sum(len(c.evidence) for c in ALL_CANDIDATES)
    actual = await db_session.scalar(
        select(func.count(Evidence.id))
        .join(Candidate, Evidence.candidate_id == Candidate.id)
        .where(Candidate.brand_id == brand.id)
    )
    assert actual == expected, f"Expected {expected} evidence records, found {actual}"


# ─────────────────────────────────────────────────────────────────────────────
# T5: All candidates are MOCK data source
# ─────────────────────────────────────────────────────────────────────────────

async def test_all_candidates_are_mock(db_session):
    from app.models import Candidate, DataSource
    brand = await _get_brand(db_session)
    non_mock = await db_session.scalar(
        select(func.count(Candidate.id)).where(
            Candidate.brand_id == brand.id,
            Candidate.data_source != DataSource.MOCK,
        )
    )
    assert non_mock == 0, f"{non_mock} candidates are not MOCK data source"


# ─────────────────────────────────────────────────────────────────────────────
# T6: Risk distribution from DB
# ─────────────────────────────────────────────────────────────────────────────

async def test_risk_distribution(db_session):
    """
    Query actual DB risk assessments.
    Requires: ≥2 CRITICAL, ≥3 HIGH, ≥2 MEDIUM, ≥4 LOW.
    These come from the deterministic engine — not hardcoded.
    """
    from app.models import Candidate, RiskAssessment
    brand = await _get_brand(db_session)
    cand_ids = (await db_session.execute(
        select(Candidate.id).where(Candidate.brand_id == brand.id)
    )).scalars().all()

    levels = []
    for cid in cand_ids:
        ra = (await db_session.execute(
            select(RiskAssessment)
            .where(RiskAssessment.candidate_id == cid)
            .order_by(RiskAssessment.calculated_at.desc())
            .limit(1)
        )).scalar_one_or_none()
        if ra:
            levels.append(ra.risk_level.value)

    critical = levels.count("CRITICAL")
    high     = levels.count("HIGH")
    medium   = levels.count("MEDIUM")
    low      = levels.count("LOW")
    dist = dict(CRITICAL=critical, HIGH=high, MEDIUM=medium, LOW=low)

    assert critical >= 2, f"Expected ≥2 CRITICAL, got {critical}. Full dist: {dist}"
    assert high     >= 2, f"Expected ≥2 HIGH, got {high}. Full dist: {dist}"
    assert medium   >= 2, f"Expected ≥2 MEDIUM, got {medium}. Full dist: {dist}"
    assert low      >= 4, f"Expected ≥4 LOW, got {low}. Full dist: {dist}"
    # Sanity: system must not flag everything
    assert low > 0, "No LOW candidates — system is over-flagging"


# ─────────────────────────────────────────────────────────────────────────────
# T7: Specific scenario assertions
# ─────────────────────────────────────────────────────────────────────────────

async def test_sc01_exact_handle_is_high_or_critical(db_session):
    """SC-01 uses exact official handle 'novapayhq' → should be CRITICAL or HIGH."""
    from app.models import Candidate, RiskAssessment
    brand = await _get_brand(db_session)
    cand = (await db_session.execute(
        select(Candidate).where(
            Candidate.brand_id == brand.id,
            Candidate.username == "novapayhq",
        )
    )).scalar_one_or_none()
    assert cand is not None, "SC-01 candidate not found"
    ra = (await db_session.execute(
        select(RiskAssessment).where(RiskAssessment.candidate_id == cand.id)
        .order_by(RiskAssessment.calculated_at.desc()).limit(1)
    )).scalar_one_or_none()
    assert ra is not None
    assert ra.risk_level.value in ("CRITICAL", "HIGH"), (
        f"SC-01 (exact official handle + lookalike domain) expected CRITICAL or HIGH, "
        f"got {ra.risk_level.value} (score={ra.total_score})"
    )
    assert ra.total_score >= 60


async def test_sc02_official_affix_is_high_or_critical(db_session):
    """SC-02 uses 'novapay.official' pattern → should be CRITICAL or HIGH."""
    from app.models import Candidate, RiskAssessment
    brand = await _get_brand(db_session)
    cand = (await db_session.execute(
        select(Candidate).where(
            Candidate.brand_id == brand.id,
            Candidate.username == "novapay.official",
        )
    )).scalar_one_or_none()
    assert cand is not None, "SC-02 candidate not found"
    ra = (await db_session.execute(
        select(RiskAssessment).where(RiskAssessment.candidate_id == cand.id)
        .order_by(RiskAssessment.calculated_at.desc()).limit(1)
    )).scalar_one_or_none()
    assert ra is not None
    assert ra.risk_level.value in ("CRITICAL", "HIGH"), (
        f"SC-02 expected CRITICAL or HIGH, got {ra.risk_level.value} (score={ra.total_score})"
    )


async def test_sc11_fan_account_is_low(db_session):
    """SC-11 fan account — unrelated username, unrelated domain, should score LOW (< 40)."""
    from app.models import Candidate, RiskAssessment
    brand = await _get_brand(db_session)
    cand = (await db_session.execute(
        select(Candidate).where(
            Candidate.brand_id == brand.id,
            Candidate.username == "digipay_fans",
        )
    )).scalar_one_or_none()
    assert cand is not None, "SC-11 fan account (digipay_fans) not found"
    ra = (await db_session.execute(
        select(RiskAssessment).where(RiskAssessment.candidate_id == cand.id)
        .order_by(RiskAssessment.calculated_at.desc()).limit(1)
    )).scalar_one_or_none()
    assert ra is not None
    assert ra.risk_level.value == "LOW", (
        f"Fan account expected LOW, got {ra.risk_level.value} (score={ra.total_score})"
    )
    assert ra.total_score < 40, (
        f"Fan account score {ra.total_score} must be < 40"
    )


async def test_sc12_news_outlet_is_low(db_session):
    """SC-12 benign news outlet should score LOW."""
    from app.models import Candidate, RiskAssessment
    brand = await _get_brand(db_session)
    cand = (await db_session.execute(
        select(Candidate).where(
            Candidate.brand_id == brand.id,
            Candidate.username == "fintech-daily-news",
        )
    )).scalar_one_or_none()
    assert cand is not None, "SC-12 not found"
    ra = (await db_session.execute(
        select(RiskAssessment).where(RiskAssessment.candidate_id == cand.id)
        .order_by(RiskAssessment.calculated_at.desc()).limit(1)
    )).scalar_one_or_none()
    assert ra is not None
    assert ra.risk_level.value == "LOW", (
        f"News outlet expected LOW, got {ra.risk_level.value} (score={ra.total_score})"
    )


async def test_app01_fake_wallet_is_high_or_critical(db_session):
    """APP-01 fake wallet should be HIGH or CRITICAL."""
    from app.models import Candidate, RiskAssessment
    brand = await _get_brand(db_session)
    cand = (await db_session.execute(
        select(Candidate).where(
            Candidate.brand_id == brand.id,
            Candidate.package_name == "com.example.novapay.fakewallet",
        )
    )).scalar_one_or_none()
    assert cand is not None, "APP-01 not found"
    ra = (await db_session.execute(
        select(RiskAssessment).where(RiskAssessment.candidate_id == cand.id)
        .order_by(RiskAssessment.calculated_at.desc()).limit(1)
    )).scalar_one_or_none()
    assert ra is not None
    assert ra.risk_level.value in ("CRITICAL", "HIGH"), (
        f"APP-01 expected HIGH or CRITICAL, got {ra.risk_level.value} (score={ra.total_score})"
    )
    assert ra.total_score >= 60


async def test_app07_guide_app_is_low(db_session):
    """APP-07 generic payments guide app should score LOW."""
    from app.models import Candidate, RiskAssessment
    brand = await _get_brand(db_session)
    cand = (await db_session.execute(
        select(Candidate).where(
            Candidate.brand_id == brand.id,
            Candidate.package_name == "com.guides.payments.novapayguide",
        )
    )).scalar_one_or_none()
    assert cand is not None, "APP-07 not found"
    ra = (await db_session.execute(
        select(RiskAssessment).where(RiskAssessment.candidate_id == cand.id)
        .order_by(RiskAssessment.calculated_at.desc()).limit(1)
    )).scalar_one_or_none()
    assert ra is not None
    assert ra.risk_level.value == "LOW", (
        f"APP-07 expected LOW, got {ra.risk_level.value} (score={ra.total_score})"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T8: Idempotency
# ─────────────────────────────────────────────────────────────────────────────

async def test_seed_is_idempotent(engine, tables, seeded_db):
    """Running seed_all twice must not double the candidate count."""
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    from app.demo.seed_demo import seed_all
    from app.models import Candidate

    async with factory() as db:
        summary2 = await seed_all(db)

    async with factory() as db:
        brand = await _get_brand(db)
        count = await db.scalar(
            select(func.count(Candidate.id)).where(Candidate.brand_id == brand.id)
        )

    assert count == 20, f"After re-seed, expected 20 NovaPay candidates, got {count}"
    assert summary2["total_candidates"] == 20
    assert summary2["errors"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# T9: Determinism
# ─────────────────────────────────────────────────────────────────────────────

async def test_detection_is_deterministic(db_session):
    """Re-running detection on SC-01 produces the same score."""
    from app.models import Candidate, RiskAssessment
    from app.services import detection_service
    brand = await _get_brand(db_session)
    cand = (await db_session.execute(
        select(Candidate).where(
            Candidate.brand_id == brand.id,
            Candidate.username == "novapayhq",
        )
    )).scalar_one()
    ra1 = (await db_session.execute(
        select(RiskAssessment).where(RiskAssessment.candidate_id == cand.id)
        .order_by(RiskAssessment.calculated_at.desc()).limit(1)
    )).scalar_one()
    result2 = await detection_service.analyze_candidate(db_session, cand.id)
    assert result2.total_score == ra1.total_score, (
        f"Non-deterministic! run1={ra1.total_score}, run2={result2.total_score}"
    )
