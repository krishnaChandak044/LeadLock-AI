"""
LeadLock AI — OpenWA HTTP Client
Sends messages through the OpenWA gateway with anti-ban rate limiting.
"""

from __future__ import annotations

import asyncio
import logging
import random

import httpx

from shared.config import settings

logger = logging.getLogger("edge_worker.openwa_client")


class OpenWAClient:
    """HTTP client for OpenWA outbound messaging with anti-ban pacing."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            headers: dict[str, str] = {
                "Content-Type": "application/json",
                "User-Agent": "LeadLock-AI/1.0",
            }
            if settings.openwa_api_key:
                headers["X-API-Key"] = settings.openwa_api_key

            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers=headers,
                follow_redirects=True,
            )
        return self._client

    async def send_text_message(
        self,
        base_url: str,
        session_id: str,
        chat_id: str,
        text: str,
    ) -> dict[str, str]:
        """
        Send a text message through OpenWA.
        Includes anti-ban pacing delay (1.5–3.5s).
        """
        # ── Anti-Ban Pacing ──────────────────────────────────────────
        delay = random.uniform(1.5, 3.5)
        logger.debug(f"Pacing delay: {delay:.1f}s before sending")
        await asyncio.sleep(delay)

        # ── Send Message ─────────────────────────────────────────────
        client = await self._get_client()
        url = f"{base_url}/api/sessions/{session_id}/messages/send-text"

        payload = {
            "chatId": chat_id,
            "text": text,
        }

        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()
            logger.info(f"Message sent to {chat_id} via session {session_id}")
            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                f"OpenWA API error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except httpx.RequestError as e:
            logger.error(f"OpenWA connection error: {e}")
            raise

    async def send_typing_indicator(
        self,
        base_url: str,
        session_id: str,
        chat_id: str,
        duration_ms: int = 3000,
    ) -> None:
        """
        Send typing indicator to simulate human-like behavior.
        Duration is based on response length approximation.
        """
        # This is a best-effort operation — don't fail the main flow
        try:
            client = await self._get_client()
            url = f"{base_url}/api/sessions/{session_id}/chats/{chat_id}/typing"
            await client.post(url, json={"duration": duration_ms})
        except Exception as e:
            logger.debug(f"Typing indicator failed (non-critical): {e}")

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
