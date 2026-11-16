"""
LeadLock AI — Edge Worker Service
High-concurrency async FastAPI service for webhook ingestion,
AI conversation processing, and outbound messaging.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import settings
from shared.redis_client import get_redis, close_redis

from .routers import webhook, health

logger = logging.getLogger("edge_worker")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle management."""
    # ── Startup ──────────────────────────────────────────────────────
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
    )
    logger.info("🚀 LeadLock Edge Worker starting...")

    # Warm up Redis connection
    await get_redis()
    logger.info("✅ Redis connected")

    logger.info(f"✅ Edge Worker ready on port {settings.edge_worker_port}")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────
    logger.info("🛑 Shutting down Edge Worker...")
    await close_redis()
    logger.info("✅ Shutdown complete")


def create_app() -> FastAPI:
    """Factory function for the Edge Worker FastAPI application."""
    app = FastAPI(
        title="LeadLock AI — Edge Worker",
        description="Webhook ingestion, AI conversation engine, and outbound messaging service.",
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
    app.include_router(health.router)
    app.include_router(webhook.router, prefix="/api/v1")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "edge_worker.main:app",
        host=settings.edge_worker_host,
        port=settings.edge_worker_port,
        reload=True,
    )
