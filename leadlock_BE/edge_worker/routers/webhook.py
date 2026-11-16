"""
LeadLock AI — OpenWA Webhook Ingestion Endpoint
Core webhook processor with idempotency, AI conversation, and outbound messaging.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models import Tenant, Customer, CommunicationSession, MessageLog
from shared.schemas import OpenWAWebhookPayload
from shared.redis_client import check_idempotency, push_message, publish_event, get_conversation_history

from ..services.ai_engine import ConversationEngine
from ..services.openwa_client import OpenWAClient
from ..services.context_manager import ContextManager

logger = logging.getLogger("edge_worker.webhook")

router = APIRouter(tags=["webhook"])

# ── Singleton services (lazy-init) ───────────────────────────────────
_ai_engine: ConversationEngine | None = None
_openwa_client: OpenWAClient | None = None
_context_manager: ContextManager | None = None


def get_ai_engine() -> ConversationEngine:
    global _ai_engine
    if _ai_engine is None:
        _ai_engine = ConversationEngine()
    return _ai_engine


def get_openwa_client() -> OpenWAClient:
    global _openwa_client
    if _openwa_client is None:
        _openwa_client = OpenWAClient()
    return _openwa_client


def get_context_manager() -> ContextManager:
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager


@router.post("/webhook/openwa")
async def receive_openwa_webhook(
    payload: OpenWAWebhookPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Receives webhook dispatches from OpenWA.

    Flow:
    1. Idempotency check (Redis SET NX EX 86400)
    2. Resolve tenant by OpenWA sessionId
    3. Upsert customer record
    4. Get/create communication session
    5. Check human takeover status
    6. Build conversation context
    7. Run AI conversation engine
    8. Send response via OpenWA
    9. Log all messages
    """

    # ── 1. Only process message.received events ──────────────────────
    if payload.event != "message.received":
        logger.debug(f"Ignoring event: {payload.event}")
        return {"status": "ignored", "reason": f"event '{payload.event}' not processed"}

    # ── 2. Idempotency check ─────────────────────────────────────────
    message_id = payload.data.get("id", payload.idempotencyKey)
    if not message_id:
        logger.warning("No message_id found in payload")
        return {"status": "ignored", "reason": "no message_id"}

    is_new = await check_idempotency(str(message_id))
    if not is_new:
        logger.info(f"Duplicate message ignored: {message_id}")
        return {"status": "duplicate"}

    # ── 3. Skip messages sent by us ──────────────────────────────────
    if payload.data.get("fromMe", False):
        logger.debug("Ignoring our own outbound message")
        return {"status": "ignored", "reason": "outbound message"}

    # ── 4. Resolve tenant ────────────────────────────────────────────
    stmt = select(Tenant).where(
        Tenant.whatsapp_session_id == payload.sessionId,
        Tenant.is_active.is_(True),
    )
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    if tenant is None:
        logger.warning(f"No active tenant for session: {payload.sessionId}. Falling back to first active tenant.")
        stmt_fallback = select(Tenant).where(Tenant.is_active.is_(True)).limit(1)
        fallback_result = await db.execute(stmt_fallback)
        tenant = fallback_result.scalar_one_or_none()

    if tenant is None:
        logger.error("No active tenants found in the database.")
        return {"status": "error", "reason": "no matching tenant"}

    # ── 5. Extract sender info ───────────────────────────────────────
    phone_number: str = str(
        payload.data.get("phoneNumber")
        or payload.data.get("from", "")
    )
    # Clean phone number (remove @c.us suffix if present)
    phone_number = phone_number.split("@")[0].strip()
    if not phone_number:
        logger.warning("No phone number in payload")
        return {"status": "error", "reason": "no phone number"}

    message_body: str = str(payload.data.get("body", ""))
    message_type: str = str(payload.data.get("type", "text"))
    sender_name: str | None = payload.data.get("notifyName") or payload.data.get("pushName")  # type: ignore[assignment]

    # ── Greeting Filter (Only for first message) ──────────────────────
    history = await get_conversation_history(str(tenant.id), phone_number)
    if not history:
        msg_lower = message_body.strip().lower()
        valid_greetings = ["hi", "hii", "hello", "hey"]
        
        # Check if the message contains any of the greeting words
        has_greeting = any(word in msg_lower.split() for word in valid_greetings) or msg_lower in valid_greetings
        
        if not has_greeting:
            logger.info(f"Ignoring non-greeting message (first message must be a greeting): {message_body}")
            return {"status": "ignored", "reason": "not a greeting"}

    # ── 6. Upsert customer ───────────────────────────────────────────
    customer = await _upsert_customer(
        db, tenant.id, phone_number, sender_name
    )

    # ── 7. Get or create session ─────────────────────────────────────
    session = await _get_or_create_session(db, tenant.id, customer.id)

    # ── 8. Log inbound message ───────────────────────────────────────
    inbound_msg = MessageLog(
        session_id=session.id,
        tenant_id=tenant.id,
        direction="INBOUND",
        content=message_body,
        message_type=message_type,
        wa_message_id=str(message_id),
        sender_phone=phone_number,
    )
    db.add(inbound_msg)
    await db.flush()

    # Push to Redis conversation cache
    await push_message(
        str(tenant.id),
        phone_number,
        {"role": "user", "content": message_body},
    )

    # ── 9. Check human takeover ──────────────────────────────────────
    if session.is_human_takeover:
        logger.info(f"Session {session.id} is in human takeover mode — skipping AI")
        await db.commit()

        # Publish event for dashboard real-time updates
        await publish_event(
            f"session:{session.id}:events",
            {
                "type": "message.received",
                "session_id": str(session.id),
                "content": message_body,
                "direction": "INBOUND",
                "phone": phone_number,
            },
        )
        return {"status": "ok", "mode": "human_takeover"}

    # ── 10. Build context and run AI ─────────────────────────────────
    try:
        ctx_manager = get_context_manager()
        context_messages = await ctx_manager.build_context(
            db, str(tenant.id), phone_number
        )

        ai_engine = get_ai_engine()
        ai_response = await ai_engine.generate_response(
            tenant=tenant,
            session=session,
            customer=customer,
            message=message_body,
            context=context_messages,
            db=db,
        )

        # ── 11. Send response via OpenWA ─────────────────────────────
        openwa = get_openwa_client()
        chat_id = str(payload.data.get("from", f"{phone_number}@c.us"))

        await openwa.send_text_message(
            base_url=tenant.openwa_base_url,
            session_id=payload.sessionId,
            chat_id=chat_id,
            text=ai_response,
        )

        # ── 12. Log outbound message ─────────────────────────────────
        outbound_msg = MessageLog(
            session_id=session.id,
            tenant_id=tenant.id,
            direction="OUTBOUND",
            content=ai_response,
            message_type="text",
            sender_phone=None,
        )
        db.add(outbound_msg)

        # Push AI response to Redis cache
        await push_message(
            str(tenant.id),
            phone_number,
            {"role": "assistant", "content": ai_response},
        )

        # Update customer last_contacted_at
        customer.last_contacted_at = inbound_msg.created_at

        await db.commit()

        # Publish real-time event
        await publish_event(
            f"session:{session.id}:events",
            {
                "type": "message.exchange",
                "session_id": str(session.id),
                "inbound": message_body,
                "outbound": ai_response,
                "phone": phone_number,
                "funnel_stage": session.funnel_stage,
            },
        )

        logger.info(
            f"✅ Processed message from {phone_number} for tenant {tenant.business_name}"
        )
        return {"status": "ok", "mode": "ai_response"}

    except Exception as e:
        logger.error(f"AI processing error: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="AI processing failed")


# ── Helper Functions ─────────────────────────────────────────────────

async def _upsert_customer(
    db: AsyncSession,
    tenant_id: UUID,
    phone_number: str,
    name: str | None,
) -> Customer:
    """Get existing customer or create a new one."""
    stmt = select(Customer).where(
        Customer.tenant_id == tenant_id,
        Customer.phone_number == phone_number,
    )
    result = await db.execute(stmt)
    customer = result.scalar_one_or_none()

    if customer is None:
        customer = Customer(
            tenant_id=tenant_id,
            phone_number=phone_number,
            name=name,
            lead_score="COLD",
        )
        db.add(customer)
        await db.flush()
        logger.info(f"New customer created: {phone_number}")
    elif name and not customer.name:
        customer.name = name
        await db.flush()

    return customer


async def _get_or_create_session(
    db: AsyncSession,
    tenant_id: UUID,
    customer_id: UUID,
) -> CommunicationSession:
    """Get the most recent active session or create a new one."""
    stmt = (
        select(CommunicationSession)
        .where(
            CommunicationSession.tenant_id == tenant_id,
            CommunicationSession.customer_id == customer_id,
        )
        .order_by(CommunicationSession.updated_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if session is None:
        session = CommunicationSession(
            tenant_id=tenant_id,
            customer_id=customer_id,
            funnel_stage="BROWSING",
            is_human_takeover=False,
            context_metadata={},
        )
        db.add(session)
        await db.flush()
        logger.info(f"New session created for customer {customer_id}")

    return session
