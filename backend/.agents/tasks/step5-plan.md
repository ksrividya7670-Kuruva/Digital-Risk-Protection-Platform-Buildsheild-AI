# Implementation Plan — Step 5: Backend API Layer

## Context from codebase exploration

- **Stack**: FastAPI + SQLAlchemy 2.0 async + aiosqlite (SQLite dev) / asyncpg (prod)
- **DB session**: `get_db()` dependency in `app/db/database.py` — commits on success, rolls back on exception
- **Existing routers**: `/health`, `/api/v1/detection`, `/api/v1/demo`
- **ORM models**: `Brand`, `Candidate` (with `CandidateType`, `CandidateStatus`), `Evidence`, `RiskAssessment` (with `RiskLevel`), `Case` + `CaseNote` (with `CasePriority`, `CaseStatus`)
- **Key constraint**: `RiskAssessment.evidence_score` (DB column) ↔ `DetectionResult.evidence_score_val` (engine output) — they differ by name; the column is `evidence_score`
- **Existing schema convention**: `model_config = {"from_attributes": True}` as seen in `RiskAssessmentSchema`
- **All route handlers**: `async def`; all DB queries use `select()` style (SQLAlchemy 2.0)
- **Tests**: pytest with `asyncio_mode = auto`; run with `cd backend && .venv\Scripts\python.exe -m pytest`; `TestClient` from `fastapi.testclient` is synchronous (regular `def test_`)
- **No new packages**: `httpx` already in requirements (used by `TestClient` internally)
- **Signal weights** in `app/services/detection/contracts.py` `SIGNAL_WEIGHTS` dict
- **Case model fields**: `candidate_id`, `brand_id`, `title`, `description`, `priority`, `status`, `assigned_to`, `created_by`, `resolved_at`, `resolution_notes`, `notes` (rel)
- **CaseNote model fields**: `case_id`, `author`, `content`
- **`docs/` directory**: does not exist yet — create it

---

## Implementation Plan

- [ ] 1. Create `app/schemas/brand.py` with three Pydantic models.
      Define `BrandResponse` (all public Brand columns, no relationships), `BrandSummaryResponse` (brand_id, name, total_candidates, social_candidates, mobile_app_candidates, critical_threats, high_threats, medium_threats, low_threats, open_cases), and `BrandCreate` (name, official_domain, description, industry — fields needed to create a brand; other fields Optional). All three use `model_config = {"from_attributes": True}`.
      Files: `app/schemas/brand.py`
      Verify: `cd backend && .venv\Scripts\python.exe -c "from app.schemas.brand import BrandResponse, BrandSummaryResponse, BrandCreate; print('OK')"` — prints OK with no import error.

- [ ] 2. Create `app/schemas/candidate.py` with four Pydantic models.
      Define `EvidenceItem` (id, evidence_type, severity, title, description, evidence_value, similarity_score, source, source_url, collected_at, is_synthetic — maps to `Evidence` model), `SignalItem` (signal_name, raw_score, weight, weighted_contribution, explanation — reconstructed in route handler), `CandidateListItem` (id, name, username, platform, candidate_type, profile_url, brand_id, risk_score, risk_level, confidence, status, discovered_at — `discovered_at` maps to `Candidate.created_at`), and `CandidateDetail` (all `CandidateListItem` fields plus bio_description, website_url, contact_email, icon_url, follower_count, following_count, account_age_days, is_verified, package_name, developer_name, developer_email, app_version, install_count, app_rating, signals: list[SignalItem], evidence: list[EvidenceItem], detection_summary, ai_explanation, calculated_at). All use `model_config = {"from_attributes": True}`.
      Files: `app/schemas/candidate.py`
      Verify: `cd backend && .venv\Scripts\python.exe -c "from app.schemas.candidate import CandidateListItem, CandidateDetail, EvidenceItem, SignalItem; print('OK')"` — prints OK.

- [ ] 3. Create `app/schemas/case.py` with five Pydantic models.
      Define `CaseCreate` (candidate_id: str, brand_id: str, title: str, description: Optional[str], priority: CasePriority = MEDIUM, assigned_to: Optional[str], created_by: Optional[str]), `CaseNoteCreate` (author: str, content: str), `CaseNoteResponse` (id, case_id, author, content, created_at — `from_attributes=True`), `CaseListItem` (id, candidate_id, brand_id, title, status, priority, assigned_to, created_at, resolved_at), `CaseDetail` (all `CaseListItem` fields plus description, created_by, resolution_notes, notes: list[CaseNoteResponse], and candidate sub-info as Optional[CandidateListItem]). Import `CasePriority`, `CaseStatus` from `app.models`. All use `model_config = {"from_attributes": True}`.
      Files: `app/schemas/case.py`
      Verify: `cd backend && .venv\Scripts\python.exe -c "from app.schemas.case import CaseCreate, CaseDetail, CaseListItem, CaseNoteResponse; print('OK')"` — prints OK.

