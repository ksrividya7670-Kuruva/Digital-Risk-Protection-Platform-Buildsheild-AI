"""
Evidence model.

Evidence is an individual, traceable observation that supports
or refutes a threat finding. Every risk score must be explainable
through the evidence records attached to a candidate.

Key constraints:
  - Evidence must NEVER be invented.
  - is_synthetic MUST be True for all demo/test data.
  - The evidence_value field stores the raw observed value
    (e.g. the actual username, the matched text, the URL).
"""

import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.candidate import Candidate


class EvidenceType(str, enum.Enum):
    """
    Taxonomy of evidence that the detection engine can collect.
    Aligns with the signal calculators in the detection engine.
    """
    # Identity signals
    USERNAME_SIMILARITY = "USERNAME_SIMILARITY"
    NAME_SIMILARITY = "NAME_SIMILARITY"
    # Visual signals
    LOGO_SIMILARITY = "LOGO_SIMILARITY"
    ICON_SIMILARITY = "ICON_SIMILARITY"
    # Content signals
    BIO_SIMILARITY = "BIO_SIMILARITY"
    DESCRIPTION_SIMILARITY = "DESCRIPTION_SIMILARITY"
    # Link / contact signals
    DOMAIN_RISK = "DOMAIN_RISK"
    LINK_RISK = "LINK_RISK"
    CONTACT_MISMATCH = "CONTACT_MISMATCH"
    # App-specific signals
    APP_METADATA = "APP_METADATA"
    DEVELOPER_MISMATCH = "DEVELOPER_MISMATCH"
    PACKAGE_SIMILARITY = "PACKAGE_SIMILARITY"
    # Account / app anomalies
    ACCOUNT_ANOMALY = "ACCOUNT_ANOMALY"
    ACTIVITY_ANOMALY = "ACTIVITY_ANOMALY"
    # Reputation
    STORE_FLAG = "STORE_FLAG"
    USER_REPORT = "USER_REPORT"
    # Catch-all
    OTHER = "OTHER"


class EvidenceSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Evidence(UUIDPrimaryKey, TimestampMixin, Base):
    """
    A single, traceable piece of evidence attached to a Candidate.

    The detection engine creates Evidence records automatically.
    Analysts can also add manual evidence during investigation.
    """

    __tablename__ = "evidence"

    # ── Foreign key ───────────────────────────────────────────
    candidate_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Classification ────────────────────────────────────────
    evidence_type: Mapped[EvidenceType] = mapped_column(
        Enum(EvidenceType),
        nullable=False,
        index=True,
    )
    severity: Mapped[EvidenceSeverity] = mapped_column(
        Enum(EvidenceSeverity),
        nullable=False,
        default=EvidenceSeverity.MEDIUM,
    )

    # ── Content ───────────────────────────────────────────────
    title: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="Short human-readable label for this evidence item",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed explanation of what was observed",
    )
    evidence_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="The raw observed value (username, matched text, URL, hash, etc.)",
    )
    similarity_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Normalised similarity score 0.0–1.0 where applicable",
    )

    # ── Source ────────────────────────────────────────────────
    source: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Where this evidence was collected from (e.g. 'Twitter API', 'Manual')",
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        comment="Direct URL to the evidence source if available",
    )
    collected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Data integrity ────────────────────────────────────────
    is_synthetic: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "MUST be True for all demo/synthetic data. "
            "Never claim synthetic evidence is real-world data."
        ),
    )

    # ── Relationship ──────────────────────────────────────────
    candidate: Mapped["Candidate"] = relationship(
        "Candidate",
        back_populates="evidence_items",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<Evidence id={self.id!r} type={self.evidence_type} "
            f"severity={self.severity} candidate_id={self.candidate_id!r}>"
        )
