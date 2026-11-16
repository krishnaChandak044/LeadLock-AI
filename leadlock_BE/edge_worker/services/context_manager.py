"""
LeadLock AI — Conversation Context Manager
Manages conversation history with Redis cache and PostgreSQL fallback.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import MessageLog
from shared.redis_client import get_conversation_history, MAX_CONTEXT_MESSAGES

logger = logging.getLogger("edge_worker.context_manager")


class ContextManager:
    """Builds conversation context from Redis cache with DB fallback."""

    async def build_context(
        self,
        db: AsyncSession,
        tenant_id: str,
        phone_number: str,
    ) -> list[dict[str, str]]:
        """
        Build conversation context for the LLM.

        1. Try Redis cache first (fast, last 15 messages)
        2. Fall back to PostgreSQL if cache is empty
        3. Return messages in chronological order (oldest first)
        """

        # ── 1. Try Redis Cache ───────────────────────────────────────
        cached_messages = await get_conversation_history(tenant_id, phone_number)

        if cached_messages:
            # Redis stores newest first (LPUSH), reverse for chronological order
            cached_messages.reverse()
            logger.debug(
                f"Context loaded from Redis: {len(cached_messages)} messages"
            )
            return cached_messages

        # ── 2. Fallback to PostgreSQL ────────────────────────────────
        logger.debug("Redis cache miss — falling back to PostgreSQL")
        return await self._load_from_database(db, tenant_id, phone_number)

    async def _load_from_database(
        self,
        db: AsyncSession,
        tenant_id: str,
        phone_number: str,
    ) -> list[dict[str, str]]:
        """Load last 5 messages from the database as context fallback."""
        # Find recent messages for this customer from the message_logs table
        stmt = (
            select(MessageLog)
            .where(
                MessageLog.tenant_id == tenant_id,
                MessageLog.sender_phone == phone_number,
            )
            .order_by(MessageLog.created_at.desc())
            .limit(5)
        )

        result = await db.execute(stmt)
        messages = result.scalars().all()

        if not messages:
            return []

        # Convert to LLM message format (oldest first)
        context: list[dict[str, str]] = []
        for msg in reversed(messages):
            role = "user" if msg.direction == "INBOUND" else "assistant"
            context.append({"role": role, "content": msg.content})

        logger.debug(f"Context loaded from DB: {len(context)} messages")
        return context