- [ ] 4. Create `app/schemas/analytics.py` with three Pydantic models.
      Define `ThreatTrend` (date: str, count: int — one entry per calendar day), `ThreatSummaryResponse` (total_threats, critical, high, medium, low, social_threats, mobile_app_threats, average_score: float, highest_score: int, open_cases: int), and `AnalyticsOverview` (total_candidates, social_candidates, mobile_app_candidates, risk_distribution: dict[str, int], average_risk_score: float, critical_count, high_count, medium_count, low_count, open_cases, platforms: dict[str, int], candidate_type_breakdown: dict[str, int], trends: list[ThreatTrend]). All use `model_config = {"from_attributes": True}`.
      Files: `app/schemas/analytics.py`
      Verify: `cd backend && .venv\Scripts\python.exe -c "from app.schemas.analytics import AnalyticsOverview, ThreatTrend, ThreatSummaryResponse; print('OK')"` — prints OK.

- [ ] 5. Create `app/services/case_service.py` with five async functions.

      **`create_case(db, data: CaseCreate) -> Case`**: Insert a new `Case` row using `uuid.uuid4()` for id. Validate that the `candidate_id` resolves to an existing `Candidate` (raise `ValueError` if not). Set status=OPEN. Commit, refresh, return.

      **`get_case(db, case_id: str) -> Case | None`**: `select(Case).where(Case.id == case_id)` with `selectinload(Case.notes)` and `selectinload(Case.candidate)`. Return scalar or None.

      **`list_cases(db, status, priority, page, page_size) -> tuple[list[Case], int]`**: Build a `select(Case)` with optional `.where(Case.status == status)` and `.where(Case.priority == priority)` clauses (both optional). Count total with a separate `select(func.count())` using the same filters. Apply `.offset((page-1)*page_size).limit(page_size).order_by(Case.created_at.desc())`. Return (items, total).

      **`update_case(db, case_id: str, patch: dict) -> Case | None`**: Fetch case, apply allowed fields from patch (`status`, `priority`, `description`, `assigned_to`, `resolution_notes`). If new status is RESOLVED or FALSE_POSITIVE, set `resolved_at = datetime.now(timezone.utc)`. Commit, refresh, return.

      **`add_note(db, case_id: str, data: CaseNoteCreate) -> CaseNote`**: Validate case exists, insert `CaseNote` with new uuid, `case_id`, `author`, `content`. Commit, refresh, return.

      Use `from sqlalchemy import select, func` throughout. No `session.query()`.
      Files: `app/services/case_service.py`
      Verify: `cd backend && .venv\Scripts\python.exe -c "from app.services.case_service import create_case, get_case, list_cases, update_case, add_note; print('OK')"` — prints OK.

- [ ] 6. Create `app/api/v1/brands.py` with three route handlers.

      **`GET /`** (`list_brands`): `select(Brand).order_by(Brand.name)` — return all brands as `list[BrandResponse]`. No pagination needed (brand count is small).

      **`GET /{brand_id}`** (`get_brand`): `select(Brand).where(Brand.id == brand_id)`. Wrap in try/except to catch malformed IDs gracefully. Return 404 with `{"detail": "Brand not found"}` if None.

      **`GET /{brand_id}/summary`** (`get_brand_summary`): Load brand (404 if missing). Use the latest-RA subquery pattern (see below) joined to Candidate to count per-risk-level threats and totals. Count open cases with `select(func.count(Case.id)).where(Case.brand_id == brand_id, Case.status.in_(["OPEN", "INVESTIGATING", "ESCALATED"]))`. Assemble and return `BrandSummaryResponse`.

      The latest-RA subquery pattern for all risk-counting queries:
      ```python
      from sqlalchemy import select, func
      latest_ra_subq = (
          select(
              RiskAssessment.candidate_id,
              func.max(RiskAssessment.calculated_at).label("max_calc")
          )
          .group_by(RiskAssessment.candidate_id)
          .subquery()
      )
      # Join: Candidate
      #   LEFT JOIN latest_ra_subq ON Candidate.id == latest_ra_subq.c.candidate_id
      #   LEFT JOIN RiskAssessment ON (RiskAssessment.candidate_id == latest_ra_subq.c.candidate_id
      #                                AND RiskAssessment.calculated_at == latest_ra_subq.c.max_calc)
      ```
      Use this join to attach current risk level per candidate, then group by `RiskAssessment.risk_level`.

      Files: `app/api/v1/brands.py`
      Verify: (step 11 registers router first) `cd backend && .venv\Scripts\python.exe -c "from app.api.v1.brands import router; print(len(router.routes), 'routes')"` — prints `3 routes`.

