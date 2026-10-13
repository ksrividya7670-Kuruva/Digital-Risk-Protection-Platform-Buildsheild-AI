"""
ORM model registry.

All models are imported here so that:
  1. SQLAlchemy's metadata is aware of every table.
  2. Alembic's autogenerate can discover all models in one import.
  3. Application code can do: from app.models import Brand, Candidate, etc.

Import order matters — parent tables before child tables
to satisfy FK references during metadata inspection.
"""

from app.models.brand import Brand
from app.models.candidate import Candidate, CandidateType, CandidateStatus, DataSource
from app.models.evidence import Evidence, EvidenceType, EvidenceSeverity
from app.models.risk_assessment import RiskAssessment, RiskLevel
from app.models.case import Case, CaseNote, CasePriority, CaseStatus

__all__ = [
    # Models
    "Brand",
    "Candidate",
    "Evidence",
    "RiskAssessment",
    "Case",
    "CaseNote",
    # Enums (exported so API layer can use them directly)
    "CandidateType",
    "CandidateStatus",
    "DataSource",
    "EvidenceType",
    "EvidenceSeverity",
    "RiskLevel",
    "CasePriority",
    "CaseStatus",
]
