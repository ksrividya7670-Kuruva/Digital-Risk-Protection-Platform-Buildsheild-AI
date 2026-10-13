"""
BrandShield AI — FastAPI Application Entry Point

This module creates and configures the FastAPI application.
All routers are registered here.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.health import router as health_router
from app.api.v1.detection import router as detection_router
from app.api.v1.demo import router as demo_router
from app.api.v1.brands import router as brands_router
from app.api.v1.candidates import router as candidates_router
from app.api.v1.threats import router as threats_router
from app.api.v1.cases import router as cases_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.investigation import router as investigation_router
from app.db.database import create_all_tables
import app.models  # noqa: F401 — ensures all ORM models are registered with metadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Runs startup logic before the app accepts requests,
    and teardown logic when the app shuts down.
    """
    # Startup
    print(f"🛡  {settings.app_name} v{settings.app_version} starting up...")
    print(f"   Environment : {settings.app_env}")
    print(f"   Database    : {settings.database_url.split('@')[-1] if '@' in settings.database_url else settings.database_url}")
    print(f"   Demo mode   : {settings.demo_mode}")
    print(f"   CORS origins: {settings.cors_origins_list}")

    # Auto-create tables for SQLite dev. For Postgres, use Alembic instead.
    if settings.database_url.startswith("sqlite"):
        await create_all_tables()
        print("   DB tables   : created (SQLite)")

    yield
    # Shutdown
    print(f"🛡  {settings.app_name} shutting down.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Digital Risk Protection Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# EMERGENCY CORS FIX
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
# Health check (no prefix — available at /health and /health/db)
app.include_router(health_router, tags=["Health"])

# Detection engine
app.include_router(
    detection_router,
    prefix="/api/v1/detection",
    tags=["Detection"],
)

# Demo data (only active when DEMO_MODE=true)
app.include_router(
    demo_router,
    prefix="/api/v1/demo",
    tags=["Demo"],
)

app.include_router(brands_router, prefix="/api/v1/brands", tags=["Brands"])
app.include_router(candidates_router, prefix="/api/v1/candidates", tags=["Candidates"])
app.include_router(threats_router, prefix="/api/v1/threats", tags=["Threats"])
app.include_router(cases_router, prefix="/api/v1/cases", tags=["Cases"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(investigation_router, prefix="/api/v1/investigation", tags=["Investigation"])


@app.get("/", include_in_schema=False)
async def root():
    """Root redirect hint."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "docs": "/docs",
        "health": "/health",
    }
