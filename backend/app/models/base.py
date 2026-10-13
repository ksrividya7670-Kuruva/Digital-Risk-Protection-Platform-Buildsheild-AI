"""
Shared base mixin for all ORM models.

Provides:
  - UUID primary key (string-stored for SQLite compatibility)
  - created_at / updated_at timestamps with automatic management
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column


def _utcnow() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """
    Adds created_at and updated_at to any model.
    updated_at is automatically refreshed on every UPDATE.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        server_default=func.now(),
        nullable=False,
    )


class UUIDPrimaryKey:
    """
    Adds a UUID primary key stored as a VARCHAR(36).
    Using string UUIDs keeps the schema compatible with both
    SQLite (no native UUID type) and PostgreSQL.
    """

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
