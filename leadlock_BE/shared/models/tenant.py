"""
LeadLock AI — Tenant Model
Multi-tenant business entity with AI configuration and WhatsApp session binding.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    vertical_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="GENERAL"
    )  # AUTOMOTIVE, HEALTHCARE, GENERAL
    ai_system_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    whatsapp_session_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
    openwa_base_url: Mapped[str] = mapped_column(
        String(512), nullable=False, default="http://openwa-api:2785"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    customers: Mapped[list["Customer"]] = relationship(  # noqa: F821
        back_populates="tenant", cascade="all, delete-orphan"
    )
    inventories: Mapped[list["Inventory"]] = relationship(  # noqa: F821
        back_populates="tenant", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["CommunicationSession"]] = relationship(  # noqa: F821
        back_populates="tenant", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_tenants_id_vertical", "id", "vertical_type"),
        Index("ix_tenants_wa_session", "whatsapp_session_id"),
    )

    def __repr__(self) -> str:
        return f"<Tenant {self.business_name} ({self.vertical_type})>"
