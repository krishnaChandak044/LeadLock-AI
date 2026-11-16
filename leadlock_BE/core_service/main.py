"""
LeadLock AI — Core Service
REST API for tenant management, CRUD operations, analytics, and dashboard support.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import settings
from shared.redis_client import get_redis, close_redis

from .routers import tenants, customers, sessions, inventory, analytics, websocket_rt

logger = logging.getLogger("core_service")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle management."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
    )
    logger.info("🚀 LeadLock Core Service starting...")

    await get_redis()
    logger.info("✅ Redis connected")
    logger.info(f"✅ Core Service ready on port {settings.core_service_port}")

    yield

    logger.info("🛑 Shutting down Core Service...")
    await close_redis()
    logger.info("✅ Shutdown complete")


def create_app() -> FastAPI:
    """Factory function for the Core Service FastAPI application."""
    app = FastAPI(
        title="LeadLock AI — Core Service",
        description="Tenant management, CRUD, analytics, and dashboard API.",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ─────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ──────────────────────────────────────────────────────
    prefix = "/api/v1"
    app.include_router(tenants.router, prefix=prefix)
    app.include_router(customers.router, prefix=prefix)
    app.include_router(sessions.router, prefix=prefix)
    app.include_router(inventory.router, prefix=prefix)
    app.include_router(analytics.router, prefix=prefix)
    app.include_router(websocket_rt.router)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "service": "core-service"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "core_service.main:app",
        host=settings.core_service_host,
        port=settings.core_service_port,
        reload=True,
    )
