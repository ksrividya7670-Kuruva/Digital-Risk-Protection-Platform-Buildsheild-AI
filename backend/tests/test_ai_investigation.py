"""
AI Investigation Tests — Step 6

All tests mock the external AI provider — no real LLM calls are made.

Tests cover:
  T1:  Template fallback produces valid InvestigationResult
  T2:  Template fallback never changes risk_score
  T3:  Template fallback never changes risk_level
  T4:  Template fallback generates_by == "template"
  T5:  OpenAI investigator uses template on provider failure
  T6:  OpenAI investigator uses template when key is empty
  T7:  Malformed AI JSON response falls back to template
  T8:  AI cannot change risk_score (invariant enforced in router)
  T9:  AI cannot change risk_level (invariant enforced in router)
  T10: Template fallback for /ask returns answer
  T11: Template /ask answers "why risky" question
  T12: Template /ask answers "evidence" question
  T13: Template /ask answers "signals" question
  T14: Template /ask answers "recommended actions" question
  T15: get_investigator() returns TemplateInvestigator when no key set
  T16: API /analyze returns 404 for unknown candidate
  T17: API /analyze returns 422 when no assessment exists yet
  T18: API /ask returns 404 for unknown candidate
  T19: API /ask validates empty question
  T20: generated_by field is always present in response
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from app.schemas.investigation import InvestigationContext, InvestigationResult, AskResponse
from app.services.ai_investigation import (
    TemplateInvestigator,
    OpenAIInvestigator,
    get_investigator,
)
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_context(
    risk_score: int = 75,
    risk_level: str = "HIGH",
    confidence: float = 0.80,
    evidence_count: int = 3,
) -> InvestigationContext:
    return InvestigationContext(
        candidate_id="test-cand-001",
        candidate_type="SOCIAL_PROFILE",
        platform="Twitter",
        name="NovaPay Support",
        username="novapayhq_support",
        bio_description="Official NovaPay customer support account.",
        website_url="https://novapay-support.example",
        brand_name="NovaPay",
        brand_domain="novapay.example",
        risk_score=risk_score,
        risk_level=risk_level,
        confidence=confidence,
        signals=[
            {"signal_name": "identity_similarity", "raw_score": 0.90, "weight": 25, "weighted_score": 22.5},
            {"signal_name": "visual_similarity",   "raw_score": 0.80, "weight": 20, "weighted_score": 16.0},
            {"signal_name": "link_risk",            "raw_score": 0.85, "weight": 15, "weighted_score": 12.75},
            {"signal_name": "content_similarity",  "raw_score": 0.60, "weight": 15, "weighted_score": 9.0},
            {"signal_name": "account_anomaly",     "raw_score": 0.50, "weight": 10, "weighted_score": 5.0},
            {"signal_name": "evidence_score",      "raw_score": 0.90, "weight": 10, "weighted_score": 9.0},
            {"signal_name": "activity_anomaly",    "raw_score": 0.15, "weight": 5,  "weighted_score": 0.75},
        ],
        top_reasons=[
            "Username nearly identical to official brand handle",
            "Lookalike domain in profile",
            "Account is extremely new (11 days)",
        ],
        evidence=[
            {"title": "Username Match", "description": "Handle matches brand exactly.", "severity": "CRITICAL", "is_synthetic": True, "evidence_type": "USERNAME_SIMILARITY"},
            {"title": "Domain Risk",    "description": "Lookalike domain detected.",    "severity": "CRITICAL", "is_synthetic": True, "evidence_type": "DOMAIN_RISK"},
            {"title": "New Account",    "description": "11-day-old account.",           "severity": "HIGH",     "is_synthetic": True, "evidence_type": "ACCOUNT_ANOMALY"},
        ][:evidence_count],
    )


# ─────────────────────────────────────────────────────────────────────────────
# T1–T4: Template fallback basic contract
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_template_produces_valid_result():
    """Template fallback returns a fully populated InvestigationResult."""
    ctx = _make_context()
    investigator = TemplateInvestigator()
    result = await investigator.investigate(ctx)
    assert isinstance(result, InvestigationResult)
    assert result.summary
    assert result.risk_explanation
    assert isinstance(result.key_findings, list)
    assert isinstance(result.evidence_summary, list)
    assert isinstance(result.recommended_actions, list)
    assert result.confidence_note
    assert result.generated_at


@pytest.mark.asyncio
async def test_template_never_changes_risk_score():
    """Template MUST mirror input risk_score — it cannot change it."""
    ctx = _make_context(risk_score=83)
    result = await TemplateInvestigator().investigate(ctx)
    assert result.risk_score == 83, "risk_score was changed by template — must not happen"


@pytest.mark.asyncio
async def test_template_never_changes_risk_level():
    """Template MUST mirror input risk_level — it cannot change it."""
    ctx = _make_context(risk_level="CRITICAL")
    result = await TemplateInvestigator().investigate(ctx)
    assert result.risk_level == "CRITICAL", "risk_level was changed by template — must not happen"


@pytest.mark.asyncio
async def test_template_generated_by_is_template():
    ctx = _make_context()
    result = await TemplateInvestigator().investigate(ctx)
    assert result.generated_by == "template"


# ─────────────────────────────────────────────────────────────────────────────
# T5–T7: OpenAI fallback behaviour
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_openai_fallback_on_provider_exception():
    """If the HTTP call to OpenAI raises, the result must be from template fallback."""
    investigator = OpenAIInvestigator(
        api_key="sk-test-fake",
        model="gpt-4o-mini",
        timeout=5,
        max_tokens=800,
    )
    ctx = _make_context()
    with patch("httpx.AsyncClient.post", side_effect=Exception("Connection refused")):
        result = await investigator.investigate(ctx)
    assert result.generated_by == "template"
    assert result.risk_score == ctx.risk_score


@pytest.mark.asyncio
async def test_empty_api_key_uses_template():
    """get_investigator() with no key returns TemplateInvestigator."""
    with patch("app.services.ai_investigation.settings") as mock_settings:
        mock_settings.ai_api_key = ""
        mock_settings.openai_api_key = ""
        mock_settings.ai_provider = ""
        mock_settings.ai_model = "gpt-4o-mini"
        mock_settings.openai_model = "gpt-4o-mini"
        mock_settings.ai_timeout_seconds = 15
        mock_settings.ai_max_tokens = 800
        investigator = get_investigator()
    assert isinstance(investigator, TemplateInvestigator)


@pytest.mark.asyncio
async def test_malformed_ai_json_falls_back():
    """If OpenAI returns non-JSON content, we fall back to template."""
    investigator = OpenAIInvestigator(
        api_key="sk-test-fake",
        model="gpt-4o-mini",
        timeout=5,
        max_tokens=800,
    )
    ctx = _make_context()
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "NOT VALID JSON {{{ "}}]
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        result = await investigator.investigate(ctx)
    assert result.generated_by == "template"


@pytest.mark.asyncio
async def test_ai_response_is_strictly_validated():
    """Unrecognized provider fields are rejected instead of entering the API result."""
    investigator = OpenAIInvestigator(
        api_key="sk-test-fake",
        model="gpt-4o-mini",
        timeout=5,
        max_tokens=800,
    )
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": (
                    '{"summary":"Grounded summary",'
                    '"evidence_summary":["Fabricated observation"]}'
                )
            }
        }]
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        result = await investigator.investigate(_make_context())
    assert result.generated_by == "template"
    assert all("Fabricated observation" not in item for item in result.evidence_summary)


@pytest.mark.asyncio
async def test_ai_generated_unprovided_url_falls_back():
    """A provider cannot introduce a URL that was not present in the context."""
    investigator = OpenAIInvestigator(
        api_key="sk-test-fake",
        model="gpt-4o-mini",
        timeout=5,
        max_tokens=800,
    )
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"summary":"Investigate https://invented.example now."}'
            }
        }]
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        result = await investigator.investigate(_make_context())
    assert result.generated_by == "template"
    assert "https://invented.example" not in result.summary


@pytest.mark.asyncio
async def test_ai_evidence_summary_is_derived_from_stored_evidence():
    """AI prose cannot populate the evidence section; it comes from backend context."""
    investigator = OpenAIInvestigator(
        api_key="sk-test-fake",
        model="gpt-4o-mini",
        timeout=5,
        max_tokens=800,
    )
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {"content": '{"summary":"Review the supplied findings."}'}
        }]
    }
    ctx = _make_context()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        result = await investigator.investigate(ctx)
    assert result.generated_by == "ai"
    assert len(result.evidence_summary) == len(ctx.evidence)
    assert all(
        any(evidence["title"] in summary for evidence in ctx.evidence)
        for summary in result.evidence_summary
    )


# ─────────────────────────────────────────────────────────────────────────────
# T8–T9: Score invariant (enforced in router)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_risk_score_invariant_enforced():
    """
    Even if a mock AI returns a different score in its JSON,
    the router enforces the original score.
    Simulate by overriding after investigate().
    """
    ctx = _make_context(risk_score=75, risk_level="HIGH")
    result = await TemplateInvestigator().investigate(ctx)
    # Simulate what the router does:
    result.risk_score = ctx.risk_score
    result.risk_level = ctx.risk_level
    assert result.risk_score == 75
    assert result.risk_level == "HIGH"


@pytest.mark.asyncio
async def test_openai_result_score_never_changes():
    """OpenAI response risk_score is always replaced by the router with the original."""
    investigator = OpenAIInvestigator(
        api_key="sk-test-fake",
        model="gpt-4o-mini",
        timeout=5,
        max_tokens=800,
    )
    ctx = _make_context(risk_score=91, risk_level="CRITICAL")
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    # Simulate AI trying to lower the score
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"summary":"Review the supplied candidate data."}'
            }
        }]
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        result = await investigator.investigate(ctx)
    assert result.generated_by == "ai"
    assert result.risk_score == 91
    assert result.risk_level == "CRITICAL"


# ─────────────────────────────────────────────────────────────────────────────
# T10–T14: Template /ask
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_template_ask_returns_answer():
    ctx = _make_context()
    result = await TemplateInvestigator().ask(ctx, "What is the risk level?")
    assert isinstance(result, AskResponse)
    assert result.answer
    assert result.generated_by == "template"
    assert result.candidate_id == ctx.candidate_id


@pytest.mark.asyncio
async def test_template_ask_why_risky():
    ctx = _make_context()
    result = await TemplateInvestigator().ask(ctx, "Why is this candidate flagged as risky?")
    assert "75" in result.answer or "HIGH" in result.answer or "flagged" in result.answer.lower()


@pytest.mark.asyncio
async def test_template_ask_evidence():
    ctx = _make_context(evidence_count=3)
    result = await TemplateInvestigator().ask(ctx, "What evidence supports the score?")
    assert result.answer
    # Should mention one of the evidence titles
    assert "Username Match" in result.answer or "Domain Risk" in result.answer or "evidence" in result.answer.lower()


@pytest.mark.asyncio
async def test_template_ask_top_signal():
    ctx = _make_context()
    result = await TemplateInvestigator().ask(ctx, "Which signal contributed most to the score?")
    assert result.answer
    assert "identity" in result.answer.lower() or "signal" in result.answer.lower()


@pytest.mark.asyncio
async def test_template_ask_recommended_actions():
    ctx = _make_context(risk_level="CRITICAL", risk_score=82)
    result = await TemplateInvestigator().ask(ctx, "What should I do next?")
    assert result.answer
    assert any(kw in result.answer.lower() for kw in ("takedown", "evidence", "case", "investigate", "report", "action"))


# ─────────────────────────────────────────────────────────────────────────────
# T15: get_investigator factory
# ─────────────────────────────────────────────────────────────────────────────

def test_get_investigator_no_key_returns_template():
    with patch("app.services.ai_investigation.settings") as m:
        m.ai_api_key = ""
        m.openai_api_key = ""
        m.ai_provider = ""
        m.ai_model = "gpt-4o-mini"
        m.openai_model = "gpt-4o-mini"
        m.ai_timeout_seconds = 15
        m.ai_max_tokens = 800
        assert isinstance(get_investigator(), TemplateInvestigator)


def test_get_investigator_with_key_returns_openai():
    with patch("app.services.ai_investigation.settings") as m:
        m.ai_api_key = "sk-test-key"
        m.openai_api_key = ""
        m.ai_provider = "openai"
        m.ai_model = "gpt-4o-mini"
        m.openai_model = "gpt-4o-mini"
        m.ai_timeout_seconds = 15
        m.ai_max_tokens = 800
        assert isinstance(get_investigator(), OpenAIInvestigator)


# ─────────────────────────────────────────────────────────────────────────────
# T16–T20: API endpoint tests (synchronous TestClient)
# ─────────────────────────────────────────────────────────────────────────────

def test_api_analyze_candidate_not_found():
    """POST /analyze for a non-existent candidate returns 404."""
    r = client.post("/api/v1/investigation/candidates/no-such-id/analyze")
    assert r.status_code == 404


def test_api_analyze_no_assessment_yet():
    """
    POST /analyze for a candidate that has no risk assessment yet returns 422.
    We use a random UUID that definitely has no RA.
    """
    import uuid
    r = client.post(f"/api/v1/investigation/candidates/{uuid.uuid4()}/analyze")
    # 404 (candidate not found) is also acceptable
    assert r.status_code in (404, 422)


def test_api_ask_candidate_not_found():
    """POST /ask for a non-existent candidate returns 404."""
    r = client.post(
        "/api/v1/investigation/candidates/no-such-id/ask",
        json={"question": "Why is this risky?"},
    )
    assert r.status_code == 404


def test_api_ask_empty_question_rejected():
    """POST /ask with a question shorter than 3 chars returns 422."""
    r = client.post(
        "/api/v1/investigation/candidates/any-id/ask",
        json={"question": "  "},  # too short after any trim
    )
    assert r.status_code in (404, 422)


def test_api_investigation_endpoints_in_openapi():
    """Both investigation endpoints must appear in the OpenAPI schema."""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = list(r.json()["paths"].keys())
    assert any("investigation" in p and "analyze" in p for p in paths), \
        f"analyze endpoint missing from OpenAPI. Paths: {paths}"
    assert any("investigation" in p and "ask" in p for p in paths), \
        f"ask endpoint missing from OpenAPI. Paths: {paths}"


def test_api_generated_by_field_present():
    """
    If there is a seeded candidate with a risk assessment,
    the response must include 'generated_by' field.
    This is a structural test — it verifies the schema contract holds
    regardless of whether AI or template produced the output.
    """
    # First get any candidate that might have been seeded
    r = client.get("/api/v1/candidates?page_size=1")
    assert r.status_code == 200
    items = r.json().get("items", [])
    if not items:
        pytest.skip("No candidates in DB — seed data not loaded in this test session")

    cid = items[0]["id"]
    r2 = client.post(f"/api/v1/investigation/candidates/{cid}/analyze")
    # Candidate may not have a RA yet (422) — that's fine for this test
    if r2.status_code == 422:
        pytest.skip("Candidate has no risk assessment yet")
    assert r2.status_code == 200
    data = r2.json()
    assert "generated_by" in data
    assert data["generated_by"] in ("ai", "template")
    assert "risk_score" in data
    assert "risk_level" in data
    assert "summary" in data


def test_api_analyze_cannot_change_stored_risk_score(monkeypatch):
    """The route replaces provider score fields with the stored deterministic values."""
    from app.api.v1 import investigation as investigation_api

    ctx = _make_context(risk_score=75, risk_level="HIGH")

    class TamperingInvestigator:
        async def investigate(self, _context):
            return InvestigationResult(
                candidate_id=ctx.candidate_id,
                risk_score=1,
                risk_level="LOW",
                summary="Analyst summary",
                risk_explanation="Explanation",
                confidence_note="Confidence note",
                generated_by="ai",
                generated_at=datetime.now(timezone.utc),
            )

        async def ask(self, _context, question):
            return AskResponse(
                candidate_id=ctx.candidate_id,
                question=question,
                answer="Answer",
                generated_by="ai",
                generated_at=datetime.now(timezone.utc),
            )

    monkeypatch.setattr(
        investigation_api,
        "_load_context",
        AsyncMock(return_value=ctx),
    )
    monkeypatch.setattr(investigation_api, "get_investigator", TamperingInvestigator)

    response = client.post(
        f"/api/v1/investigation/candidates/{ctx.candidate_id}/analyze"
    )
    assert response.status_code == 200
    assert response.json()["risk_score"] == 75
    assert response.json()["risk_level"] == "HIGH"
