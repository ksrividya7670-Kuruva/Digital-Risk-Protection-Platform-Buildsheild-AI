"""
Case management service.

All functions are async and take an AsyncSession as the first argument.
Uses SQLAlchemy 2.0 select() style — no session.query() calls.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Case, CaseNote, CaseStatus, Candidate
from app.schemas.case import CaseCreate


async def create_case(db: AsyncSession, data: CaseCreate) -> Case:
    """
    Create a new investigation case for a candidate.

    Raises ValueError if the candidate_id does not resolve to an
    existing Candidate record.
    """
    # Validate candidate exists
    result = await db.execute(
        select(Candidate).where(Candidate.id == data.candidate_id)
    )
    candidate = result.scalar_one_or_none()
    if candidate is None:
        raise ValueError("Candidate not found")

    case = Case(
        id=str(uuid.uuid4()),
        candidate_id=data.candidate_id,
        brand_id=data.brand_id,
        title=data.title,
        description=data.description,
        priority=data.priority,
        assigned_to=data.assigned_to,
        created_by=data.created_by,
        status=CaseStatus.OPEN,
    )
    db.add(case)
    await db.flush()
    await db.refresh(case)
    return case


async def get_case(db: AsyncSession, case_id: str) -> Optional[Case]:
    """
    Load a case by ID with its notes eagerly loaded.

    Returns None if the case does not exist.
    """
    result = await db.execute(
        select(Case)
        .where(Case.id == case_id)
        .options(
            selectinload(Case.notes),
        )
    )
    return result.scalar_one_or_none()


async def list_cases(
    db: AsyncSession,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Case], int]:
    """
    Return a paginated list of cases with optional status/priority filters.

    Returns (items, total_count).
    """
    base_conditions = []
    if status is not None:
        base_conditions.append(Case.status == status)
    if priority is not None:
        base_conditions.append(Case.priority == priority)

    # Total count
    count_q = select(func.count(Case.id))
    if base_conditions:
        count_q = count_q.where(*base_conditions)
    total_result = await db.execute(count_q)
    total = total_result.scalar_one()

    # Paginated items
    items_q = (
        select(Case)
        .order_by(Case.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if base_conditions:
        items_q = items_q.where(*base_conditions)

    items_result = await db.execute(items_q)
    items = list(items_result.scalars().all())
    return items, total


async def update_case(
    db: AsyncSession,
    case_id: str,
    updates: dict,
) -> Optional[Case]:
    """
    Apply a partial update to a case.

    If the new status is RESOLVED or FALSE_POSITIVE, resolved_at is set
    to the current UTC time.

    Returns the updated Case, or None if the case was not found.
    """
    result = await db.execute(
        select(Case)
        .where(Case.id == case_id)
        .options(selectinload(Case.notes))
    )
    case = result.scalar_one_or_none()
    if case is None:
        return None

    allowed_fields = {"status", "priority", "description", "assigned_to", "resolution_notes"}
    for field, value in updates.items():
        if field in allowed_fields:
            setattr(case, field, value)

    # Set resolution timestamp when closing a case
    new_status = updates.get("status")
    if new_status in (CaseStatus.RESOLVED, CaseStatus.FALSE_POSITIVE):
        case.resolved_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(case)
    return case


async def add_note(
    db: AsyncSession,
    case_id: str,
    author: str,
    content: str,
) -> CaseNote:
    """
    Append a timestamped note to an existing case.

    Raises ValueError if the case does not exist.
    """
    case_check = await db.execute(select(Case).where(Case.id == case_id))
    if case_check.scalar_one_or_none() is None:
        raise ValueError(f"Case '{case_id}' not found")

    note = CaseNote(
        id=str(uuid.uuid4()),
        case_id=case_id,
        author=author,
        content=content,
    )
    db.add(note)
    await db.flush()
    await db.refresh(note)
    return note
