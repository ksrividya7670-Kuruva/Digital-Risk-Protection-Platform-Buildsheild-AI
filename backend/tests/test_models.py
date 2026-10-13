"""
Model verification tests.

Tests:
  1. All model imports succeed
  2. All enum values are correct
  3. Database tables are created correctly
  4. Minimal seed inserts and all relationships traverse correctly
  5. Evidence is_synthetic flag is enforced

Uses in-memory SQLite — never touches brandshield.db.

Run:
  .venv\\Scripts\\python.exe -m pytest tests/test_models.py -v
"""

import uuid
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text, select

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
async def engine():
    """Async engine against an in-memory SQLite database."""
    eng = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    yield eng
    await eng.dispose()


@pytest.fixture(scope="module")
async def tables(engine):
    """Create all ORM tables once for the whole module."""
    from app.db.database import Base
    import app.models  # noqa: F401 — registers all models with Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db(engine, tables):
    """
    Provide a fresh session for each test.
    Rolls back after the test so tests remain isolated.
    """
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Import tests (synchronous — no DB needed)
# ─────────────────────────────────────────────────────────────────────────────

def test_all_models_import():
    """Every model and enum can be imported without error."""
    from app.models import (
        Brand, Candidate, Evidence, RiskAssessment, Case, CaseNote,
        CandidateType, CandidateStatus, DataSource,
        EvidenceType, EvidenceSeverity,
        RiskLevel,
        CasePriority, CaseStatus,
    )
    assert Brand.__tablename__ == "brands"
    assert Candidate.__tablename__ == "candidates"
    assert Evidence.__tablename__ == "evidence"
    assert RiskAssessment.__tablename__ == "risk_assessments"
    assert Case.__tablename__ == "cases"
    assert CaseNote.__tablename__ == "case_notes"


def test_enum_values():
    """Key enum string values are as expected by the rest of the system."""
    from app.models import CandidateType, RiskLevel, CaseStatus, EvidenceType, DataSource

    assert CandidateType.SOCIAL_PROFILE == "SOCIAL_PROFILE"
    assert CandidateType.MOBILE_APP == "MOBILE_APP"
    assert RiskLevel.CRITICAL == "CRITICAL"
    assert RiskLevel.HIGH == "HIGH"
    assert RiskLevel.MEDIUM == "MEDIUM"
    assert RiskLevel.LOW == "LOW"
    assert CaseStatus.OPEN == "OPEN"
    assert CaseStatus.RESOLVED == "RESOLVED"
    assert CaseStatus.FALSE_POSITIVE == "FALSE_POSITIVE"
    assert EvidenceType.USERNAME_SIMILARITY == "USERNAME_SIMILARITY"
    assert EvidenceType.DOMAIN_RISK == "DOMAIN_RISK"
    assert DataSource.MOCK == "MOCK"
    assert DataSource.LIVE == "LIVE"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Schema tests
# ─────────────────────────────────────────────────────────────────────────────

async def test_all_tables_exist(engine, tables):
    """All six expected tables are present in the schema."""
    expected = {"brands", "candidates", "evidence", "risk_assessments", "cases", "case_notes"}
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        actual = {row[0] for row in result.fetchall()}
    for table in expected:
        assert table in actual, f"Missing table: '{table}'"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Full relationship chain test
# ─────────────────────────────────────────────────────────────────────────────

