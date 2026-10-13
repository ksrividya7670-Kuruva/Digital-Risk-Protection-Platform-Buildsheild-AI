"""
Case and CaseNote models.

A Case is opened by an analyst to formally investigate a threat.
It links a Candidate (and its RiskAssessment) to a structured
investigation workflow with status tracking and timestamped notes.

Case lifecycle:
  OPEN → INVESTIGATING → ESCALATED → RESOLVED
                      ↘              → FALSE_POSITIVE
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.brand import Brand


class CasePriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CaseStatus(str, enum.Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class Case(UUIDPrimaryKey, TimestampMixin, Base):
    """
    A formal investigation case opened against a Candidate.

    One Candidate should have at most one active Case at a time,
    though historical closed cases may accumulate.
    """

    __tablename__ = "cases"

    # ── Foreign keys ──────────────────────────────────────────
    candidate_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    brand_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Case metadata ─────────────────────────────────────────
    title: Mapped[str] = mapped_column(
        String(400),
        nullable=False,
        comment="Short case title (pre-filled from candidate name + platform)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Initial case description from the analyst",
    )
    priority: Mapped[CasePriority] = mapped_column(
        Enum(CasePriority),
        nullable=False,
        default=CasePriority.MEDIUM,
        index=True,
    )
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus),
        nullable=False,
        default=CaseStatus.OPEN,
        index=True,
    )

    # ── Assignment ────────────────────────────────────────────
    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Email or username of the assigned analyst",
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Email or username of the analyst who opened the case",
    )

    # ── Resolution ────────────────────────────────────────────
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Set when status transitions to RESOLVED or FALSE_POSITIVE",
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Final resolution summary",
    )

    # ── Relationships ─────────────────────────────────────────
    candidate: Mapped["Candidate"] = relationship(
        "Candidate",
        back_populates="cases",
        lazy="select",
    )
    brand: Mapped["Brand"] = relationship(
        "Brand",
        back_populates="cases",
        lazy="select",
    )
    notes: Mapped[List["CaseNote"]] = relationship(
        "CaseNote",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="CaseNote.created_at.asc()",
    )

    def __repr__(self) -> str:
        return (
            f"<Case id={self.id!r} title={self.title!r} "
            f"status={self.status} priority={self.priority}>"
        )


class CaseNote(UUIDPrimaryKey, TimestampMixin, Base):
    """
    A timestamped investigation note added to a Case by an analyst.

    Notes are append-only — analysts add observations, actions taken,
    and next steps as the investigation progresses.
    """

    __tablename__ = "case_notes"

    # ── Foreign key ───────────────────────────────────────────
    case_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Content ───────────────────────────────────────────────
    author: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Email or username of the analyst who wrote this note",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Free-text investigation note",
    )

    # ── Relationship ──────────────────────────────────────────
    case: Mapped["Case"] = relationship(
        "Case",
        back_populates="notes",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<CaseNote id={self.id!r} case_id={self.case_id!r} author={self.author!r}>"
