"""
Health check endpoint.
Returns service status. Used for:
- Docker health checks
- Load balancer probes
- Developer verification that the API is running
"""

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db.database import get_db
from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check — confirms the API process is running.
    Does not check database connectivity.
    """
    return {
        "status": "ok",
        "service": "brandshield-api",
        "version": settings.app_version,
        "environment": settings.app_env,
    }


@router.get("/health/db")
async def health_check_db(db: AsyncSession = Depends(get_db)):
    """
    Deep health check — confirms the API can reach the database.
    """
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        db_status = f"error: {str(exc)}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "service": "brandshield-api",
        "database": db_status,
    }
