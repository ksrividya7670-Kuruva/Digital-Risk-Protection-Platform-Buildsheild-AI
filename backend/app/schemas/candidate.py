"""
Candidate Pydantic schemas for the BrandShield AI API.

CandidateListItem — lightweight row used in paginated list responses.
CandidateDetail   — full investigation-ready representation.
EvidenceItem      — individual piece of traceable evidence.
SignalItem        — reconstructed signal breakdown for the detail view.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, computed_field, model_validator


class EvidenceItem(BaseModel):
    """A single traceable evidence record attached to a candidate."""

    model_config = {"from_attributes": True}

    id: str
    evidence_type: str
    severity: str
    title: str
    description: Optional[str] = None
    evidence_value: Optional[str] = None
    similarity_score: Optional[float] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    is_synthetic: bool
    collected_at: Optional[datetime] = None


class SignalItem(BaseModel):
    """
    A reconstructed scoring signal.

    weighted_score is the contribution to the 0-100 total score.
    raw_score is the normalised 0.0-1.0 signal strength before weighting.
    """

    model_config = {"from_attributes": True}

    signal_name: str
    raw_score: float
    weight: int
    weighted_score: float
    reason: str


class CandidateListItem(BaseModel):
    """Lightweight candidate representation for paginated list endpoints."""

    model_config = {"from_attributes": True}

    id: str
    brand_id: str
    candidate_type: str
    platform: str
    name: Optional[str] = None
    username: Optional[str] = None
    risk_score: Optional[int] = None
    risk_level: Optional[str] = None
    confidence: Optional[float] = None
    status: str
    data_source: str
    # discovered_at is populated from Candidate.created_at by the route handler
    discovered_at: Optional[datetime] = None


class CandidateDetail(BaseModel):
    """
    Complete investigation-ready candidate response.

    Powers the Threat Detail screen. Includes profile metadata,
    current risk assessment, signal breakdown, and evidence.
    """

    model_config = {"from_attributes": True}

    # Identity
    id: str
    brand_id: str
    brand_name: Optional[str] = None
    candidate_type: str
    platform: str
    name: Optional[str] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    profile_url: Optional[str] = None

    # Profile/app metadata
    bio_description: Optional[str] = None
    website_url: Optional[str] = None
    contact_email: Optional[str] = None
    icon_url: Optional[str] = None

    # Social-specific
    follower_count: Optional[int] = None
    following_count: Optional[int] = None
    account_age_days: Optional[int] = None
    is_verified: Optional[bool] = None

    # App-specific
    package_name: Optional[str] = None
    developer_name: Optional[str] = None
    developer_email: Optional[str] = None
    app_version: Optional[str] = None
    install_count: Optional[int] = None
    app_rating: Optional[str] = None

    # Status
    status: str
    data_source: str
    discovered_at: Optional[datetime] = None

    # Risk assessment
    risk_score: Optional[int] = None
    risk_level: Optional[str] = None
    confidence: Optional[float] = None
    detection_summary: Optional[str] = None
    ai_explanation: Optional[str] = None

    # Breakdown
    signals: List[SignalItem] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