async def test_full_relationship_chain(db):
    """
    Brand → Candidate → Evidence + RiskAssessment + Case → CaseNote.
    All relationships must be traversable after commit.
    All demo evidence must have is_synthetic=True.
    """
    from app.demo.minimal_seed import run_minimal_seed

    summary = await run_minimal_seed(db)

    # Verify returned IDs
    assert summary["brand_id"]
    assert summary["candidate_id"]
    assert summary["assessment_id"]
    assert summary["case_id"]
    assert summary["note_id"]
    assert summary["evidence_count"] == 2
    assert summary["assessment_score"] == 91
    assert summary["assessment_level"] == "CRITICAL"

    # Re-fetch brand from DB
    from app.models import Brand, Candidate
    brand = (await db.execute(
        select(Brand).where(Brand.id == summary["brand_id"])
    )).scalar_one()
    assert brand.name == "NovaBank"
    assert brand.official_domain == "novabank.com"
    assert brand.twitter_handle == "novabankofficial"

    # Brand → Candidates relationship
    await db.refresh(brand, ["candidates"])
    assert len(brand.candidates) == 1
    candidate = brand.candidates[0]
    assert candidate.username == "NovaBankSecure"
    assert candidate.candidate_type == "SOCIAL_PROFILE"
    assert candidate.platform == "Twitter"
    assert candidate.data_source == "MOCK"
    assert candidate.account_age_days == 14

    # Candidate → Evidence
    await db.refresh(candidate, ["evidence_items"])
    assert len(candidate.evidence_items) == 2
    for ev in candidate.evidence_items:
        assert ev.is_synthetic is True, (
            f"Evidence {ev.id} is not marked synthetic — "
            "all demo data MUST have is_synthetic=True"
        )

    # Candidate → RiskAssessment
    await db.refresh(candidate, ["risk_assessments"])
    assert len(candidate.risk_assessments) == 1
    ra = candidate.risk_assessments[0]
    assert ra.total_score == 91
    assert ra.risk_level == "CRITICAL"
    # Score components present
    assert ra.identity_similarity_score == 22.0
    assert ra.visual_similarity_score == 18.0
    # AI explanation NOT set yet — set by AIService in a later step
    assert ra.ai_explanation is None

    # Candidate → Case
    await db.refresh(candidate, ["cases"])
    assert len(candidate.cases) == 1
    case = candidate.cases[0]
    assert case.status == "OPEN"
    assert case.priority == "CRITICAL"
    assert case.brand_id == brand.id

    # Case → CaseNotes
    await db.refresh(case, ["notes"])
    assert len(case.notes) == 1
    note = case.notes[0]
    assert "NovaBankSecure" in note.content
    assert note.author == "analyst@brandshield.demo"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Mobile app candidate test
# ─────────────────────────────────────────────────────────────────────────────

async def test_mobile_app_candidate(db):
    """A MOBILE_APP candidate stores app-specific fields correctly."""
    from app.models import Brand, Candidate, CandidateType, CandidateStatus, DataSource

    brand = Brand(id=str(uuid.uuid4()), name="TestCorp", official_domain="testcorp.com")
    db.add(brand)
    await db.flush()

    app_candidate = Candidate(
        id=str(uuid.uuid4()),
        brand_id=brand.id,
        candidate_type=CandidateType.MOBILE_APP,
        platform="Google Play",
        data_source=DataSource.MOCK,
        name="TestCorp Mobile Banking",
        package_name="com.testcorp.bank.fake",
        developer_name="Unknown Developer LLC",
        developer_email="dev@shady.xyz",
        app_version="1.0.0",
        install_count=5200,
        status=CandidateStatus.NEW,
    )
    db.add(app_candidate)
    await db.flush()

    result = await db.execute(
        select(Candidate).where(Candidate.id == app_candidate.id)
    )
    fetched = result.scalar_one()
    assert fetched.candidate_type == "MOBILE_APP"
    assert fetched.package_name == "com.testcorp.bank.fake"
    assert fetched.developer_name == "Unknown Developer LLC"
    assert fetched.follower_count is None   # Social-only field — should be null
    assert fetched.username is None         # Not set for app candidates


# ─────────────────────────────────────────────────────────────────────────────
# 5. Evidence integrity test
# ─────────────────────────────────────────────────────────────────────────────

async def test_evidence_synthetic_flag(db):
    """Evidence records must have is_synthetic explicitly set."""
    from app.models import Brand, Candidate, CandidateType, DataSource, Evidence, EvidenceType, EvidenceSeverity

    brand = Brand(id=str(uuid.uuid4()), name="FlagTestBrand")
    db.add(brand)
    await db.flush()

    candidate = Candidate(
        id=str(uuid.uuid4()),
        brand_id=brand.id,
        candidate_type=CandidateType.SOCIAL_PROFILE,
        platform="Instagram",
        data_source=DataSource.MOCK,
    )
    db.add(candidate)
    await db.flush()

    ev = Evidence(
        id=str(uuid.uuid4()),
        candidate_id=candidate.id,
        evidence_type=EvidenceType.BIO_SIMILARITY,
        severity=EvidenceSeverity.MEDIUM,
        title="Bio text overlap",
        evidence_value="similarity: 0.74",
        similarity_score=0.74,
        is_synthetic=True,
    )
    db.add(ev)
    await db.flush()

    result = await db.execute(select(Evidence).where(Evidence.id == ev.id))
    fetched = result.scalar_one()
    assert fetched.is_synthetic is True
    assert fetched.similarity_score == pytest.approx(0.74)
    assert fetched.evidence_type == "BIO_SIMILARITY"
