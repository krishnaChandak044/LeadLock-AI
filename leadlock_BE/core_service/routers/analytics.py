"""
LeadLock AI — Analytics Router
Dashboard metrics and reporting endpoints.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models import Customer, CommunicationSession, MessageLog

router = APIRouter(prefix="/tenants/{tenant_id}/analytics", tags=["analytics"])


@router.get("")
async def get_analytics(
    tenant_id: UUID,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get comprehensive dashboard analytics for a tenant."""
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)

    # ── Lead Distribution ────────────────────────────────────────────
    lead_stmt = (
        select(Customer.lead_score, func.count(Customer.id))
        .where(Customer.tenant_id == tenant_id)
        .group_by(Customer.lead_score)
    )
    lead_result = await db.execute(lead_stmt)
    lead_distribution = {row[0]: row[1] for row in lead_result.all()}

    # ── Total Customers ──────────────────────────────────────────────
    total_customers = sum(lead_distribution.values())

    # ── Session Stats ────────────────────────────────────────────────
    session_stmt = (
        select(
            CommunicationSession.funnel_stage,
            func.count(CommunicationSession.id),
        )
        .where(CommunicationSession.tenant_id == tenant_id)
        .group_by(CommunicationSession.funnel_stage)
    )
    session_result = await db.execute(session_stmt)
    funnel_breakdown = {row[0]: row[1] for row in session_result.all()}
    total_sessions = sum(funnel_breakdown.values())

    # ── Active Sessions (updated in last 24h) ────────────────────────
    active_stmt = (
        select(func.count(CommunicationSession.id))
        .where(
            CommunicationSession.tenant_id == tenant_id,
            CommunicationSession.updated_at >= now - timedelta(hours=24),
        )
    )
    active_result = await db.execute(active_stmt)
    active_sessions = active_result.scalar() or 0

    # ── Messages per Day (last N days) ───────────────────────────────
    messages_stmt = (
        select(
            func.date_trunc("day", MessageLog.created_at).label("day"),
            func.count(MessageLog.id).label("count"),
        )
        .where(
            MessageLog.tenant_id == tenant_id,
            MessageLog.created_at >= start_date,
        )
        .group_by("day")
        .order_by("day")
    )
    messages_result = await db.execute(messages_stmt)
    messages_per_day = [
        {"date": row[0].isoformat() if row[0] else "", "count": row[1]}
        for row in messages_result.all()
    ]

    # ── AI vs Human Response Ratio ───────────────────────────────────
    human_sessions_stmt = (
        select(func.count(CommunicationSession.id))
        .where(
            CommunicationSession.tenant_id == tenant_id,
            CommunicationSession.is_human_takeover.is_(True),
        )
    )
    human_result = await db.execute(human_sessions_stmt)
    human_sessions = human_result.scalar() or 0

    ai_sessions = total_sessions - human_sessions

    # ── Total Messages ───────────────────────────────────────────────
    total_msg_stmt = (
        select(
            func.count(MessageLog.id),
            func.count(case((MessageLog.direction == "INBOUND", 1))),
            func.count(case((MessageLog.direction == "OUTBOUND", 1))),
        )
        .where(MessageLog.tenant_id == tenant_id)
    )
    total_msg_result = await db.execute(total_msg_stmt)
    total_msg_row = total_msg_result.one()

    return {
        "overview": {
            "total_customers": total_customers,
            "total_sessions": total_sessions,
            "active_sessions_24h": active_sessions,
            "total_messages": total_msg_row[0],
            "inbound_messages": total_msg_row[1],
            "outbound_messages": total_msg_row[2],
        },
        "lead_distribution": {
            "COLD": lead_distribution.get("COLD", 0),
            "WARM": lead_distribution.get("WARM", 0),
            "HOT": lead_distribution.get("HOT", 0),
        },
        "funnel_breakdown": {
            "BROWSING": funnel_breakdown.get("BROWSING", 0),
            "QUALIFYING": funnel_breakdown.get("QUALIFYING", 0),
            "SCHEDULING": funnel_breakdown.get("SCHEDULING", 0),
            "ESCALATED": funnel_breakdown.get("ESCALATED", 0),
        },
        "response_ratio": {
            "ai_managed": ai_sessions,
            "human_managed": human_sessions,
        },
        "messages_per_day": messages_per_day,
    }
