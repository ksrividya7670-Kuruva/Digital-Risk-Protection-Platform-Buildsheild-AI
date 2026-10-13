"""
Detection Engine Tests — Step 3

Tests verify:
  T1:  Strong identity + suspicious link + evidence → CRITICAL or HIGH
  T2:  Moderate identity + limited evidence → MEDIUM
  T3:  Fan account (brand content, no suspicious signals) → LOW
  T4:  Mobile app with brand name + unrelated developer → HIGH or CRITICAL
  T5:  Insufficient data → no artificial inflation
  T6:  Same candidate twice → identical result (deterministic)
  T7:  Signal weights sum to exactly 100
  T8:  Confidence ≠ risk_score

All tests use pure in-memory data — no database required for engine unit tests.
DB integration tests are in test_detection_db.py.
"""

import pytest
from app.services.detection.contracts import (
    SIGNAL_WEIGHTS, classify_risk, calculate_confidence,
)
from app.services.detection.risk_engine import run, CandidateBundle
from app.services.detection.evidence_score import EvidenceItem
from app.services.detection import (
    identity_similarity, visual_similarity, content_similarity,
    link_risk, account_anomaly, evidence_score, activity_anomaly,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _base_brand() -> dict:
    return dict(
        brand_name="NovaBank",
        brand_description="Leading digital bank serving 2 million customers. Official support: support@novabank.com",
        brand_official_handles=["novabankofficial", "novabank"],
        brand_official_domain="novabank.com",
        brand_official_email_domain="novabank.com",
        brand_logo_hash=None,
        brand_official_developer_name="NovaBank Financial Services Ltd",
    )


def _make_bundle(**overrides) -> CandidateBundle:
    """Build a CandidateBundle with sensible defaults, overridable per test."""
    defaults = dict(
        candidate_id="test-cand-001",
        brand_id="test-brand-001",
        candidate_type="SOCIAL_PROFILE",
        **_base_brand(),
        candidate_username=None,
        candidate_display_name=None,
        candidate_name=None,
        candidate_bio=None,
        candidate_website=None,
        candidate_email=None,
        candidate_icon_hash=None,
        follower_count=None,
        following_count=None,
        account_age_days=None,
        is_verified=None,
        package_name=None,
        developer_name=None,
        developer_email=None,
        app_version=None,
        install_count=None,
        evidence_items=[],
    )
    defaults.update(overrides)
    return CandidateBundle(**defaults)


# ─────────────────────────────────────────────────────────────────────────────
# T7: Weight integrity (run first — prerequisite for everything else)
# ─────────────────────────────────────────────────────────────────────────────

def test_signal_weights_sum_to_100():
    """All signal weights must sum to exactly 100."""
    total = sum(SIGNAL_WEIGHTS.values())
    assert total == 100, f"Weights sum to {total}, expected 100"


def test_signal_weight_keys():
    """All seven expected signals are present in the weight table."""
    expected = {
        "identity_similarity", "visual_similarity", "content_similarity",
        "link_risk", "account_anomaly", "evidence_score", "activity_anomaly",
    }
    assert set(SIGNAL_WEIGHTS.keys()) == expected


# ─────────────────────────────────────────────────────────────────────────────
# T1: Strong identity + suspicious domain + evidence → HIGH or CRITICAL
# ─────────────────────────────────────────────────────────────────────────────

def test_strong_identity_suspicious_domain_is_high_or_critical():
    """
    Scenario: Fake support account
      - Username nearly identical to brand handle
      - Suspicious lookalike domain in profile
      - Account is 14 days old
      - Has HIGH severity evidence
    Expected: CRITICAL or HIGH
    """
    bundle = _make_bundle(
        candidate_username="NovaBankSecure",
        candidate_display_name="NovaBank Secure 🏦",
        candidate_bio="Official NovaBank customer support. DM for help.",
        candidate_website="https://novabank-secure.com",
        candidate_email="support@novabank-secure.com",
        account_age_days=14,
        follower_count=800,
        following_count=3,
        is_verified=False,
        evidence_items=[
            EvidenceItem("USERNAME_SIMILARITY", "HIGH", 0.82, "Username closely matches brand"),
            EvidenceItem("DOMAIN_RISK", "CRITICAL", None, "Lookalike domain detected"),
        ],
    )
    result = run(bundle)
    assert result.risk_level in ("CRITICAL", "HIGH"), (
        f"Expected CRITICAL or HIGH, got {result.risk_level} (score={result.total_score})"
    )
    assert result.total_score >= 60
    assert result.explanation


# ─────────────────────────────────────────────────────────────────────────────
# T2: Moderate identity + limited evidence → MEDIUM
# ─────────────────────────────────────────────────────────────────────────────

def test_moderate_identity_limited_evidence_is_medium():
    """
    Scenario: Typosquatting account with moderate similarity
      - Username moderately similar (typosquat with double k)
      - Bio mentions the bank name + "unofficial updates"
      - Account is a few months old
      - No domain risk, no claims of being official
    Expected: MEDIUM (40–59)
    """
    bundle = _make_bundle(
        candidate_username="nova_bankk",           # typosquat: double k
        candidate_display_name="Nova Bankk Updates",
        candidate_bio="NovaBank unofficial updates and news. Support information for customers.",
        candidate_website="https://banking-updates.info",
        account_age_days=45,
        follower_count=230,
        following_count=180,
        evidence_items=[
            EvidenceItem("USERNAME_SIMILARITY", "MEDIUM", 0.55, "Moderate username resemblance"),
        ],
    )
    result = run(bundle)
    assert result.risk_level == "MEDIUM", (
        f"Expected MEDIUM, got {result.risk_level} (score={result.total_score})"
    )
    assert 40 <= result.total_score <= 59


# ─────────────────────────────────────────────────────────────────────────────
# T3: Fan/aggregator account → LOW
# ─────────────────────────────────────────────────────────────────────────────

def test_fan_account_is_low():
    """
    Scenario: Fan account — brand name appears but context is benign
      - Username unrelated to brand
      - Bio: "NovaBank news fan" — mentions brand but no suspicious claims
      - Old, established account
      - No suspicious domain
    Expected: LOW (<40)
    """
    bundle = _make_bundle(
        candidate_username="bank_news_daily",
        candidate_display_name="Banking News Daily",
        candidate_bio="Sharing news about banks including NovaBank. Not affiliated.",
        candidate_website="https://bankingdaily.net",
        account_age_days=730,
        follower_count=5400,
        following_count=310,
        is_verified=False,
        evidence_items=[],
    )
    result = run(bundle)
    assert result.risk_level == "LOW", (
        f"Expected LOW, got {result.risk_level} (score={result.total_score})"
    )
    assert result.total_score < 40


# ─────────────────────────────────────────────────────────────────────────────
# T4: Mobile app — brand name + unrelated developer → HIGH or CRITICAL
# ─────────────────────────────────────────────────────────────────────────────

def test_fake_mobile_app_is_high_or_critical():
    """
    Scenario: Fake bank app on Play Store
      - App name closely matches brand name
      - Package name contains brand name
      - Developer is completely different from official
      - Very new app, low installs
      - Suspicious TLD on developer website
      - Multiple HIGH/CRITICAL evidence items
    Expected: HIGH or CRITICAL
    """
    bundle = _make_bundle(
        candidate_type="MOBILE_APP",
        candidate_name="NovaBank Mobile Banking",
        candidate_display_name="NovaBank Mobile Banking",
        candidate_bio="Official NovaBank mobile app. Easy banking for all customers.",
        package_name="com.novanet.mobilebanking.fake",
        developer_name="MobileApps LLC",
        developer_email="dev@freemail.xyz",
        candidate_website="https://novabank-app.tk",
        account_age_days=8,
        install_count=150,
        app_version="1.0.0",
        evidence_items=[
            EvidenceItem("NAME_SIMILARITY", "CRITICAL", 0.92, "App name nearly identical to brand"),
            EvidenceItem("DEVELOPER_MISMATCH", "CRITICAL", None, "Developer not affiliated with brand"),
            EvidenceItem("LOGO_SIMILARITY", "HIGH", 0.85, "Icon visually similar to brand logo"),
        ],
    )
    result = run(bundle)
    assert result.risk_level in ("HIGH", "CRITICAL"), (
        f"Expected HIGH or CRITICAL, got {result.risk_level} (score={result.total_score})"
    )
    assert result.total_score >= 60


# ─────────────────────────────────────────────────────────────────────────────
# T5: Insufficient data → no artificial inflation
# ─────────────────────────────────────────────────────────────────────────────

def test_insufficient_data_no_artificial_risk():
    """
    Scenario: Candidate with almost no data fields populated.
    The engine must NOT inflate the score when data is missing.
    Expected: LOW (<40)
    """
    bundle = _make_bundle(
        candidate_username="random_user_xyz_9823",
        candidate_display_name="Random User",
        candidate_bio=None,
        candidate_website=None,
        evidence_items=[],
    )
    result = run(bundle)
    assert result.risk_level == "LOW", (
        f"Insufficient-data candidate should be LOW, got {result.risk_level} "
        f"(score={result.total_score})"
    )
    assert result.total_score < 40


# ─────────────────────────────────────────────────────────────────────────────
# T6: Determinism — same input → same output
# ─────────────────────────────────────────────────────────────────────────────

def test_engine_is_deterministic():
    """Running the same bundle twice must produce identical results."""
    bundle = _make_bundle(
        candidate_username="NovaBankHelp",
        candidate_bio="Official support account for NovaBank customers.",
        candidate_website="https://novabank-help.com",
        account_age_days=20,
        follower_count=300,
        following_count=5,
        evidence_items=[
            EvidenceItem("USERNAME_SIMILARITY", "HIGH", 0.75, "High username match"),
        ],
    )
    result1 = run(bundle)
    result2 = run(bundle)

    assert result1.total_score == result2.total_score
    assert result1.risk_level == result2.risk_level
    assert result1.confidence == result2.confidence
    assert result1.explanation == result2.explanation


# ─────────────────────────────────────────────────────────────────────────────
# T8: Confidence ≠ risk score
# ─────────────────────────────────────────────────────────────────────────────

def test_confidence_is_independent_of_risk_score():
    """
    Confidence and risk score are different values with different meanings.
    A high-risk candidate with little evidence should have LOW confidence.
    """
    # High risk score only from one very strong signal, no evidence
    bundle_high_risk_low_evidence = _make_bundle(
        candidate_username="novabankofficial",   # exact match to official handle
        candidate_bio="Official NovaBank support",
        account_age_days=3,
        evidence_items=[],   # NO evidence records
    )
    result = run(bundle_high_risk_low_evidence)

    # Score should be elevated
    assert result.total_score > 40

    # Confidence should be moderate/low (no evidence records to back it up)
    # Specifically: confidence must NOT simply equal total_score/100
    assert result.confidence != (result.total_score / 100), (
        "Confidence must not be a simple normalization of the risk score"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Individual signal unit tests
# ─────────────────────────────────────────────────────────────────────────────

def test_identity_similarity_exact_match():
    sig = identity_similarity.calculate(
        brand_name="NovaBank",
        brand_official_handles=["novabankofficial"],
        candidate_username="novabankofficial",
        candidate_display_name="NovaBank Official",
        candidate_name=None,
    )
    assert sig.raw_score >= 0.90
    assert sig.weighted_score == pytest.approx(sig.raw_score * 25, abs=0.01)


def test_identity_similarity_impersonation_affix():
    sig = identity_similarity.calculate(
        brand_name="NovaBank",
        brand_official_handles=["novabankofficial"],
        candidate_username="novabanksupport",
        candidate_display_name=None,
        candidate_name=None,
    )
    # Should detect "support" affix
    assert sig.raw_score >= 0.70
    assert "support" in sig.reason.lower() or "similar" in sig.reason.lower()


def test_identity_similarity_unrelated_name():
    sig = identity_similarity.calculate(
        brand_name="NovaBank",
        brand_official_handles=["novabankofficial"],
        candidate_username="sunrise_bakery_shop",
        candidate_display_name="Sunrise Bakery",
        candidate_name=None,
    )
    assert sig.raw_score < 0.30


def test_visual_no_data_returns_zero():
    sig = visual_similarity.calculate(
        brand_logo_hash=None,
        candidate_icon_hash=None,
        evidence_visual_scores=[],
    )
    assert sig.raw_score == 0.0
    assert "No visual evidence" in sig.reason


def test_visual_hash_identical():
    same_hash = "f8c8c8c8c8c8c8c8"
    sig = visual_similarity.calculate(
        brand_logo_hash=same_hash,
        candidate_icon_hash=same_hash,
        evidence_visual_scores=[],
    )
    assert sig.raw_score >= 0.95


def test_visual_evidence_scores_used():
    sig = visual_similarity.calculate(
        brand_logo_hash=None,
        candidate_icon_hash=None,
        evidence_visual_scores=[0.88, 0.90],
    )
    assert sig.raw_score >= 0.75


def test_content_similarity_suspicious_claims():
    sig = content_similarity.calculate(
        brand_name="NovaBank",
        brand_description="Leading digital bank",
        candidate_bio="Official NovaBank customer support. DM for help. Verified account.",
        candidate_name=None,
    )
    assert sig.raw_score >= 0.40
    assert any(term in sig.reason.lower() for term in ("official", "support", "verified"))


def test_content_similarity_unrelated():
    sig = content_similarity.calculate(
        brand_name="NovaBank",
        brand_description="Leading digital bank serving customers",
        candidate_bio="I love cooking pasta and pizza recipes.",
        candidate_name=None,
    )
    assert sig.raw_score < 0.20


def test_link_risk_lookalike_domain():
    sig = link_risk.calculate(
        brand_name="NovaBank",
        official_domain="novabank.com",
        official_developer_name=None,
        official_email_domain="novabank.com",
        candidate_website="https://novabank-secure.com",
        candidate_email=None,
        candidate_package_name=None,
        candidate_developer_name=None,
        candidate_developer_email=None,
    )
    assert sig.raw_score >= 0.80
    assert "lookalike" in sig.reason.lower()


def test_link_risk_official_domain_no_risk():
    sig = link_risk.calculate(
        brand_name="NovaBank",
        official_domain="novabank.com",
        official_developer_name=None,
        official_email_domain="novabank.com",
        candidate_website="https://novabank.com/support",
        candidate_email=None,
        candidate_package_name=None,
        candidate_developer_name=None,
        candidate_developer_email=None,
    )
    assert sig.raw_score == 0.0


def test_link_risk_no_data_returns_zero():
    sig = link_risk.calculate(
        brand_name="NovaBank",
        official_domain="novabank.com",
        official_developer_name=None,
        official_email_domain=None,
        candidate_website=None,
        candidate_email=None,
        candidate_package_name=None,
        candidate_developer_name=None,
        candidate_developer_email=None,
    )
    assert sig.raw_score == 0.0


def test_account_anomaly_new_account():
    sig = account_anomaly.calculate(
        candidate_type="SOCIAL_PROFILE",
        account_age_days=5,
        follower_count=50,
        following_count=2,
        is_verified=False,
        bio_description="Official NovaBank support",
        display_name=None,
        developer_name=None,
        official_developer_name=None,
        install_count=None,
        app_version=None,
        claims_to_be_official=True,
    )
    assert sig.raw_score >= 0.50


def test_account_anomaly_established_account():
    sig = account_anomaly.calculate(
        candidate_type="SOCIAL_PROFILE",
        account_age_days=1200,
        follower_count=50000,
        following_count=500,
        is_verified=True,
        bio_description="Finance news aggregator",
        display_name=None,
        developer_name=None,
        official_developer_name=None,
        install_count=None,
        app_version=None,
        claims_to_be_official=False,
    )
    assert sig.raw_score < 0.30


def test_evidence_score_empty():
    sig = evidence_score.calculate(evidence_items=[])
    assert sig.raw_score == 0.0
    assert "No evidence" in sig.reason


def test_evidence_score_critical_items():
    items = [
        EvidenceItem("USERNAME_SIMILARITY", "CRITICAL", 0.95, "Exact match"),
        EvidenceItem("DOMAIN_RISK", "CRITICAL", None, "Lookalike domain"),
        EvidenceItem("LOGO_SIMILARITY", "HIGH", 0.88, "Logo copied"),
    ]
    sig = evidence_score.calculate(evidence_items=items)
    assert sig.raw_score >= 0.70


def test_activity_anomaly_no_data():
    sig = activity_anomaly.calculate(
        candidate_type="SOCIAL_PROFILE",
        account_age_days=None,
        follower_count=None,
        following_count=None,
        install_count=None,
        bio_description=None,
    )
    assert sig.raw_score == 0.0
    assert "Insufficient" in sig.reason


def test_activity_anomaly_urgency_language():
    sig = activity_anomaly.calculate(
        candidate_type="SOCIAL_PROFILE",
        account_age_days=10,
        follower_count=100,
        following_count=1000,
        install_count=None,
        bio_description="Act now! Limited time offer. DM us immediately to claim your prize!",
    )
    assert sig.raw_score >= 0.30


def test_risk_thresholds():
    assert classify_risk(85) == "CRITICAL"
    assert classify_risk(80) == "CRITICAL"
    assert classify_risk(79) == "HIGH"
    assert classify_risk(60) == "HIGH"
    assert classify_risk(59) == "MEDIUM"
    assert classify_risk(40) == "MEDIUM"
    assert classify_risk(39) == "LOW"
    assert classify_risk(0)  == "LOW"


def test_all_detection_modules_import():
    """Verify all seven signal modules can be imported without error."""
    from app.services.detection import (
        identity_similarity,
        visual_similarity,
        content_similarity,
        link_risk,
        account_anomaly,
        evidence_score,
        activity_anomaly,
    )
    from app.services.detection.risk_engine import run, CandidateBundle
    from app.services.detection.contracts import DetectionResult, SignalResult
    assert True  # if we got here, all imports succeeded
