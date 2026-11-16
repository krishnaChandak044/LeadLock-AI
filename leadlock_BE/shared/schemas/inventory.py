"""Inventory API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class InventoryCreate(BaseModel):
    """Schema for creating an inventory item."""
    name: str = Field(..., min_length=1, max_length=255)
    status: str = Field(
        default="AVAILABLE",
        pattern=r"^(AVAILABLE|RESERVED|SOLD)$",
    )
    vertical_data: dict[str, Any] = Field(default_factory=dict)


class InventoryUpdate(BaseModel):
    """Schema for updating an inventory item."""
    name: str | None = Field(None, min_length=1, max_length=255)
    status: str | None = Field(
        None,
        pattern=r"^(AVAILABLE|RESERVED|SOLD)$",
    )
    vertical_data: dict[str, Any] | None = None


class InventoryResponse(BaseModel):
    """Schema for inventory API responses."""
    id: UUID
    tenant_id: UUID
    name: str
    status: str
    vertical_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InventoryBulkCreate(BaseModel):
    """Schema for bulk creating inventory items."""
    items: list[InventoryCreate] = Field(..., min_length=1, max_length=500)
