"""
LeadLock AI — Session Management Router
Session CRUD, human takeover, and message history.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.database import get_db
from shared.models import CommunicationSession, MessageLog, Customer
from shared.schemas import SessionResponse, SessionUpdate, SessionDetailResponse, MessageLogResponse
from shared.redis_client import publish_event

router = APIRouter(prefix="/tenants/{tenant_id}/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    tenant_id: UUID,
    funnel_stage: str | None = Query(None, pattern=r"^(BROWSING|QUALIFYING|SCHEDULING|ESCALATED)$"),
    is_human_takeover: bool | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[CommunicationSession]:
    """List sessions for a tenant with filtering."""
    stmt = (
        select(CommunicationSession)
        .where(CommunicationSession.tenant_id == tenant_id)
        .order_by(CommunicationSession.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if funnel_stage:
        stmt = stmt.where(CommunicationSession.funnel_stage == funnel_stage)
    if is_human_takeover is not None:
        stmt = stmt.where(CommunicationSession.is_human_takeover == is_human_takeover)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    tenant_id: UUID,
    session_id: UUID,
    message_limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> SessionDetailResponse:
    """Get session details with message history."""
    # Fetch session
    stmt = select(CommunicationSession).where(
        CommunicationSession.id == session_id,
        CommunicationSession.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Fetch customer
    cust_stmt = select(Customer).where(Customer.id == session.customer_id)
    cust_result = await db.execute(cust_stmt)
    customer = cust_result.scalar_one_or_none()

    # Fetch messages
    msg_stmt = (
        select(MessageLog)
        .where(MessageLog.session_id == session_id)
        .order_by(MessageLog.created_at.asc())
        .limit(message_limit)
    )
    msg_result = await db.execute(msg_stmt)
    messages = msg_result.scalars().all()

    return SessionDetailResponse(
        session=SessionResponse.model_validate(session),
        customer_name=customer.name if customer else None,
        customer_phone=customer.phone_number if customer else "unknown",
        customer_lead_score=customer.lead_score if customer else "COLD",
        messages=[MessageLogResponse.model_validate(m) for m in messages],
        total_messages=len(messages),
    )


@router.put("/{session_id}/takeover", response_model=SessionResponse)
async def takeover_session(
    tenant_id: UUID,
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> CommunicationSession:
    """Take over a session (switch from AI to human control)."""
    stmt = select(CommunicationSession).where(
        CommunicationSession.id == session_id,
        CommunicationSession.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session.is_human_takeover = True
    session.funnel_stage = "ESCALATED"
    await db.commit()
    await db.refresh(session)

    # Publish real-time event
    await publish_event(
        f"session:{session_id}:events",
        {
            "type": "session.takeover",
            "session_id": str(session_id),
            "mode": "human",
        },
    )

    return session


@router.put("/{session_id}/release", response_model=SessionResponse)
async def release_session(
    tenant_id: UUID,
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> CommunicationSession:
    """Release a session back to AI control."""
    stmt = select(CommunicationSession).where(
        CommunicationSession.id == session_id,
        CommunicationSession.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session.is_human_takeover = False
    session.funnel_stage = "BROWSING"
    await db.commit()
    await db.refresh(session)

    # Publish real-time event
    await publish_event(
        f"session:{session_id}:events",
        {
            "type": "session.released",
            "session_id": str(session_id),
            "mode": "ai",
        },
    )

    return session
