# BrandShield AI — Digital Risk Protection Platform

> **Hackathon project** — AI-powered social media & mobile app threat monitoring  
> Challenge: Social & App Monitoring · Deterministic Risk Engine + Case Management

---

## What It Does

BrandShield AI detects and investigates digital impersonation threats targeting a protected brand:

- **Social impersonation** — rogue accounts on Instagram, Twitter, Facebook, LinkedIn, TikTok
- **Mobile app threats** — lookalike apps on Google Play / App Store
- **Website risks** — typosquatting domains and phishing pages
- **Brand name analysis** — keyword and similarity scoring

**Key capabilities:**
- Deterministic multi-signal risk scoring (0–100, no randomness)
- Evidence-backed investigation reports with AI narrative support
- Full case management lifecycle (OPEN → INVESTIGATING → RESOLVED)
- Real-time SOC dashboard from live database

---

## Quick Start — Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- (Optional) Docker Desktop for PostgreSQL

### 1. Start the backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1       # Windows
# source .venv/bin/activate         # macOS / Linux

pip install -r requirements.txt

# Start the API (uses SQLite by default — no Docker needed)
uvicorn app.main:app --reload --port 8000
```

### 2. Seed demo data

```powershell
# In a new terminal, or use the dashboard's "Load demo dataset" button
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/demo/seed" -Method POST
```

### 3. Start the frontend

```powershell
cd frontend
npm install
npm run dev
```

### 4. Open the app

| URL | Purpose |
|-----|---------|
| http://localhost:3000 | Frontend application |
| http://localhost:8000/docs | Backend API explorer |
| http://localhost:8000/health | Backend health check |

---

## Demo Credentials

| Field | Value |
|-------|-------|
| Email | `analyst@brandshield.demo` |
| Password | `BrandShield@123` |

Or click **Enter Demo** on the landing page.

---

## LAN / Friend Access

To let another device on the same WiFi/LAN access the running app:

### Step 1 — Find your PC's local IP

**Windows PowerShell:**
```powershell
(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notmatch "^127" -and $_.PrefixOrigin -eq "Dhcp" } | Select-Object -First 1).IPAddress
```

**macOS / Linux:**
```bash
ifconfig | grep "inet " | grep -v 127 | awk '{print $2}' | head -1
```

This gives you something like `192.168.1.105`.

### Step 2 — Configure the frontend API URL

Edit `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://192.168.1.105:8000
```

Replace `192.168.1.105` with your actual LAN IP.

### Step 3 — Restart frontend with host binding

```powershell
# Allow LAN connections (Next.js listens on all interfaces by default in dev)
npm run dev -- --hostname 0.0.0.0
```

### Step 4 — Start backend bound to all interfaces

```powershell
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
```

### Step 5 — Access from the other device

On the phone or laptop:
```
http://192.168.1.105:3000
```

> **Note:** Both devices must be on the same WiFi network. Firewall rules may need to allow ports 3000 and 8000.

---

## Docker Compose (Full Stack)

Runs all three services (PostgreSQL, backend, frontend) in containers.

```bash
# Copy environment files
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local

# Start everything
docker-compose up -d

# Seed demo data (first run only)
curl -X POST http://localhost:8000/api/v1/demo/seed

# Stop
docker-compose down
```

For LAN access with Docker, set in `.env`:
```env
NEXT_PUBLIC_API_BASE_URL=http://<YOUR-LAN-IP>:8000
```

---

## Project Structure

```
brandshield-ai/
├── frontend/                  # Next.js 14 (App Router)
│   ├── app/                   # Pages and layouts
│   │   ├── (workspace)/       # Protected routes (auth required)
│   │   │   ├── dashboard/     # Executive KPI dashboard
│   │   │   ├── threats/       # Threat queue with filters
│   │   │   ├── candidates/[id]/ # Threat investigation
│   │   │   ├── analyze/       # Ad-hoc entity analysis
│   │   │   ├── brands/        # Brand portfolio
│   │   │   ├── cases/         # Case management
│   │   │   └── analytics/     # Risk analytics
│   │   ├── login/             # Authentication
│   │   └── signup/            # Account creation
│   ├── components/            # Shared UI components
│   └── lib/                   # API client, utilities
│
├── backend/                   # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── api/v1/            # REST endpoints
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic schemas
│   │   └── services/          # Detection engine, AI layer
│   └── alembic/               # Database migrations
│
├── database/                  # Docker init scripts
├── docs/                      # Technical documentation
├── docker-compose.yml
└── .env.example
```

---

## Architecture

```
Browser (Next.js)
      │
      │ /api/* → rewrites to backend
      ▼
FastAPI (port 8000)
      │
      ├─ Detection Engine  (deterministic multi-signal scoring)
      ├─ AI Investigation  (template fallback + optional OpenAI)
      ├─ Case Management   (OPEN → INVESTIGATING → RESOLVED)
      └─ Demo Data Seeder  (20 synthetic candidates, NovaPay brand)
            │
            ▼
    SQLite (dev) / PostgreSQL (production)
```

---

## Risk Score System

| Score | Level | Color |
|-------|-------|-------|
| 80–100 | CRITICAL | Red |
| 60–79 | HIGH | Orange |
| 40–59 | MEDIUM | Yellow |
| 0–39 | LOW | Green |

Scores are fully deterministic — calculated from 7 weighted signals:
- Identity similarity
- Visual / logo similarity
- Content / bio similarity
- Link / contact risk
- Account / app anomaly
- Evidence score
- Activity anomaly

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./brandshield.db` | Database connection |
| `APP_ENV` | `development` | Environment name |
| `DEMO_MODE` | `true` | Enable demo seeder endpoint |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed frontend origins |
| `AI_PROVIDER` | *(empty)* | Set to `openai` for AI narration |
| `AI_API_KEY` | *(empty)* | OpenAI API key (optional) |

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Backend API URL |

---

## Security Notes

- All demo data is **synthetic** — no real persons, accounts, or companies
- No real social media credentials are requested or stored
- Passwords are not hashed (demo auth only — not production-ready)
- API keys are loaded from `.env` files (never committed)
- CORS is configurable via `CORS_ORIGINS` environment variable

---

*BrandShield AI — Hackathon Demo · Synthetic Dataset · Deterministic Risk Engine*


### PPT link

https://gamma.app/docs/BrandShield-AI-xb0wfphoj40w8si
