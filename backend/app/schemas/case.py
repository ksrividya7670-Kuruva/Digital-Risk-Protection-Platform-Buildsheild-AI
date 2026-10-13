"""
Case management Pydantic schemas for the BrandShield AI API.

CaseCreate        — request body to open a new investigation case.
CasePatchRequest  — partial update body for PATCH /cases/{id}.
CaseNoteCreate    — request body to append an investigation note.
CaseNoteResponse  — response for a single case note.
CaseListItem      — lightweight case row for paginated lists.
CaseDetail        — full case with notes, used in GET/POST responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class CaseCreate(BaseModel):
    """Request body for opening a new investigation case."""

    model_config = {"from_attributes": True}

    candidate_id: str
    brand_id: str
    title: str
    description: Optional[str] = None
    priority: str = "MEDIUM"
    assigned_to: Optional[str] = None
    created_by: Optional[str] = None


class CasePatchRequest(BaseModel):
    """Partial update payload for PATCH /api/v1/cases/{case_id}."""

    model_config = {"from_attributes": True}

    status: Optional[str] = None
    priority: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None


class CaseNoteCreate(BaseModel):
    """Request body to append a timestamped note to a case."""

    model_config = {"from_attributes": True}

    author: str
    content: str


class CaseNoteResponse(BaseModel):
    """Response schema for a single case note."""

    model_config = {"from_attributes": True}

    id: str
    case_id: str
    author: str
    content: str
    created_at: datetime


class CaseListItem(BaseModel):
    """Lightweight case representation for paginated list endpoints."""

    model_config = {"from_attributes": True}

    id: str
    title: str
    status: str
    priority: str
    assigned_to: Optional[str] = None
    candidate_id: str
    brand_id: str
    created_at: datetime
    updated_at: datetime


class CaseDetail(BaseModel):
    """
    Full case response including all fields, notes, and timestamps.

    Returned by POST /cases, GET /cases/{id}, and PATCH /cases/{id}.
    """

    model_config = {"from_attributes": True}

    id: str
    title: str
    status: str
    priority: str
    assigned_to: Optional[str] = None
    candidate_id: str
    brand_id: str
    description: Optional[str] = None
    created_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    notes: List[CaseNoteResponse] = []
