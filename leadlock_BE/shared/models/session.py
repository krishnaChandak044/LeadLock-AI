"""
LeadLock AI — Communication Session Model
Tracks conversation lifecycle, funnel stages, and human takeover state.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class CommunicationSession(Base):
    __tablename__ = "communication_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    funnel_stage: Mapped[str] = mapped_column(
        String(50), nullable=False, default="BROWSING"
    )  # BROWSING, QUALIFYING, SCHEDULING, ESCALATED
    is_human_takeover: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    context_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="sessions")  # noqa: F821
    customer: Mapped["Customer"] = relationship(back_populates="sessions")  # noqa: F821
    messages: Mapped[list["MessageLog"]] = relationship(  # noqa: F821
        back_populates="session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_sessions_tenant_customer", "tenant_id", "customer_id"),
        Index("ix_sessions_funnel", "tenant_id", "funnel_stage"),
        Index("ix_sessions_updated", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<Session {self.id} stage={self.funnel_stage}>"
