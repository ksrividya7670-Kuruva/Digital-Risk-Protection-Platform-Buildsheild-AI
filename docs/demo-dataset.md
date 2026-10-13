# BrandShield AI — Synthetic Demo Dataset

## ⚠️ Synthetic Data Policy

**ALL data in this dataset is completely fictional.**

- No real persons, companies, or organizations are referenced.
- No real social media accounts or URLs are used.
- All domains use the IANA-reserved `.example` TLD (cannot be real websites).
- All evidence records are marked `is_synthetic = True`.
- Risk scores are produced by the deterministic detection engine — never hardcoded.

This dataset exists solely for hackathon demonstration purposes.

---

## Fictional Brand: NovaPay

| Field | Value |
|---|---|
| Name | NovaPay |
| Domain | `novapay.example` (IANA reserved) |
| Industry | Fintech / Digital Payments |
| Official Twitter | `@novapayhq` |
| Official Android | `com.novapay.wallet` |
| Official Developer | NovaPay Technologies Inc. |

---

## Dataset Overview

| Category | Count |
|---|---|
| Total candidates | 20 |
| Social profiles | 15 |
| Mobile apps | 8 |
| Expected CRITICAL | 2 |
| Expected HIGH | 4 |
| Expected MEDIUM | 5 |
| Expected LOW | 9 |

> Note: "Expected" tiers are informational targets. Actual scores are determined by the detection engine and may vary slightly as the engine is tuned.

---

## Social Profile Scenarios (15 candidates)

| Label | Platform | Username | Expected Tier | Scenario |
|---|---|---|---|---|
| SC-01 | Twitter | NovaPay_Support | CRITICAL | Fake support account, lookalike domain, young account |
| SC-02 | Instagram | novapay.official | CRITICAL | Fake official account, bio match, lookalike domain |
| SC-03 | Facebook | NovaPay.Promotions | HIGH | Fake promo page, urgency language |
| SC-04 | Twitter | novapayhelpdesk | HIGH | Fake helpdesk, lookalike domain |
| SC-05 | Twitter | N0vaPay | HIGH | Leet-speak substitution, fake wallet |
| SC-06 | Instagram | novapay_india | HIGH | Fake regional account |
| SC-07 | Twitter | novap4y | MEDIUM | Typosquat, declares unofficial |
| SC-08 | Facebook | NovaPay.Verify | MEDIUM | Credential phishing style |
| SC-09 | TikTok | novapaynews | MEDIUM | News aggregator, explicit disclaimer |
| SC-10 | Twitter | nova_pay_backup | MEDIUM | Claims to be backup account |
| SC-11 | Twitter | novapayfans | LOW | Fan community, explicit disclaimer |
| SC-12 | LinkedIn | fintech-daily-news | LOW | Independent news site |
| SC-13 | Facebook | DigitalPaymentsDiscussion | LOW | Community discussion group |
| SC-14 | Twitter | novapaywatch | LOW | Service watchdog, unrelated domain |
| SC-15 | YouTube | HowToUsePay | LOW | Educational tutorials channel |

---

## Mobile App Scenarios (8 candidates)

| Label | Store | Package Name | Expected Tier | Scenario |
|---|---|---|---|---|
| APP-01 | Google Play | com.example.novapay.fakewallet | CRITICAL | Exact name match, unrelated developer |
| APP-02 | App Store | com.securepay.novapay.unofficial | CRITICAL | Brand name in title, developer mismatch, logo similarity |
| APP-03 | Google Play | com.example.rewards.novapay | HIGH | Fake rewards app, developer mismatch |
| APP-04 | App Store | com.support.novapay.help | HIGH | Fake support app, developer mismatch |
| APP-05 | Google Play | com.thirdparty.novapaymobile | MEDIUM | Explicit disclaimer, older app |
| APP-06 | App Store | com.example.novapay.official | MEDIUM | Claims official, developer mismatch |
| APP-07 | Google Play | com.guides.payments.novapayguide | LOW | Unofficial guide, clearly labeled |
| APP-08 | App Store | com.community.novapayforum | LOW | Community forum, long history |

---

## Threat Scenarios — Detailed

### CRITICAL Threats

**SC-01 — Fake Twitter Support Account**
- Username `NovaPay_Support` highly similar to official handle `novapayhq`
- Links to lookalike domain `novapay-support.example`
- Account only 11 days old
- Claims to be official support
- 3 CRITICAL/HIGH evidence items

**APP-01 — Fake Android Wallet**
- App name `NovaPay Wallet` identical to official app name
- Developer `FinanceApps Studio` completely unrelated to `NovaPay Technologies Inc.`
- Developer uses free email domain
- App published 12 days ago

### HIGH Threats

**SC-03 — Fake Promotions Page**: Brand name in username, promotional scam language, lookalike domain

**SC-04 — Helpdesk Impersonation**: Username follows `brand + helpdesk` pattern, contact email on lookalike domain

**SC-05 — Leet-Speak Substitution**: `N0vaPay` → leet-normalized to `NovaPay` (95% similarity)

**SC-06 — Fake Regional Account**: `novapay_india` geographic impersonation pattern

### LOW Threats (Benign Examples)

These candidates demonstrate that BrandShield AI does **not** flag every brand mention:

- **SC-11 NovaPay Fans**: Explicitly states "not affiliated", 420-day-old account, no domain risk
- **SC-12 Fintech Daily News**: Independent news outlet, NovaPay is one of many mentioned brands
- **SC-13 Digital Payments Discussion**: Community group, completely unrelated username
- **SC-14 NovaPay Watch**: Service watchdog, unrelated domain, long history
- **SC-15 How To Use Digital Payments**: Educational YouTube, NovaPay mentioned among many products
- **APP-07 NovaPay Guide**: Unofficial guide, explicitly labeled, high rating (4.6), 550 days old
- **APP-08 NovaPay Community**: Community forum, transparent disclaimer, established (730 days)

---

## How to Seed the Dataset

### Via command line (from `backend/` directory, venv activated):
```bash
python -m app.demo.seed_demo
```

To wipe and re-seed:
```bash
python -m app.demo.seed_demo --reset
```

### Via API (server must be running):
```bash
# Seed (idempotent)
curl -X POST http://localhost:8000/api/v1/demo/seed

# Reset and re-seed
curl -X POST http://localhost:8000/api/v1/demo/reset

# Check status
curl http://localhost:8000/api/v1/demo/status
```

Requires `DEMO_MODE=true` in `backend/.env`.

---

## Idempotency Guarantee

The seeder detects existing records using a label marker embedded in display names (e.g., `[SC-01]`). Running the seeder multiple times will not create duplicate records.

---

## Evidence Integrity Rules

1. Every evidence record has `is_synthetic = True`
2. Evidence values are plausible string representations of detected signals
3. Evidence descriptions explain what was observed — no invented claims
4. Risk scores come from the detection engine, not from evidence fields directly

---

*BrandShield AI Demo Dataset — Synthetic only. National Hackathon MVP.*