- [ ] 7. Create `app/api/v1/candidates.py` with two route handlers.

      **`GET /`** (`list_candidates`): Accept query params: `brand_id: Optional[str]`, `candidate_type: Optional[str]`, `platform: Optional[str]`, `status: Optional[str]`, `risk_level: Optional[str]`, `min_score: Optional[int]`, `max_score: Optional[int]`, `page: int = 1`, `page_size: int = 20`. Build a `select(Candidate, RiskAssessment)` using the latest-RA subquery LEFT JOINs. Add `.where()` clauses for each non-None filter — validate enum values (return 422 with `HTTPException` if invalid). Count total with the same filters. Return `{"items": [...], "page": page, "page_size": page_size, "total": total}` where each item is `CandidateListItem` (populate `risk_score` from `RiskAssessment.total_score`, `risk_level` from `RiskAssessment.risk_level`, `confidence` from `RiskAssessment.confidence`, `discovered_at` from `Candidate.created_at`).

      **`GET /{candidate_id}`** (`get_candidate`): Load Candidate with `selectinload(Candidate.evidence_items)`, LEFT JOIN latest RA. Return 404 if missing. Reconstruct signals from RA columns using `SIGNAL_MAP`:
      ```python
      SIGNAL_MAP = [
          ("identity_similarity", ra.identity_similarity_score, 25),
          ("visual_similarity",   ra.visual_similarity_score,   20),
          ("content_similarity",  ra.content_similarity_score,  15),
          ("link_risk",           ra.link_contact_score,        15),
          ("account_anomaly",     ra.anomaly_score,             10),
          ("evidence_score",      ra.evidence_score,            10),
          ("activity_anomaly",    ra.activity_score,             5),
      ]
      ```
      For each entry, `raw_score = (stored_weighted_score / weight)` clamped to [0,1]; `weighted_contribution = stored_weighted_score`; `explanation = ra.detection_summary` (shared text, acceptable for MVP). Return `CandidateDetail`.

      Files: `app/api/v1/candidates.py`
      Verify: `cd backend && .venv\Scripts\python.exe -c "from app.api.v1.candidates import router; print(len(router.routes), 'routes')"` — prints `2 routes`.

- [ ] 8. Create `app/api/v1/threats.py` with two route handlers.

      **Decision**: `GET /summary` must be registered BEFORE `GET /` to avoid FastAPI routing `summary` as a path param. Achieve this by defining `summary` route first in the router.

      **`GET /summary`** (`get_threats_summary`): Use the latest-RA subquery to join all Candidates with their current RA. Count per risk_level using `func.count()` grouped by `RiskAssessment.risk_level`. Count per `candidate_type`. Compute `avg(RiskAssessment.total_score)` and `max(RiskAssessment.total_score)`. Count open cases. Return `ThreatSummaryResponse`.

      **`GET /`** (`list_threats`): Accept query params: `risk_level: Optional[str]`, `candidate_type: Optional[str]`, `platform: Optional[str]`, `status: Optional[str]`, `min_score: Optional[int]`, `sort: str = "risk_score_desc"` (allowed values: `risk_score_desc`, `risk_score_asc`, `newest`, `oldest`), `page: int = 1`, `page_size: int = 20`. Only return candidates that HAVE a RiskAssessment (INNER JOIN on RA, not LEFT JOIN). Apply filters. Apply sort: `risk_score_desc` → `RiskAssessment.total_score.desc()`; `risk_score_asc` → `.asc()`; `newest` → `Candidate.created_at.desc()`; `oldest` → `.asc()`. Return paginated response where each item includes: id, name, platform, candidate_type, risk_score, risk_level, confidence, top_reasons (split first 2 sentences from `detection_summary`), status, discovered_at.

      Files: `app/api/v1/threats.py`
      Verify: `cd backend && .venv\Scripts\python.exe -c "from app.api.v1.threats import router; print(len(router.routes), 'routes')"` — prints `2 routes`.

