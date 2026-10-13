# BrandShield AI — Backend API Reference

Base URL: `http://localhost:8000`

All list endpoints use the same paginated envelope:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 42
}
```

---

## Consistent Response Format

- **List endpoints** return `{ items, page, page_size, total }`.
- **Detail endpoints** return a single object.
- **Error responses** return `{ "detail": "message" }`.
- Timestamps are ISO 8601 strings (`2025-01-15T10:30:00Z`).

---

## Allowed Values

### Case statuses
`OPEN` | `INVESTIGATING` | `ESCALATED` | `RESOLVED` | `FALSE_POSITIVE`

### Case priorities
`LOW` | `MEDIUM` | `HIGH` | `CRITICAL`

### Threat sort options
`risk_score_desc` (default) | `risk_score_asc` | `newest` | `oldest`

### Risk levels
`LOW` | `MEDIUM` | `HIGH` | `CRITICAL`

---

## Brands

### GET /api/v1/brands

Returns all active monitored brands ordered by name.

**Response:** `array of BrandResponse`

```json
[
  {
    "id": "uuid",
    "name": "NovaPay",
    "official_domain": "novapay.io",
    "industry": "Fintech",
    "is_active": true,
    "created_at": "2025-01-10T00:00:00Z",
    "updated_at": "2025-01-10T00:00:00Z"
  }
]
```

**Errors:** none (returns empty list if no brands exist)

```bash
curl http://localhost:8000/api/v1/brands
```

---

### GET /api/v1/brands/{brand_id}

Returns a single brand by ID.

**Path params:** `brand_id` — brand UUID

**Response:** `BrandResponse`

**Errors:**
- `404` — brand not found

```bash
curl http://localhost:8000/api/v1/brands/abc123
```

---

### GET /api/v1/brands/{brand_id}/summary

Returns aggregated threat and candidate statistics for one brand.

**Path params:** `brand_id` — brand UUID

**Response:**

```json
{
  "brand_id": "uuid",
  "brand_name": "NovaPay",
  "total_candidates": 23,
  "social_candidates": 15,
  "app_candidates": 8,
  "critical_threats": 3,
  "high_threats": 7,
  "medium_threats": 5,
  "low_threats": 8,
  "open_cases": 4
}
```

**Errors:**
- `404` — brand not found

```bash
curl http://localhost:8000/api/v1/brands/abc123/summary
```

---

## Candidates

### GET /api/v1/candidates

Returns a paginated list of candidates with optional filters.

**Query parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| brand_id | string | — | Filter by brand UUID |
| candidate_type | string | — | `SOCIAL_PROFILE` or `MOBILE_APP` |
| platform | string | — | e.g. `Twitter`, `Instagram`, `Google Play` |
| status | string | — | `NEW`, `REVIEWING`, `CONFIRMED_THREAT`, `BENIGN`, `FALSE_POSITIVE` |
| risk_level | string | — | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| min_score | int | — | Minimum risk score (0–100) |
| max_score | int | — | Maximum risk score (0–100) |
| sort | string | `risk_score_desc` | Sort order |
| page | int | `1` | Page number |
| page_size | int | `20` | Items per page (max 100) |

**Response:**

```json
{
  "items": [
    {
      "id": "uuid",
      "brand_id": "uuid",
      "candidate_type": "SOCIAL_PROFILE",
      "platform": "Instagram",
      "name": "NovaPay Official",
      "username": "novapaypro",
      "risk_score": 82,
      "risk_level": "CRITICAL",
      "confidence": 0.91,
      "status": "NEW",
      "data_source": "MOCK",
      "discovered_at": "2025-01-10T00:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 23
}
```

**Errors:**
- `422` — invalid `candidate_type`, `status`, or `sort`

```bash
curl "http://localhost:8000/api/v1/candidates?candidate_type=SOCIAL_PROFILE&page=1&page_size=10"
```

---

### GET /api/v1/candidates/{candidate_id}

Returns the full investigation-ready detail for one candidate. Includes signal breakdown and all evidence.

**Path params:** `candidate_id` — candidate UUID

**Response:**

```json
{
  "id": "uuid",
  "brand_id": "uuid",
  "brand_name": "NovaPay",
  "candidate_type": "SOCIAL_PROFILE",
  "platform": "Instagram",
  "name": "NovaPay Official",
  "username": "novapaypro",
  "profile_url": "https://instagram.com/novapaypro",
  "risk_score": 82,
  "risk_level": "CRITICAL",
  "confidence": 0.91,
  "detection_summary": "High identity similarity detected...",
  "signals": [
    {
      "signal_name": "identity_similarity",
      "raw_score": 0.88,
      "weight": 25,
      "weighted_score": 22.0,
      "reason": "Username closely matches brand handle"
    }
  ],
  "evidence": [
    {
      "id": "uuid",
      "evidence_type": "USERNAME_SIMILARITY",
      "severity": "HIGH",
      "title": "Username similarity",
      "description": "Handle 'novapaypro' is 89% similar to official 'novapayofficial'",
      "is_synthetic": true
    }
  ]
}
```

**Errors:**
- `404` — candidate not found

```bash
curl http://localhost:8000/api/v1/candidates/abc123
```

---

## Threats

### GET /api/v1/threats/summary

Returns aggregated KPI statistics for the threat queue.

**Response:**

```json
{
  "total": 23,
  "critical": 3,
  "high": 7,
  "medium": 8,
  "low": 5,
  "social_threats": 15,
  "app_threats": 8,
  "avg_score": 62.4,
  "max_score": 95,
  "open_cases": 4
}
```

```bash
curl http://localhost:8000/api/v1/threats/summary
```

---

### GET /api/v1/threats

Returns the paginated threat queue — candidates with a risk assessment.

**Query parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| risk_level | string | — | Filter by risk level |
| candidate_type | string | — | `SOCIAL_PROFILE` or `MOBILE_APP` |
| platform | string | — | Platform filter |
| status | string | — | Candidate status filter |
| min_score | int | — | Minimum risk score |
| sort | string | `risk_score_desc` | Sort order |
| page | int | `1` | Page number |
| page_size | int | `20` | Items per page |

**Response:**

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "NovaPay Pro",
      "platform": "Instagram",
      "candidate_type": "SOCIAL_PROFILE",
      "risk_score": 82,
      "risk_level": "CRITICAL",
      "confidence": 0.91,
      "top_reasons": ["High username similarity", "Bio matches brand language"],
      "status": "NEW",
      "discovered_at": "2025-01-10T00:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 23
}
```

**Errors:**
- `422` — invalid `risk_level` or `sort`

```bash
curl "http://localhost:8000/api/v1/threats?risk_level=CRITICAL&sort=risk_score_desc"
```

---

## Cases

### POST /api/v1/cases

Opens a new investigation case for a candidate.

**Request body:**

```json
{
  "candidate_id": "uuid",
  "brand_id": "uuid",
  "title": "Suspicious Instagram account - novapaypro",
  "description": "Account is impersonating NovaPay and collecting credentials.",
  "priority": "HIGH",
  "assigned_to": "analyst@brandshield.demo",
  "created_by": "analyst@brandshield.demo"
}
```

**Response:** `CaseDetail` (status 201)

**Errors:**
- `404` — candidate not found

```bash
curl -X POST http://localhost:8000/api/v1/cases \
  -H "Content-Type: application/json" \
  -d '{"candidate_id":"uuid","brand_id":"uuid","title":"Test case"}'
```

---

### GET /api/v1/cases

Returns a paginated list of investigation cases.

**Query parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| status | string | — | Filter by case status |
| priority | string | — | Filter by priority |
| page | int | `1` | Page number |
| page_size | int | `20` | Items per page |

**Response:**

```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Suspicious account",
      "status": "OPEN",
      "priority": "HIGH",
      "candidate_id": "uuid",
      "brand_id": "uuid",
      "created_at": "2025-01-10T00:00:00Z",
      "updated_at": "2025-01-10T00:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 4
}
```

**Errors:**
- `422` — invalid status or priority

```bash
curl "http://localhost:8000/api/v1/cases?status=OPEN&priority=HIGH"
```

---

### GET /api/v1/cases/{case_id}

Returns the full case detail including all investigation notes.

**Path params:** `case_id` — case UUID

**Response:** `CaseDetail` with `notes` array

**Errors:**
- `404` — case not found

```bash
curl http://localhost:8000/api/v1/cases/abc123
```

---

### PATCH /api/v1/cases/{case_id}

Partially updates a case. All fields are optional.

**Path params:** `case_id` — case UUID

**Request body:**

```json
{
  "status": "INVESTIGATING",
  "priority": "CRITICAL",
  "assigned_to": "senior@brandshield.demo",
  "description": "Updated description",
  "resolution_notes": "Takedown request submitted"
}
```

**Allowed status values:** `OPEN`, `INVESTIGATING`, `ESCALATED`, `RESOLVED`, `FALSE_POSITIVE`

Setting status to `RESOLVED` or `FALSE_POSITIVE` automatically sets `resolved_at`.

**Response:** Updated `CaseDetail`

**Errors:**
- `404` — case not found
- `422` — invalid status or priority

```bash
curl -X PATCH http://localhost:8000/api/v1/cases/abc123 \
  -H "Content-Type: application/json" \
  -d '{"status":"INVESTIGATING"}'
```

---

### POST /api/v1/cases/{case_id}/notes

Appends a timestamped investigation note to a case.

**Path params:** `case_id` — case UUID

**Request body:**

```json
{
  "author": "analyst@brandshield.demo",
  "content": "Contacted platform trust and safety team. Awaiting response."
}
```

**Response:** `CaseNoteResponse` (status 201)

**Errors:**
- `404` — case not found

```bash
curl -X POST http://localhost:8000/api/v1/cases/abc123/notes \
  -H "Content-Type: application/json" \
  -d '{"author":"analyst@example.com","content":"Investigation note text"}'
```

---

## Analytics

### GET /api/v1/analytics/overview

Returns all data needed for the analytics dashboard.

**Response:**

```json
{
  "total_candidates": 23,
  "social_candidates": 15,
  "app_candidates": 8,
  "critical": 3,
  "high": 7,
  "medium": 8,
  "low": 5,
  "avg_score": 62.4,
  "max_score": 95,
  "open_cases": 4,
  "by_platform": {
    "Instagram": 5,
    "Twitter": 4,
    "Google Play": 6,
    "App Store": 2
  },
  "by_type": {
    "SOCIAL_PROFILE": 15,
    "MOBILE_APP": 8
  }
}
```

```bash
curl http://localhost:8000/api/v1/analytics/overview
```

---

### GET /api/v1/analytics/trends

Returns daily candidate discovery counts for the past 30 days. Returns an empty list if no data exists — history is never fabricated.

**Response:**

```json
[
  { "date": "2025-01-10", "count": 5 },
  { "date": "2025-01-11", "count": 8 },
  { "date": "2025-01-12", "count": 3 }
]
```

```bash
curl http://localhost:8000/api/v1/analytics/trends
```

---

## AI Investigation

Investigation output explains the latest deterministic risk assessment. It does
not run detection, change a score, or determine whether a candidate is malicious.
Set `AI_PROVIDER=openai` and `AI_API_KEY` to enable live summaries. Without a
configured key, or when the provider fails, the API returns evidence-based
template output and labels it `generated_by: "template"`.

### POST /api/v1/investigation/candidates/{candidate_id}/analyze

Returns a structured explanation from the latest stored risk assessment,
signal breakdown, candidate metadata, and stored evidence. The response includes
the unchanged deterministic score and risk level, plus summary, findings,
evidence summary, recommended actions, confidence note, generation time, and
provenance (`"ai"` or `"template"`).

**Errors:**
- `404` — candidate not found
- `422` — candidate has no stored risk assessment yet

```bash
curl -X POST http://localhost:8000/api/v1/investigation/candidates/{candidate_id}/analyze
```

### POST /api/v1/investigation/candidates/{candidate_id}/ask

Answers a natural-language analyst question using the same stored candidate
context. No assessment or evidence is changed.

**Request:**

```json
{ "question": "What evidence supports the score?" }
```

`question` must contain 3–500 characters after whitespace trimming.

**Response:** includes `candidate_id`, normalized `question`, `answer`,
`generated_by` (`"ai"` or `"template"`), and `generated_at`.

**Errors:**
- `404` — candidate not found
- `422` — invalid question or candidate has no stored risk assessment

```bash
curl -X POST http://localhost:8000/api/v1/investigation/candidates/{candidate_id}/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What evidence supports the score?"}'
```

See [AI investigation security and behavior](./ai-investigation.md) for
grounding, fallback, configuration, and known limitations.

---

## Error Codes

| Code | Meaning |
|------|---------|
| 200 | OK |
| 201 | Created |
| 404 | Resource not found |
| 422 | Validation error (invalid filter value, missing required field) |
| 500 | Internal server error (stack trace not exposed) |

---

## OpenAPI Documentation

Interactive docs are available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
