"""Health check endpoint for the Edge Worker."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Liveness / readiness probe."""
    return {"status": "healthy", "service": "edge-worker"}