- [ ] 9. Create `app/api/v1/cases.py` with five route handlers, all delegating to `case_service`.

      **`POST /`** (`create_case`): Accept `CaseCreate` body. Call `case_service.create_case(db, data)`. Catch `ValueError` → 404. Return 201 + `CaseDetail`.

      **`GET /`** (`list_cases`): Accept `status: Optional[str]`, `priority: Optional[str]`, `page: int = 1`, `page_size: int = 20`. Validate status against `CaseStatus` enum values; validate priority against `CasePriority` enum values (return 422 on invalid). Call `case_service.list_cases(...)`. Return `{"items": [...], "page": page, "page_size": page_size, "total": total}` where each item is `CaseListItem`.

      **`GET /{case_id}`** (`get_case`): Call `case_service.get_case(db, case_id)`. Return 404 if None. Return `CaseDetail` (include notes and linked candidate info).

      **`PATCH /{case_id}`** (`update_case`): Accept body `CasePatchRequest` (inline Pydantic model with Optional fields: status, priority, description, assigned_to, resolution_notes). Validate status value if provided. Call `case_service.update_case(db, case_id, patch.model_dump(exclude_none=True))`. Return 404 if None. Return `CaseDetail`.

      **`POST /{case_id}/notes`** (`add_note`): Accept `CaseNoteCreate` body. Call `case_service.add_note(db, case_id, data)`. Catch `ValueError` → 404. Return 201 + `CaseNoteResponse`.

      Files: `app/api/v1/cases.py`
      Verify: `cd backend && .venv\Scripts\python.exe -c "from app.api.v1.cases import router; print(len(router.routes), 'routes')"` — prints `5 routes`.

- [ ] 10. Create `app/api/v1/analytics.py` with two route handlers.

      **`GET /overview`** (`get_overview`): Single DB round-trip per count group where practical. Compute:
      - `total_candidates` → `select(func.count(Candidate.id))`
      - `social_candidates` → filter `candidate_type == SOCIAL_PROFILE`
      - `mobile_app_candidates` → filter `candidate_type == MOBILE_APP`
      - risk_distribution (CRITICAL/HIGH/MEDIUM/LOW counts), average_risk_score, highest score → via latest-RA subquery grouping
      - `open_cases` → `select(func.count(Case.id)).where(Case.status.in_(["OPEN", "INVESTIGATING", "ESCALATED"]))`
      - `platforms` → `select(Candidate.platform, func.count()).group_by(Candidate.platform)` — returns dict
      - `candidate_type_breakdown` → `select(Candidate.candidate_type, func.count()).group_by(Candidate.candidate_type)` — returns dict
      - `trends` → see GET /trends below; reuse the same logic

      **`GET /trends`** (`get_trends`): `select(func.date(Candidate.created_at), func.count(Candidate.id)).group_by(func.date(Candidate.created_at)).where(Candidate.created_at >= datetime.now(timezone.utc) - timedelta(days=30)).order_by(func.date(Candidate.created_at))`. Return `list[ThreatTrend]`. If no data exists, return `[]` — never fabricate history.

      Files: `app/api/v1/analytics.py`
      Verify: `cd backend && .venv\Scripts\python.exe -c "from app.api.v1.analytics import router; print(len(router.routes), 'routes')"` — prints `2 routes`.

- [ ] 11. Modify `app/main.py` to register the five new routers.
      Import `brands_router`, `candidates_router`, `threats_router`, `cases_router`, `analytics_router` from their respective modules. Add five `app.include_router(...)` calls with prefixes `/api/v1/brands`, `/api/v1/candidates`, `/api/v1/threats`, `/api/v1/cases`, `/api/v1/analytics` and tags `["Brands"]`, `["Candidates"]`, `["Threats"]`, `["Cases"]`, `["Analytics"]`. Replace the commented-out placeholder lines with the real registrations. Do not change the existing health, detection, or demo router registrations.
      Files: `app/main.py`
      Verify: `cd backend && .venv\Scripts\python.exe -c "from app.main import app; routes = [r.path for r in app.routes]; print([r for r in routes if '/api/v1/' in r])"` — output includes `/api/v1/brands`, `/api/v1/candidates`, `/api/v1/threats`, `/api/v1/cases`, `/api/v1/analytics` paths.

