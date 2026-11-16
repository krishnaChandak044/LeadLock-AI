"""Customer API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    """Schema for creating a customer."""
    phone_number: str = Field(..., min_length=1, max_length=32)
    name: str | None = Field(None, max_length=255)
    lead_score: str = Field(
        default="COLD",
        pattern=r"^(COLD|WARM|HOT)$",
    )


class CustomerUpdate(BaseModel):
    """Schema for updating a customer."""
    name: str | None = Field(None, max_length=255)
    lead_score: str | None = Field(
        None,
        pattern=r"^(COLD|WARM|HOT)$",
    )


class CustomerResponse(BaseModel):
    """Schema for customer API responses."""
    id: UUID
    tenant_id: UUID
    phone_number: str
    name: str | None
    lead_score: str
    last_contacted_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
