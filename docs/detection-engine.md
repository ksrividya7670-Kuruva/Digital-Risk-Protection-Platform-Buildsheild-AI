# BrandShield AI — Detection Engine

## Overview

The BrandShield AI detection engine is a **deterministic, rule-based risk scoring system** that evaluates external candidates (social profiles and mobile applications) for potential brand impersonation.

**Key principle:** Every numerical risk score is produced by the deterministic engine. The LLM layer only explains and summarizes findings — it never calculates or modifies scores.

---

## Architecture

```
Candidate + Brand + Evidence (from DB)
              ↓
        CandidateBundle
              ↓
    ┌─────────────────────────────┐
    │       Risk Engine           │
    │  (risk_engine.py)           │
    │                             │
    │  identity_similarity   25%  │
    │  visual_similarity     20%  │
    │  content_similarity    15%  │
    │  link_risk             15%  │
    │  account_anomaly       10%  │
    │  evidence_score        10%  │
    │  activity_anomaly       5%  │
    └─────────────────────────────┘
              ↓
       DetectionResult
    (score, level, signals, reasons, explanation)
              ↓
     RiskAssessment (persisted to DB)
```

---

## The Seven Signals

### 1. Identity Similarity (weight: 25%)

Compares the candidate's username and display name against the brand's official handles and name.

**Techniques:**
- Levenshtein edit distance (pure Python)
- Character n-gram Jaccard similarity
- Token overlap ratio
- Impersonation affix detection (`brand + "support"`, `brand + "official"`, etc.)
- Leet-speak normalization (`0 → o`, `1 → i`, `3 → e`)
- Brand name embedded in longer username

**Returns:** 0.0–1.0 raw score, max contribution 25 points.

---

### 2. Visual / Logo Similarity (weight: 20%)

Compares the candidate's icon/image against the brand logo.

**Techniques:**
- Perceptual hash comparison (Hamming distance on hex-encoded hashes)
- Evidence record-backed scores (from stored DB evidence)
- Returns 0 when no visual data is available (never inflates score from missing data)

**MVP limitation:** Full image download and hashing requires Pillow + imagehash (added in a later step). The architecture supports plug-in replacement without interface changes.

**Returns:** 0.0–1.0 raw score, max contribution 20 points.

---

### 3. Content / Bio Similarity (weight: 15%)

Compares the candidate's bio or description against the brand's official description.

**Techniques:**
- Jaccard token similarity
- Token overlap ratio
- Character n-gram similarity
- Brand name mention detection
- Suspicious claim detection: "official", "support", "verified", "customer care", etc.
- Keyword overlap with brand vocabulary

**Returns:** 0.0–1.0 raw score, max contribution 15 points.

---

### 4. Link / Contact Risk (weight: 15%)

Structural analysis of URLs, domains, and contact information. **No HTTP requests are made.**

**Checks:**
- Official domain match/mismatch
- Lookalike domain (brand name in domain, but different TLD or additions)
- Suspicious TLD (`.xyz`, `.tk`, `.ml`, etc.)
- URL shortener detection
- Suspicious keywords in URL path
- Free email provider for "official" contact
- Developer email mismatch (mobile apps)
- Package name brand-squatting

**Returns:** 0.0–1.0 raw score (max risk component), max contribution 15 points.

---

### 5. Account / App Anomaly (weight: 10%)

Detects suspicious patterns in candidate metadata.

**Social profile signals:**
- Very young account age (< 7 days → 0.90, < 30 days → 0.70)
- Suspicious follower/following ratio
- Claims to be official but unverified and has few followers
- Empty bio on account claiming official status

**Mobile app signals:**
- Developer name mismatch with official developer
- Very low install count despite claiming official status
- Very new app
- Version `1.0.0` on a claimed official app

**Rule:** Missing data is never treated as evidence of risk.

**Returns:** 0.0–1.0 raw score, max contribution 10 points.

---

### 6. Evidence Score (weight: 10%)

Aggregates risk from evidence records already stored in the database.

**Rules:**
- Returns 0 if no evidence records exist
- Severity mapping: CRITICAL → 1.0, HIGH → 0.75, MEDIUM → 0.50, LOW → 0.25
- Blends severity with `similarity_score` when available
- Count bonus: more independent evidence items raise the signal (saturates at 5+)

**Critical rule:** The engine never manufactures evidence. This signal is zero until evidence is explicitly stored.

**Returns:** 0.0–1.0 raw score, max contribution 10 points.

---

### 7. Activity Anomaly (weight: 5%)

Detects suspicious activity patterns.

**Signals:**
- Rapid follower growth rate
- Follow-farming pattern (new account, high following, low followers)
- App install spike in first days
- Urgency/pressure language in bio

**Rule:** Returns 0 with explicit message when no activity data is available.

**Returns:** 0.0–1.0 raw score, max contribution 5 points.

---

## Scoring Formula

```
total_score = Σ (signal.raw_score × signal.weight)

           = identity  × 25
           + visual    × 20
           + content   × 15
           + link      × 15
           + anomaly   × 10
           + evidence  × 10
           + activity  ×  5

Range: 0–100 (integer, rounded)
```

> **Note:** These weights are an **initial engineering proposal for the hackathon MVP**. They are not prescribed by the hackathon challenge specification. They should be calibrated with real-world data before production deployment.

---

## Risk Levels

| Score Range | Level    |
|-------------|----------|
| 80–100      | CRITICAL |
| 60–79       | HIGH     |
| 40–59       | MEDIUM   |
| 0–39        | LOW      |

---

## Confidence (Independent of Risk Score)

Confidence reflects **how strongly the available evidence supports the assessment** — not how suspicious the candidate appears.

```
confidence = 0.40 × (signals_fired / total_signals)
           + 0.40 × (average_raw_score_of_fired_signals)
           + 0.20 × (evidence_count_factor)
```

**Example:** A CRITICAL score driven by one strong identity match but no evidence records → confidence = moderate. A MEDIUM score backed by 4 independent signals with DB evidence → confidence = high.

---

## Explainability

Every `DetectionResult` contains:

1. **`signals[]`** — per-signal breakdown with `signal_name`, `raw_score`, `weight`, `weighted_score`, `reason`, `metadata`
2. **`reasons[]`** — top 5 firing signals with human-readable reasons
3. **`explanation`** — one-sentence deterministic summary

**Rule:** The explanation is generated from calculated signal values only. No LLM is involved. No evidence is invented.

---

## Limitations (MVP)

1. **Visual similarity** — currently uses hash comparison or evidence-backed scores. Full perceptual hashing (imagehash) is not installed at foundation stage.
2. **Text similarity** — uses pure Python Jaccard/edit distance. Does not use semantic embeddings.
3. **No live data** — engine operates on supplied candidate data only. No web scraping, no API calls.
4. **English optimized** — normalization and keyword lists are primarily English.

---

## Extension Points

The architecture is designed for incremental improvement:

| Component | Current | Future |
|-----------|---------|--------|
| Text similarity | Jaccard + edit distance | TF-IDF, sentence embeddings |
| Visual similarity | Hash comparison | imagehash, CLIP embeddings |
| Identity signals | Username string matching | Phonetic matching, multilingual |
| Link risk | Static domain analysis | Domain age lookup, VirusTotal |
| Signal weights | Fixed constants | Calibrated ML model |
| Data source | Synthetic / manual | Live social API, store API |

---

*BrandShield AI — Detection Engine documentation. Last updated: Step 3.*
