"""
API layer tests for BrandShield AI Step 5.

Uses FastAPI's synchronous TestClient — all test functions are regular def,
not async. The TestClient triggers the lifespan which auto-creates tables
for SQLite URLs.

Tests check HTTP status codes and response structure only — counts and
specific values depend on whether demo data has been seeded.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Health ────────────────────────────────────────────────────────────────────

def test_health():
    r = client.get("/health")
    assert r.status_code == 200


# ── Brands ───────────────────────────────────────────────────────────────────

def test_list_brands():
    r = client.get("/api/v1/brands")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_brand_not_found():
    r = client.get("/api/v1/brands/nonexistent-id-12345")
    assert r.status_code == 404


def test_brand_summary_not_found():
    r = client.get("/api/v1/brands/nonexistent-id-12345/summary")
    assert r.status_code == 404


# ── Candidates ───────────────────────────────────────────────────────────────

def test_list_candidates():
    r = client.get("/api/v1/candidates")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


def test_filter_candidates_by_type():
    r = client.get("/api/v1/candidates?candidate_type=SOCIAL_PROFILE")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data


def test_filter_candidates_invalid_type():
    r = client.get("/api/v1/candidates?candidate_type=INVALID_TYPE")
    assert r.status_code in (400, 422)


def test_candidate_not_found():
    r = client.get("/api/v1/candidates/nonexistent-id-12345")
    assert r.status_code == 404


def test_candidate_pagination():
    r = client.get("/api/v1/candidates?page=1&page_size=5")
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) <= 5


# ── Threats ──────────────────────────────────────────────────────────────────

def test_list_threats():
    r = client.get("/api/v1/threats")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


def test_threat_summary():
    r = client.get("/api/v1/threats/summary")
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "critical" in data
    assert "high" in data
    assert "medium" in data
    assert "low" in data


def test_filter_threats_by_risk_level():
    r = client.get("/api/v1/threats?risk_level=HIGH")
    assert r.status_code == 200


# ── Analytics ────────────────────────────────────────────────────────────────

def test_analytics_overview():
    r = client.get("/api/v1/analytics/overview")
    assert r.status_code == 200
    data = r.json()
    assert "total_candidates" in data
    assert "social_candidates" in data
    assert "app_candidates" in data


def test_analytics_trends():
    r = client.get("/api/v1/analytics/trends")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ── Cases ────────────────────────────────────────────────────────────────────

def test_create_case_invalid_candidate():
    r = client.post(
        "/api/v1/cases",
        json={
            "candidate_id": "nonexistent-id-12345",
            "brand_id": "nonexistent-brand-12345",
            "title": "Test Case",
        },
    )
    assert r.status_code == 404


def test_list_cases():
    r = client.get("/api/v1/cases")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


def test_case_not_found():
    r = client.get("/api/v1/cases/nonexistent-id-12345")
    assert r.status_code == 404


def test_patch_case_not_found():
    r = client.patch(
        "/api/v1/cases/nonexistent-id-12345",
        json={"status": "RESOLVED"},
    )
    assert r.status_code == 404
