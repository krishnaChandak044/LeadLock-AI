"""
LeadLock AI — Inventory Model
Schema-agnostic inventory with JSONB vertical_data for multi-vertical support.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Inventory(Base):
    __tablename__ = "inventories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="AVAILABLE"
    )  # AVAILABLE, RESERVED, SOLD
    vertical_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="inventories")  # noqa: F821

    __table_args__ = (
        Index("ix_inventory_tenant_status", "tenant_id", "status"),
        Index("ix_inventory_vertical_data", "vertical_data", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<Inventory {self.name} ({self.status})>"
