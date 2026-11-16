"""
LeadLock AI — Tool Executor
Executes function/tool calls from the LLM.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import Tenant, Customer, CommunicationSession, Inventory
from shared.redis_client import publish_event

logger = logging.getLogger("edge_worker.tool_executor")


class ToolExecutor:
    """Executes LLM tool calls against the database and services."""

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        db: AsyncSession,
        tenant: Tenant,
        session: CommunicationSession,
        customer: Customer,
    ) -> dict[str, Any]:
        """Route and execute a tool call."""
        handlers = {
            "query_tenant_inventory": self._query_inventory,
            "schedule_appointment": self._schedule_appointment,
            "escalate_to_human": self._escalate_to_human,
            "update_lead_score": self._update_lead_score,
        }

        handler = handlers.get(tool_name)
        if handler is None:
            logger.warning(f"Unknown tool: {tool_name}")
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            return await handler(
                arguments=arguments,
                db=db,
                tenant=tenant,
                session=session,
                customer=customer,
            )
        except Exception as e:
            logger.error(f"Tool execution error ({tool_name}): {e}", exc_info=True)
            return {"error": f"Tool execution failed: {str(e)}"}

    async def _query_inventory(
        self,
        arguments: dict[str, Any],
        db: AsyncSession,
        tenant: Tenant,
        session: CommunicationSession,
        customer: Customer,
    ) -> dict[str, Any]:
        """Query inventory items using JSONB filters."""
        filters: dict[str, Any] = arguments.get("filters", {})

        stmt = select(Inventory).where(
            Inventory.tenant_id == tenant.id,
            Inventory.status == "AVAILABLE",
        )

        # Apply JSONB filters dynamically
        for key, value in filters.items():
            if key.lower() == "name":
                stmt = stmt.where(Inventory.name.ilike(f"%{value}%"))
            else:
                # Case-insensitive JSONB matching
                stmt = stmt.where(
                    Inventory.vertical_data[key].astext.ilike(f"%{value}%")
                )

        stmt = stmt.limit(10)
        result = await db.execute(stmt)
        items = result.scalars().all()

        if not items:
            return {
                "found": 0,
                "message": "No matching items found in inventory.",
                "items": [],
            }

        # Update funnel stage to QUALIFYING since they're looking at products
        if session.funnel_stage == "BROWSING":
            session.funnel_stage = "QUALIFYING"
            await db.flush()

        return {
            "found": len(items),
            "items": [
                {
                    "id": str(item.id),
                    "name": item.name,
                    "status": item.status,
                    **item.vertical_data,
                }
                for item in items
            ],
        }

    async def _schedule_appointment(
        self,
        arguments: dict[str, Any],
        db: AsyncSession,
        tenant: Tenant,
        session: CommunicationSession,
        customer: Customer,
    ) -> dict[str, Any]:
        """Schedule an appointment (healthcare vertical)."""
        specialty: str = arguments.get("specialty", "General")
        practitioner: str | None = arguments.get("practitioner")
        preferred_date: str | None = arguments.get("preferred_date")
        preferred_time: str | None = arguments.get("preferred_time")

        # Query available practitioners from inventory
        stmt = select(Inventory).where(
            Inventory.tenant_id == tenant.id,
            Inventory.status == "AVAILABLE",
        )

        if practitioner:
            stmt = stmt.where(
                Inventory.vertical_data["practitioner"].astext == practitioner
            )
        if specialty:
            stmt = stmt.where(
                Inventory.vertical_data["specialty"].astext == specialty
            )

        result = await db.execute(stmt)
        available = result.scalars().all()

        if not available:
            return {
                "available": False,
                "message": f"No available slots for {specialty}",
                "slots": [],
            }

        # Update funnel stage to SCHEDULING
        session.funnel_stage = "SCHEDULING"
        session.context_metadata = {
            **session.context_metadata,
            "booking_interest": {
                "specialty": specialty,
                "practitioner": practitioner,
                "preferred_date": preferred_date,
                "preferred_time": preferred_time,
            },
        }
        await db.flush()

        return {
            "available": True,
            "practitioners": [
                {
                    "name": item.vertical_data.get("practitioner", "Doctor"),
                    "specialty": item.vertical_data.get("specialty", specialty),
                    "available_slots": item.vertical_data.get("available_slots", []),
                }
                for item in available[:5]
            ],
        }

    async def _escalate_to_human(
        self,
        arguments: dict[str, Any],
        db: AsyncSession,
        tenant: Tenant,
        session: CommunicationSession,
        customer: Customer,
    ) -> dict[str, Any]:
        """Escalate the conversation to a human agent."""
        reason: str = arguments.get("reason", "Customer requested human assistance")

        session.funnel_stage = "ESCALATED"
        session.is_human_takeover = True
        session.context_metadata = {
            **session.context_metadata,
            "escalation_reason": reason,
        }
        await db.flush()

        # Publish escalation event for real-time dashboard notification
        await publish_event(
            f"session:{session.id}:events",
            {
                "type": "session.escalated",
                "session_id": str(session.id),
                "customer_phone": customer.phone_number,
                "customer_name": customer.name,
                "reason": reason,
            },
        )

        logger.info(f"Session {session.id} escalated: {reason}")

        return {
            "escalated": True,
            "reason": reason,
            "message": "A human agent has been notified and will join shortly.",
        }

    async def _update_lead_score(
        self,
        arguments: dict[str, Any],
        db: AsyncSession,
        tenant: Tenant,
        session: CommunicationSession,
        customer: Customer,
    ) -> dict[str, Any]:
        """Update the customer's lead score."""
        new_score: str = arguments.get("new_score", "WARM")
        reason: str = arguments.get("reason", "")

        old_score = customer.lead_score
        customer.lead_score = new_score
        await db.flush()

        logger.info(
            f"Lead score updated for {customer.phone_number}: "
            f"{old_score} → {new_score} ({reason})"
        )

        return {
            "updated": True,
            "old_score": old_score,
            "new_score": new_score,
            "reason": reason,
        }
