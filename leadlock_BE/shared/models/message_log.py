"""
LeadLock AI — Message Log Model
Immutable audit trail of all inbound and outbound messages.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class MessageLog(Base):
    __tablename__ = "message_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communication_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # INBOUND, OUTBOUND
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="text"
    )  # text, image, audio, etc.
    wa_message_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    sender_phone: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    session: Mapped["CommunicationSession"] = relationship(  # noqa: F821
        back_populates="messages"
    )

    __table_args__ = (
        Index("ix_messages_session", "session_id"),
        Index("ix_messages_tenant", "tenant_id"),
        Index("ix_messages_created", "created_at"),
        Index("ix_messages_wa_id", "wa_message_id"),
    )

    def __repr__(self) -> str:
        return f"<Message {self.direction} {self.message_type}>"
