"""
LeadLock AI — Async Redis Client
Provides conversation caching, idempotency checks, and pub/sub.
"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from .config import settings

# ── Global Connection Pool ───────────────────────────────────────────────
_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Get or create the global Redis connection pool."""
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=50,
        )
    return _pool


async def close_redis() -> None:
    """Gracefully close the Redis connection pool."""
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


# ── Idempotency ──────────────────────────────────────────────────────────

async def check_idempotency(message_id: str) -> bool:
    """
    Atomic idempotency check using SET NX EX.
    Returns True if the message is NEW (should be processed).
    Returns False if the message is a DUPLICATE (should be ignored).
    """
    r = await get_redis()
    result = await r.set(f"msg:{message_id}", "locked", ex=86400, nx=True)
    return result is True


# ── Conversation Cache ───────────────────────────────────────────────────

CONVERSATION_TTL = 86400  # 24 hours
MAX_CONTEXT_MESSAGES = 15


async def get_conversation_history(
    tenant_id: str,
    phone_number: str,
) -> list[dict[str, Any]]:
    """Fetch cached conversation history from Redis."""
    r = await get_redis()
    key = f"session:{tenant_id}:{phone_number}"
    raw = await r.lrange(key, 0, MAX_CONTEXT_MESSAGES - 1)
    return [json.loads(item) for item in raw]


async def push_message(
    tenant_id: str,
    phone_number: str,
    message: dict[str, Any],
) -> None:
    """Push a message to the conversation cache (LPUSH + LTRIM + EXPIRE)."""
    r = await get_redis()
    key = f"session:{tenant_id}:{phone_number}"
    await r.lpush(key, json.dumps(message))
    await r.ltrim(key, 0, MAX_CONTEXT_MESSAGES - 1)
    await r.expire(key, CONVERSATION_TTL)


# ── Pub/Sub ──────────────────────────────────────────────────────────────

async def publish_event(channel: str, data: dict[str, Any]) -> None:
    """Publish an event to a Redis pub/sub channel."""
    r = await get_redis()
    await r.publish(channel, json.dumps(data))
