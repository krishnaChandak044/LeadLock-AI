"""
LeadLock AI — Customer Model
Lead entity with E.164 phone number, lead scoring, and tenant isolation.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    phone_number: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # E.164 format
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lead_score: Mapped[str] = mapped_column(
        String(20), nullable=False, default="COLD"
    )  # COLD, WARM, HOT
    last_contacted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="customers")  # noqa: F821
    sessions: Mapped[list["CommunicationSession"]] = relationship(  # noqa: F821
        back_populates="customer", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "phone_number", name="uq_customer_tenant_phone"),
        Index("ix_customers_tenant_phone", "tenant_id", "phone_number"),
        Index("ix_customers_lead_score", "tenant_id", "lead_score"),
    )

    def __repr__(self) -> str:
        return f"<Customer {self.phone_number} ({self.lead_score})>"
