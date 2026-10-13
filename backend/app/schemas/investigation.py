"""
AI Investigation Pydantic schemas.

These define the contract between the AI service and the API layer.
All AI output is validated against these schemas before being returned.
The AI can never change numerical risk scores — they are read-only inputs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    field_validator,
)


class InvestigationContext(BaseModel):
    """
    All data passed INTO the AI investigator.
    Assembled from the database — the AI receives this as read-only context.
    """
    # Candidate identity
    candidate_id: str
    candidate_type: str
    platform: str
    name: Optional[str] = None
    username: Optional[str] = None
    data_source: str = "UNKNOWN"
    profile_url: Optional[str] = None
    bio_description: Optional[str] = None
    website_url: Optional[str] = None
    candidate_metadata: dict[str, object] = Field(default_factory=dict)

    # Brand
    brand_name: str
    brand_domain: Optional[str] = None

    # Risk (read-only — AI cannot change these)
    risk_score: int
    risk_level: str
    confidence: float

    # Deterministic signal breakdown
    signals: list[dict] = Field(default_factory=list)
    top_reasons: list[str] = Field(default_factory=list)

    # Stored evidence (already in DB — AI summarises, never invents)
    evidence: list[dict] = Field(default_factory=list)


class AIInvestigationDraft(BaseModel):
    """The AI investigation response including verdicts."""

    model_config = ConfigDict(extra="forbid", strict=True)

    summary: StrictStr = Field(min_length=1, max_length=1200)
    ai_verdict: Literal[
        "AI_VERDICT_FAKE",
        "AI_VERDICT_LIKELY_FAKE", 
        "AI_VERDICT_SUSPICIOUS",
        "AI_VERDICT_LIKELY_LEGITIMATE",
        "AI_VERDICT_LEGITIMATE"
    ]
    ai_verdict_reasoning: StrictStr = Field(min_length=1, max_length=500)
    threat_confidence: StrictInt = Field(ge=1, le=100)


class InvestigationResult(BaseModel):
    """
    Structured output from the AI investigator (or template fallback).

    IMPORTANT CONTRACT:
      - risk_score and risk_level are copied from the INPUT — the AI cannot change them.
      - generated_by tells the client whether real AI or the deterministic fallback was used.
      - All textual fields are based ONLY on the supplied context.
      - AI verdict provides additional threat assessment layer.
    """
    model_config = ConfigDict(extra="forbid", strict=True)

    # Read-only — always mirrored from input
    candidate_id: StrictStr
    risk_score: StrictInt
    risk_level: StrictStr

    # Narrative summary is AI-generated or templated. Other fields are server-derived.
    summary: StrictStr = Field(min_length=1, max_length=1200)
    risk_explanation: StrictStr = Field(min_length=1, max_length=1000)
    key_findings: list[StrictStr] = Field(default_factory=list, max_length=8)
    evidence_summary: list[StrictStr] = Field(default_factory=list, max_length=8)
    recommended_actions: list[StrictStr] = Field(default_factory=list, max_length=8)
    confidence_note: StrictStr = Field(
        min_length=1,
        max_length=500,
        description="Deterministic engine confidence, kept separate from risk_score.",
    )

    # AI Verdict System
    ai_verdict: Optional[Literal[
        "AI_VERDICT_FAKE",
        "AI_VERDICT_LIKELY_FAKE", 
        "AI_VERDICT_SUSPICIOUS",
        "AI_VERDICT_LIKELY_LEGITIMATE",
        "AI_VERDICT_LEGITIMATE"
    ]] = None
    ai_verdict_reasoning: Optional[StrictStr] = Field(default=None, max_length=500)
    threat_confidence: Optional[StrictInt] = Field(default=None, ge=1, le=100)

    # Provenance — always explicit
    generated_by: Literal["ai", "template"]
    generated_at: datetime


class AskRequest(BaseModel):
    """Request body for the /ask endpoint."""
    question: str = Field(
        min_length=3,
        max_length=500,
        description="A question about this candidate/threat for the AI analyst.",
    )

    @field_validator("question", mode="before")
    @classmethod
    def strip_question(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class AskResponse(BaseModel):
    """Response from the /ask endpoint."""
    model_config = ConfigDict(extra="forbid", strict=True)

    candidate_id: StrictStr
    question: StrictStr
    answer: StrictStr = Field(min_length=1, max_length=2000)
    generated_by: Literal["ai", "template"]
    generated_at: datetime
