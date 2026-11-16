"""Communication Session API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SessionUpdate(BaseModel):
    """Schema for updating a session."""
    funnel_stage: str | None = Field(
        None,
        pattern=r"^(BROWSING|QUALIFYING|SCHEDULING|ESCALATED)$",
    )
    is_human_takeover: bool | None = None
    context_metadata: dict[str, Any] | None = None


class SessionResponse(BaseModel):
    """Schema for session API responses."""
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    funnel_stage: str
    is_human_takeover: bool
    context_metadata: dict[str, Any]
    updated_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageLogResponse(BaseModel):
    """Schema for message log entries."""
    id: UUID
    session_id: UUID
    direction: str
    content: str
    message_type: str
    wa_message_id: str | None
    sender_phone: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionDetailResponse(BaseModel):
    """Session with message history and customer info."""
    session: SessionResponse
    customer_name: str | None
    customer_phone: str
    customer_lead_score: str
    messages: list[MessageLogResponse]
    total_messages: int
