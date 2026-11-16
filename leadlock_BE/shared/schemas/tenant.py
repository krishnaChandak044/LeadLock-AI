"""Tenant API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    """Schema for creating a new tenant."""
    business_name: str = Field(..., min_length=1, max_length=255)
    vertical_type: str = Field(
        default="GENERAL",
        pattern=r"^(AUTOMOTIVE|HEALTHCARE|GENERAL)$",
    )
    ai_system_prompt: str = Field(default="")
    whatsapp_session_id: str | None = None
    openwa_base_url: str = Field(default="http://openwa-api:2785")


class TenantUpdate(BaseModel):
    """Schema for updating a tenant."""
    business_name: str | None = Field(None, min_length=1, max_length=255)
    vertical_type: str | None = Field(
        None,
        pattern=r"^(AUTOMOTIVE|HEALTHCARE|GENERAL)$",
    )
    ai_system_prompt: str | None = None
    whatsapp_session_id: str | None = None
    openwa_base_url: str | None = None
    is_active: bool | None = None


class TenantResponse(BaseModel):
    """Schema for tenant API responses."""
    id: UUID
    business_name: str
    vertical_type: str
    ai_system_prompt: str
    whatsapp_session_id: str | None
    openwa_base_url: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
