"""
Brand model.

A Brand represents an organisation whose identity we are protecting.
The brand's official identity is the source of truth for all comparisons
made by the detection engine.
"""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.case import Case


class Brand(UUIDPrimaryKey, TimestampMixin, Base):
    """
    Stores the legitimate identity of a monitored brand.

    Every candidate entity and every risk assessment is evaluated
    against the official data stored here.
    """

    __tablename__ = "brands"

    # ── Core identity ─────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
        comment="Official brand name (e.g. 'NovaBank')",
    )
    official_domain: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Primary official website domain (e.g. 'novabank.com')",
    )
    official_email_domain: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Official email domain (e.g. 'novabank.com')",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Official brand description used for content similarity checks",
    )
    industry: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Industry / sector (e.g. 'Banking', 'Healthcare')",
    )

    # ── Social media handles ──────────────────────────────────
    # Stored as individual columns for query efficiency.
    # The detection engine compares candidate usernames against these.
    twitter_handle: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Official Twitter/X handle without @"
    )
    instagram_handle: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    facebook_handle: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    linkedin_handle: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    youtube_handle: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    tiktok_handle: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )

    # ── Mobile app identifiers ────────────────────────────────
    official_android_package: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
        comment="Official Android package name (e.g. 'com.novabank.app')",
    )
    official_ios_bundle_id: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
        comment="Official iOS bundle ID (e.g. 'com.novabank.ios')",
    )
    official_developer_name: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
        comment="Official app store developer/publisher name",
    )

    # ── Visual identity ───────────────────────────────────────
    logo_url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        comment="URL or local path to the official brand logo",
    )
    logo_perceptual_hash: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Pre-computed perceptual hash of the logo for similarity comparison",
    )

    # ── Monitoring state ──────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Set to False to pause monitoring for this brand",
    )

    # ── Relationships ─────────────────────────────────────────
    candidates: Mapped[List["Candidate"]] = relationship(
        "Candidate",
        back_populates="brand",
        cascade="all, delete-orphan",
        lazy="select",
    )
    cases: Mapped[List["Case"]] = relationship(
        "Case",
        back_populates="brand",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Brand id={self.id!r} name={self.name!r}>"