- [ ] 12. Create `tests/test_api.py` with 14 API tests using `TestClient`.

      **Setup**: At module top, override the DB dependency to use a fresh in-memory SQLite DB for tests. Use this pattern:
      ```python
      import os, pytest
      os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_api_step5.db")
      from fastapi.testclient import TestClient
      from app.main import app
      client = TestClient(app)
      ```
      Note: `TestClient` runs the ASGI app synchronously — no `async` needed in test functions. All tests are regular `def test_` functions.

      **The 14 tests**:
      1. `test_list_brands` — `GET /api/v1/brands` → 200, body has `items` key or is a list (handle both — brands router returns a list directly)
      2. `test_get_brand_not_found` — `GET /api/v1/brands/nonexistent-id` → 404
      3. `test_brand_summary_not_found` — `GET /api/v1/brands/nonexistent-id/summary` → 404
      4. `test_list_candidates_empty` — `GET /api/v1/candidates` → 200, body has keys `items`, `page`, `page_size`, `total`
      5. `test_list_candidates_filter_invalid_type` — `GET /api/v1/candidates?candidate_type=INVALID` → 422 or 400
      6. `test_get_candidate_not_found` — `GET /api/v1/candidates/nonexistent-id` → 404
      7. `test_list_threats_empty` — `GET /api/v1/threats` → 200, body has keys `items`, `page`, `page_size`, `total`
      8. `test_threats_summary` — `GET /api/v1/threats/summary` → 200, body has keys `total_threats`, `critical`, `high`, `medium`, `low`
      9. `test_create_case_invalid_candidate` — `POST /api/v1/cases` with `{"candidate_id": "nonexistent", "brand_id": "nonexistent", "title": "Test"}` → 404
      10. `test_list_cases_empty` — `GET /api/v1/cases` → 200, body has keys `items`, `page`, `page_size`, `total`
      11. `test_get_case_not_found` — `GET /api/v1/cases/nonexistent-id` → 404
      12. `test_patch_case_not_found` — `PATCH /api/v1/cases/nonexistent-id` with `{"status": "RESOLVED"}` → 404
      13. `test_analytics_overview` — `GET /api/v1/analytics/overview` → 200, body has keys `total_candidates`, `social_candidates`, `mobile_app_candidates`
      14. `test_analytics_trends` — `GET /api/v1/analytics/trends` → 200, body is a list

      Every test checks only HTTP status codes and response structure (key presence), not specific counts — passes whether or not demo seed has been run.
      Files: `tests/test_api.py`
      Verify: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_api.py -v` — all 14 tests pass. Also confirm existing tests still pass: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_detection_engine.py tests/test_models.py -v`.

- [ ] 13. Create `docs/api.md` — endpoint documentation with curl examples.
      Document all 15 new endpoints (3 brands, 2 candidates, 2 threats, 5 cases, 2 analytics, 1 note sub-endpoint) with:
      - HTTP method + path
      - Short description
      - Query parameters table (name, type, default, description) for endpoints that have them
      - Request body schema (for POST/PATCH)
      - Response shape (key fields only)
      - One `curl` example per endpoint using `http://localhost:8000` as base URL
      Also include a section on consistent response format, allowed case statuses, and allowed sort values for threats.
      Files: `docs/api.md`
      Verify: File exists and is readable — `cd backend && .venv\Scripts\python.exe -m pytest -v` confirms full suite still passes (docs file does not affect tests).

---

## Dependency order summary

Items 1–4 (schemas) have no inter-dependencies and can be implemented in parallel, but are listed first because items 5–10 import from them.
Item 5 (case_service) depends on schemas from items 2 and 3.
Items 6–10 (routers) depend on schemas (1–4) and, for cases, on case_service (5).
Item 11 (main.py) depends on all routers (6–10) being importable.
Item 12 (tests) depends on item 11 (app fully wired).
Item 13 (docs) depends on nothing — can be written any time after items 6–10 are clear.

## Key pitfalls to avoid

- **`evidence_score` column name**: In `RiskAssessment`, the column is `evidence_score` (not `evidence_score_val`). The `_val` suffix exists only in `DetectionResult` (the engine dataclass).
- **`/threats/summary` vs `/{threat_id}`**: Register `GET /summary` first in the threats router so FastAPI doesn't interpret "summary" as a `threat_id` path parameter.
- **`Candidate.created_at` as `discovered_at`**: The `Candidate` model uses `created_at` (from `TimestampMixin`). Expose it as `discovered_at` in response schemas by using `Field(alias=...)` or by populating it explicitly in the route handler.
- **SQLite `func.date()`**: For the trends query, `func.date(Candidate.created_at)` works with SQLite's date() function. Returns a string like `"2025-01-15"` — store as `str` in `ThreatTrend.date`.
- **TestClient + lifespan**: `TestClient(app)` triggers the lifespan handler which calls `create_all_tables()` for SQLite URLs. Set `DATABASE_URL` env var to a SQLite URL before importing `app.main` in the test file to ensure the test DB is SQLite.
- **No `session.query()`**: Use `select()` + `await db.execute()` + `result.scalars().all()` or `result.scalar_one_or_none()` throughout — consistent with detection_service.py.
