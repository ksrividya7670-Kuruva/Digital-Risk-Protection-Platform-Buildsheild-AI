"""
Cases API router — investigation case management.

Endpoints:
  POST   /api/v1/cases/               — open a new case
  GET    /api/v1/cases/               — paginated list of cases
  GET    /api/v1/cases/{case_id}      — full case detail
  PATCH  /api/v1/cases/{case_id}      — partial update (status, priority, etc.)
  POST   /api/v1/cases/{case_id}/notes — append an investigation note
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models import CasePriority, CaseStatus
from app.schemas.case import (
    CaseCreate,
    CaseDetail,
    CaseListItem,
    CaseNoteCreate,
    CaseNoteResponse,
    CasePatchRequest,
)
from app.services import case_service

router = APIRouter()

VALID_STATUSES = {e.value for e in CaseStatus}
VALID_PRIORITIES = {e.value for e in CasePriority}


@router.post(
    "/",
    response_model=CaseDetail,
    status_code=201,
    summary="Create case",
    description=(
        "Opens a new investigation case for a candidate. "
        "Returns 404 if the candidate_id does not exist."
    ),
)
async def create_case_endpoint(
    body: CaseCreate,
    db: AsyncSession = Depends(get_db),
) -> CaseDetail:
    try:
        case = await case_service.create_case(db, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    full_case = await case_service.get_case(db, case.id)
    return CaseDetail.model_validate(full_case)


@router.get(
    "/",
    summary="List cases",
    description="Returns a paginated list of investigation cases. Supports filtering by status and priority.",
)
async def list_cases_endpoint(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    if status is not None and status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{status}'. Must be one of: {sorted(VALID_STATUSES)}",
        )
    if priority is not None and priority not in VALID_PRIORITIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid priority '{priority}'. Must be one of: {sorted(VALID_PRIORITIES)}",
        )

    items, total = await case_service.list_cases(db, status, priority, page, page_size)
    return {
        "items": [CaseListItem.model_validate(c).model_dump() for c in items],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get(
    "/{case_id}",
    response_model=CaseDetail,
    summary="Get case by ID",
    description="Returns the full case including investigation notes. Returns 404 if not found.",
)
async def get_case_endpoint(
    case_id: str,
    db: AsyncSession = Depends(get_db),
) -> CaseDetail:
    case = await case_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
    return CaseDetail.model_validate(case)


@router.patch(
    "/{case_id}",
    response_model=CaseDetail,
    summary="Update case",
    description=(
        "Partially updates a case. Allowed fields: status, priority, description, "
        "assigned_to, resolution_notes. Returns 404 if not found."
    ),
)
async def update_case_endpoint(
    case_id: str,
    body: CasePatchRequest,
    db: AsyncSession = Depends(get_db),
) -> CaseDetail:
    # Validate enum values if provided
    if body.status is not None and body.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{body.status}'. Allowed: {sorted(VALID_STATUSES)}",
        )
    if body.priority is not None and body.priority not in VALID_PRIORITIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid priority '{body.priority}'. Allowed: {sorted(VALID_PRIORITIES)}",
        )

    updated = await case_service.update_case(
        db, case_id, body.model_dump(exclude_none=True)
    )
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
    return CaseDetail.model_validate(updated)


@router.post(
    "/{case_id}/notes",
    response_model=CaseNoteResponse,
    status_code=201,
    summary="Add investigation note",
    description="Appends a timestamped investigation note to a case. Returns 404 if the case does not exist.",
)
async def add_note_endpoint(
    case_id: str,
    body: CaseNoteCreate,
    db: AsyncSession = Depends(get_db),
) -> CaseNoteResponse:
    try:
        note = await case_service.add_note(db, case_id, body.author, body.content)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return CaseNoteResponse.model_validate(note)
