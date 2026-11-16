"""
LeadLock AI — WebSocket Router for Real-Time Updates
Subscribes to Redis pub/sub for live session streaming.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from shared.redis_client import get_redis

logger = logging.getLogger("core_service.websocket")

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/sessions/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str) -> None:
    """
    WebSocket endpoint for real-time session monitoring.
    Subscribes to Redis pub/sub channel for the given session.
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for session: {session_id}")

    redis = await get_redis()
    pubsub = redis.pubsub()
    channel = f"session:{session_id}:events"

    try:
        await pubsub.subscribe(channel)

        while True:
            # Check for Redis messages
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )

            if message and message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                await websocket.send_text(data)

            # Small delay to prevent busy-waiting
            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
