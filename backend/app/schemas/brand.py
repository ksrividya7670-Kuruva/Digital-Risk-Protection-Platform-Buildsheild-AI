"""
Brand Pydantic schemas for the BrandShield AI API.

BrandResponse     — public representation of a Brand ORM object.
BrandSummaryResponse — aggregated threat counts for a brand's dashboard card.
BrandCreate       — payload for creating a new monitored brand.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class BrandResponse(BaseModel):
    """Full public representation of a monitored brand."""

    model_config = {"from_attributes": True}

    id: str
    name: str
    official_domain: Optional[str] = None
    official_email_domain: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    twitter_handle: Optional[str] = None
    instagram_handle: Optional[str] = None
    facebook_handle: Optional[str] = None
    linkedin_handle: Optional[str] = None
    youtube_handle: Optional[str] = None
    tiktok_handle: Optional[str] = None
    official_android_package: Optional[str] = None
    official_ios_bundle_id: Optional[str] = None
    official_developer_name: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BrandSummaryResponse(BaseModel):
    """Aggregated threat and candidate statistics for one brand.

    All counts are derived from live database queries —
    nothing is hardcoded.
    """

    model_config = {"from_attributes": True}

    brand_id: str
    brand_name: str
    total_candidates: int
    social_candidates: int
    app_candidates: int
    critical_threats: int
    high_threats: int
    medium_threats: int
    low_threats: int
    open_cases: int


class BrandCreate(BaseModel):
    """Payload for creating a new monitored brand."""

    model_config = {"from_attributes": True}

    name: str
    official_domain: Optional[str] = None
    official_email_domain: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    twitter_handle: Optional[str] = None
    instagram_handle: Optional[str] = None
    facebook_handle: Optional[str] = None
    linkedin_handle: Optional[str] = None
    youtube_handle: Optional[str] = None
    tiktok_handle: Optional[str] = None
    official_android_package: Optional[str] = None
    official_ios_bundle_id: Optional[str] = None
    official_developer_name: Optional[str] = None
    logo_url: Optional[str] = None
