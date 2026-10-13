"""
Candidate model.

A Candidate is any external entity being monitored for potential
brand impersonation. It is deliberately unified to cover both:

  - SOCIAL_PROFILE : A social media account (Twitter, Instagram, etc.)
  - MOBILE_APP     : An application in an app store (Play Store, App Store, etc.)

Using one table keeps the detection engine, threat queue, and case management
simple — they all work against a single entity type.

Fields that are only relevant to one candidate_type are nullable.
"""

import enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.brand import Brand
    from app.models.evidence import Evidence
    from app.models.risk_assessment import RiskAssessment
    from app.models.case import Case


class CandidateType(str, enum.Enum):
    SOCIAL_PROFILE = "SOCIAL_PROFILE"
    MOBILE_APP = "MOBILE_APP"


class CandidateStatus(str, enum.Enum):
    NEW = "NEW"                         # Just discovered, not yet reviewed
    REVIEWING = "REVIEWING"             # Analyst is actively reviewing
    CONFIRMED_THREAT = "CONFIRMED_THREAT"  # Confirmed as impersonation
    BENIGN = "BENIGN"                   # Reviewed and determined to be safe
    FALSE_POSITIVE = "FALSE_POSITIVE"   # System flagged incorrectly


class DataSource(str, enum.Enum):
    MOCK = "MOCK"       # Synthetic demo data — always labelled
    LIVE = "LIVE"       # Retrieved from a real external API
    MANUAL = "MANUAL"   # Manually entered by an analyst


class Candidate(UUIDPrimaryKey, TimestampMixin, Base):
    """
    Represents a single external entity to be evaluated for brand impersonation.

    One Candidate → one latest RiskAssessment → zero or one Case.
    One Candidate → many Evidence items.
    """

    __tablename__ = "candidates"

    # ── Classification ────────────────────────────────────────
    brand_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_type: Mapped[CandidateType] = mapped_column(
        Enum(CandidateType),
        nullable=False,
        index=True,
        comment="SOCIAL_PROFILE or MOBILE_APP",
    )
    platform: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="e.g. 'Twitter', 'Instagram', 'Google Play', 'App Store'",
    )
    data_source: Mapped[DataSource] = mapped_column(
        Enum(DataSource),
        nullable=False,
        default=DataSource.MOCK,
        comment="MOCK (synthetic demo), LIVE (real API), or MANUAL",
    )

    # ── Identity fields (both types) ──────────────────────────
    name: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
        comment="Display name or app name",
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        index=True,
        comment="Social: @handle. App: package or bundle ID.",
    )
    display_name: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
    )
    profile_url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        comment="Direct URL to the social profile or app store listing",
    )
    bio_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Social: bio text. App: store description.",
    )
    website_url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        comment="Website link in profile or app metadata",
    )
    contact_email: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
    )
    icon_url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        comment="Profile picture URL (social) or app icon URL (app)",
    )
    icon_perceptual_hash: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Pre-computed perceptual hash for visual similarity checks",
    )

    # ── Social-profile-specific fields ────────────────────────
    follower_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Social only: follower/subscriber count",
    )
    following_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    account_age_days: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Days since account/app was created (used in anomaly detection)",
    )
    is_verified: Mapped[Optional[bool]] = mapped_column(
        nullable=True,
        comment="Whether the account has a platform-verified badge",
    )

    # ── Mobile-app-specific fields ────────────────────────────
    package_name: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
        comment="App only: Android package name or iOS bundle ID",
    )
    developer_name: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
        comment="App only: publisher / developer name in the store",
    )
    developer_email: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
    )
    app_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    install_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="App only: approximate install count",
    )
    app_rating: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="App only: store rating (e.g. '3.8')",
    )

    # ── Status ────────────────────────────────────────────────
    status: Mapped[CandidateStatus] = mapped_column(
        Enum(CandidateStatus),
        nullable=False,
        default=CandidateStatus.NEW,
        index=True,
    )

    # ── Relationships ─────────────────────────────────────────
    brand: Mapped["Brand"] = relationship(
        "Brand",
        back_populates="candidates",
        lazy="select",
    )
    evidence_items: Mapped[List["Evidence"]] = relationship(
        "Evidence",
        back_populates="candidate",
        cascade="all, delete-orphan",
        lazy="select",
    )
    risk_assessments: Mapped[List["RiskAssessment"]] = relationship(
        "RiskAssessment",
        back_populates="candidate",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="RiskAssessment.calculated_at.desc()",
    )
    cases: Mapped[List["Case"]] = relationship(
        "Case",
        back_populates="candidate",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<Candidate id={self.id!r} type={self.candidate_type} "
            f"platform={self.platform!r} name={self.name!r}>"
        )
