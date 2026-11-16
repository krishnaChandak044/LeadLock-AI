"""
LeadLock AI — Conversation Engine
LLM-powered AI conversation with tool/function calling.
Supports Google Gemini (primary) and OpenAI (fallback).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import settings
from shared.models import Tenant, Customer, CommunicationSession

from .tool_executor import ToolExecutor

logger = logging.getLogger("edge_worker.ai_engine")

# ── Healthcare Safety Keywords ───────────────────────────────────────
EMERGENCY_KEYWORDS = re.compile(
    r"\b(suicide|suicidal|kill myself|heart attack|chest pain|"
    r"stroke|overdose|can'?t breathe|emergency|dying|"
    r"bleeding heavily|unconscious|seizure)\b",
    re.IGNORECASE,
)

EMERGENCY_RESPONSE = (
    "🚨 I've detected an emergency situation in your message. "
    "Please call emergency services immediately:\n\n"
    "• Emergency: 112 / 911\n"
    "• Ambulance: 108\n\n"
    "A human representative has been notified and will reach out to you shortly. "
    "Please stay safe."
)

# ── Tool Definitions (JSON Schema for LLM Function Calling) ─────────
TOOL_DEFINITIONS = [
    {
        "name": "query_tenant_inventory",
        "description": (
            "Queries the database for matching products/assets available "
            "for purchase or booking based on customer specifications."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filters": {
                    "type": "object",
                    "description": (
                        "Key-value criteria extracted from the conversation "
                        "to query the schema-agnostic database attributes field."
                    ),
                },
            },
            "required": ["filters"],
        },
    },
    {
        "name": "schedule_appointment",
        "description": (
            "Schedules an appointment or booking for the customer. "
            "Used for healthcare verticals to check availability."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "practitioner": {
                    "type": "string",
                    "description": "Name of the doctor or practitioner",
                },
                "specialty": {
                    "type": "string",
                    "description": "Medical specialty",
                },
                "preferred_date": {
                    "type": "string",
                    "description": "Preferred date in ISO 8601 format",
                },
                "preferred_time": {
                    "type": "string",
                    "description": "Preferred time slot",
                },
            },
            "required": ["specialty"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": (
            "Escalates the conversation to a human agent. ONLY call this if the customer types EXACTLY 'human', 'agent', 'support', or 'help', or explicitly asks to speak to a person. DO NOT use this for edge cases, non-English languages, or missing information."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Why the conversation is being escalated",
                },
            },
            "required": ["reason"],
        },
    },
    {
        "name": "update_lead_score",
        "description": (
            "Updates the customer's lead score based on conversation signals. "
            "COLD = browsing, WARM = showing interest, HOT = ready to purchase/book."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "new_score": {
                    "type": "string",
                    "enum": ["COLD", "WARM", "HOT"],
                    "description": "The updated lead score",
                },
                "reason": {
                    "type": "string",
                    "description": "Why the score changed",
                },
            },
            "required": ["new_score", "reason"],
        },
    },
]


class ConversationEngine:
    """LLM-powered conversation engine with tool calling."""

    def __init__(self) -> None:
        self.tool_executor = ToolExecutor()
        self._gemini_client: Any | None = None
        self._openai_client: Any | None = None
        self._current_key_index = 0

    async def generate_response(
        self,
        tenant: Tenant,
        session: CommunicationSession,
        customer: Customer,
        message: str,
        context: list[dict[str, str]],
        db: AsyncSession,
    ) -> str:
        """
        Generate an AI response for the incoming message.

        1. Check for healthcare emergencies
        2. Build system prompt with tenant config
        3. Call LLM with tool definitions
        4. Execute any tool calls
        5. Return final response
        """

        # ── Healthcare Safety Scanner ────────────────────────────────
        if tenant.vertical_type == "HEALTHCARE" and EMERGENCY_KEYWORDS.search(message):
            logger.warning(f"🚨 Emergency detected for session {session.id}")
            session.funnel_stage = "ESCALATED"
            session.is_human_takeover = True
            await db.flush()
            return EMERGENCY_RESPONSE

        # ── Build System Prompt ──────────────────────────────────────
        system_prompt = self._build_system_prompt(tenant, customer, session)

        # ── Build Messages ───────────────────────────────────────────
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(context)
        messages.append({"role": "user", "content": message})

        # ── Call LLM ─────────────────────────────────────────────────
        try:
            if settings.gemini_api_key:
                response = await self._call_gemini(messages, db, tenant, session, customer)
            elif settings.openai_api_key:
                response = await self._call_openai(messages, db, tenant, session, customer)
            else:
                logger.error("No LLM API key configured!")
                return (
                    "I'm sorry, I'm currently experiencing technical difficulties. "
                    "A human representative will assist you shortly."
                )

            return response

        except Exception as e:
            logger.error(f"LLM call failed: {e}", exc_info=True)
            return (
                "I'm sorry, I'm having trouble processing your request right now. "
                "Please try again in a moment, or type 'help' to speak with a representative."
            )

    async def _call_gemini(
        self,
        messages: list[dict[str, str]],
        db: AsyncSession,
        tenant: Tenant,
        session: CommunicationSession,
        customer: Customer,
    ) -> str:
        """Call Google Gemini with function calling support."""
        from google import genai
        from google.genai import types

        if self._gemini_client is None:
            self._gemini_client = genai.Client(api_key=settings.gemini_api_key)

        # Build tools for Gemini
        gemini_tools = []
        for tool_def in TOOL_DEFINITIONS:
            gemini_tools.append(types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name=tool_def["name"],
                        description=tool_def["description"],
                        parameters=tool_def["parameters"],
                    )
                ]
            ))

        # Build Gemini contents
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                continue  # System instruction handled separately
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])],
            ))

        system_instruction = next(
            (m["content"] for m in messages if m["role"] == "system"), None
        )

        # Call Gemini
        response = self._gemini_client.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=gemini_tools,
                temperature=0.7,
                max_output_tokens=1024,
            ),
        )

        # Handle function calls
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    tool_name = part.function_call.name
                    tool_args = dict(part.function_call.args) if part.function_call.args else {}

                    logger.info(f"Tool call: {tool_name}({tool_args})")

                    tool_result = await self.tool_executor.execute(
                        tool_name=tool_name,
                        arguments=tool_args,
                        db=db,
                        tenant=tenant,
                        session=session,
                        customer=customer,
                    )

                    # Send tool result back to Gemini for final response
                    contents.append(types.Content(
                        role="model",
                        parts=[types.Part(function_call=part.function_call)],
                    ))
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part(function_response=types.FunctionResponse(
                            name=tool_name,
                            response={"result": tool_result},
                        ))],
                    ))

                    follow_up = self._gemini_client.models.generate_content(
                        model=settings.gemini_model,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.7,
                            max_output_tokens=1024,
                        ),
                    )

                    return follow_up.text or "I found some information for you."

                if part.text:
                    return part.text

        return response.text or "I'm here to help! How can I assist you?"

    async def _call_openai(
        self,
        messages: list[dict[str, str]],
        db: AsyncSession,
        tenant: Tenant,
        session: CommunicationSession,
        customer: Customer,
    ) -> str:
        """Call OpenAI with function calling support."""
        import json

        # Build tools for OpenAI
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            }
            for t in TOOL_DEFINITIONS
        ]

        response = await self._create_chat_completion_with_retry(
            model=settings.openai_model,
            messages=messages,  # type: ignore[arg-type]
            tools=openai_tools,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=1024,
        )

        choice = response.choices[0]

        # Handle tool calls
        if choice.message.tool_calls:
            tool_call = choice.message.tool_calls[0]
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            logger.info(f"Tool call: {tool_name}({tool_args})")

            tool_result = await self.tool_executor.execute(
                tool_name=tool_name,
                arguments=tool_args,
                db=db,
                tenant=tenant,
                session=session,
                customer=customer,
            )

            # Send tool result back for final response
            messages.append(choice.message.model_dump())  # type: ignore[arg-type]
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result),
            })

            follow_up = await self._create_chat_completion_with_retry(
                model=settings.openai_model,
                messages=messages,  # type: ignore[arg-type]
                temperature=0.7,
                max_tokens=1024,
            )

            final_text = follow_up.choices[0].message.content or "Here's what I found."
            
            # Clean up SambaNova Llama 3.3 JSON leaks in text
            import re
            final_text = re.sub(r'\{"name":\s*".*?\}\}', '', final_text, flags=re.DOTALL).strip()
            return final_text

        final_text = choice.message.content or "I'm here to help!"
        import re
        final_text = re.sub(r'\{"name":\s*".*?\}\}', '', final_text, flags=re.DOTALL).strip()
        return final_text

    async def _create_chat_completion_with_retry(self, **kwargs) -> Any:
        """Helper to handle rate limits and round-robin through multiple API keys."""
        from openai import AsyncOpenAI, RateLimitError
        
        # Parse available keys (supports file or comma-separated list)
        keys = []
        import os
        keys_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../keys"))
        
        try:
            if os.path.exists(keys_file_path):
                with open(keys_file_path, "r") as f:
                    keys = [line.strip() for line in f if line.strip()]
        except Exception as e:
            pass
            
        if not keys:
            key_str = getattr(settings, "openai_api_key", "") or ""
            keys = [k.strip() for k in key_str.split(",") if k.strip()]
        
        if not keys:
            raise ValueError("No API keys configured")
            
        last_error = None
        
        # Try up to the total number of keys available
        for _ in range(len(keys)):
            try:
                if self._openai_client is None:
                    # Initialize with the current key index
                    client_kwargs = {"api_key": keys[self._current_key_index]}
                    if settings.openai_base_url:
                        client_kwargs["base_url"] = settings.openai_base_url
                    self._openai_client = AsyncOpenAI(**client_kwargs)
                
                return await self._openai_client.chat.completions.create(**kwargs)
                
            except RateLimitError as e:
                logger.warning(f"Rate limit hit on key index {self._current_key_index}. Switching to next key...")
                last_error = e
                # Rotate to the next key
                self._current_key_index = (self._current_key_index + 1) % len(keys)
                # Force re-initialization on next loop iteration
                self._openai_client = None
                
        # If all keys are rate-limited, raise the final error
        if last_error:
            raise last_error

    @staticmethod
    def _build_system_prompt(
        tenant: Tenant,
        customer: Customer,
        session: CommunicationSession,
    ) -> str:
        """Build the complete system prompt with tenant config and context."""
        base_prompt = tenant.ai_system_prompt or ""

        context_section = f"""
--- SYSTEM CONTEXT ---
Business: {tenant.business_name}
Vertical: {tenant.vertical_type}
Customer Phone: {customer.phone_number}
Customer Name: {customer.name or 'Unknown'}
Lead Score: {customer.lead_score}
Funnel Stage: {session.funnel_stage}
Session Metadata: {json.dumps(session.context_metadata)}

--- INSTRUCTIONS ---
You are an AI sales/support assistant for {tenant.business_name}.
- Be professional, friendly, and concise.
- Keep responses under 200 words.
- When the customer shows buying intent, use the update_lead_score tool to upgrade their score.
- When the customer asks about available products/services, use the query_tenant_inventory tool.
- For healthcare: If they want to book, use schedule_appointment.
- DO NOT escalate to human unless the customer explicitly asks to speak to a person, or is extremely frustrated.
- NEVER fabricate product details, prices, or availability. Always query the database.
- CRITICAL: When executing a tool, DO NOT output the tool's JSON in your text response.
- Format responses for WhatsApp (use *bold*, _italic_, emojis sparingly).
"""
        return f"{base_prompt}\n{context_section}"
