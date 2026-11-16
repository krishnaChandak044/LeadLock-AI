"""
OpenWA Webhook Payload Schema
Matches the webhook dispatch format from OpenWA-Internal's WebhookService.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class OpenWAWebhookPayload(BaseModel):
    """
    Payload received from OpenWA webhook dispatch.
    Based on OpenWA-Internal's WebhookPayload interface:
      event: string
      timestamp: string
      sessionId: string
      idempotencyKey: string
      deliveryId: string
      data: Record<string, unknown>
    """
    event: str
    timestamp: str
    sessionId: str  # noqa: N815 — matches OpenWA's camelCase
    idempotencyKey: str  # noqa: N815
    deliveryId: str  # noqa: N815
    data: dict[str, Any]

    model_config = {"populate_by_name": True}
