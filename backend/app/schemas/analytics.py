"""
Analytics Pydantic schemas for the BrandShield AI API.

ThreatSummaryResponse — KPI counts powering the threat queue header.
AnalyticsOverview     — dashboard analytics overview.
ThreatTrend           — single date-bucket for the discovery trend chart.
"""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel


class ThreatSummaryResponse(BaseModel):
    """
    Aggregated threat statistics for the threat queue header.

    All values are derived from the live database — nothing is hardcoded.
    """

    model_config = {"from_attributes": True}

    total: int
    critical: int
    high: int
    medium: int
    low: int
    social_threats: int
    app_threats: int
    avg_score: float
    max_score: int
    open_cases: int


class AnalyticsOverview(BaseModel):
    """
    Dashboard analytics overview.

    Provides all data needed to populate KPI cards, pie charts,
    and platform/type breakdowns without additional API calls.
    """

    model_config = {"from_attributes": True}

    total_candidates: int
    social_candidates: int
    app_candidates: int
    critical: int
    high: int
    medium: int
    low: int
    avg_score: float
    max_score: int
    open_cases: int
    by_platform: Dict[str, int]
    by_type: Dict[str, int]


class ThreatTrend(BaseModel):
    """A single date bucket in the threat discovery trend chart."""

    model_config = {"from_attributes": True}

    date: str   # ISO date string, e.g. "2025-01-15"
    count: int
