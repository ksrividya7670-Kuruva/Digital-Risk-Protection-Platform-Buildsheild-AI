"""
Pydantic schemas for the detection API.
These are the request/response shapes — not ORM models.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class SignalResultSchema(BaseModel):
    signal_name: str
    raw_score: float = Field(ge=0.0, le=1.0)
    weight: int
    weighted_score: float
    reason: str
    metadata: dict[str, Any] = {}


class DetectionResultSchema(BaseModel):
    candidate_id: str
    brand_id: str
    total_score: int = Field(ge=0, le=100)
    risk_level: str
    confidence: float = Field(ge=0.0, le=1.0)
    signals: list[SignalResultSchema]
    reasons: list[str]
    explanation: str
    # Component scores
    identity_similarity_score: float
    visual_similarity_score: float
    content_similarity_score: float
    link_contact_score: float
    anomaly_score: float
    evidence_score_val: float
    activity_score: float


class RiskAssessmentSchema(BaseModel):
    """Response schema for a persisted RiskAssessment record."""
    id: str
    candidate_id: str
    total_score: int
    risk_level: str
    confidence: Optional[float]
    identity_similarity_score: Optional[float]
    visual_similarity_score: Optional[float]
    content_similarity_score: Optional[float]
    link_contact_score: Optional[float]
    anomaly_score: Optional[float]
    evidence_score: Optional[float]
    activity_score: Optional[float]
    detection_summary: Optional[str]
    ai_explanation: Optional[str]
    calculated_at: datetime

    model_config = {"from_attributes": True}
