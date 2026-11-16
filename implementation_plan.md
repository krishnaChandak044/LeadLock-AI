# LeadLock AI — Implementation Plan

> **Distributed Multi-Tenant Conversational Automation Platform**
> Production-grade system with FastAPI microservices, OpenWA WhatsApp integration, Redis event bus, and Next.js dashboard.

## User Review Required

> [!IMPORTANT]
> **Architecture Deviation from PRD**: The PRD specifies Django as the "Core Master Engine" for DB migrations and admin. However, the user explicitly requested **FastAPI for microservices**. I will implement **both services as FastAPI** — one as the Edge Worker (webhook ingestion + AI) and one as the Core API (admin, CRUD, tenant management). SQLAlchemy + Alembic will replace Django ORM for migrations. This eliminates the Django/FastAPI split complexity while keeping the separation of concerns.

> [!IMPORTANT]
> **OpenWA Integration**: The existing [OpenWA-Internal](file:///Users/LENOVO/Desktop/LeadLock%20AI/OpenWA-Internal) is a full NestJS application with webhook dispatch, session management, and message sending APIs. LeadLock's FastAPI Edge Worker will:
> 1. **Receive** webhook payloads from OpenWA (via OpenWA's webhook registration system)
> 2. **Send** messages back through OpenWA's REST API (`POST /api/sessions/:sessionId/messages/send-text`)
> 3. **No code changes to OpenWA** are needed — we just configure a webhook pointing to our FastAPI endpoint.

> [!WARNING]
> **LLM API Keys Required**: The AI conversation engine needs either a Google Gemini API key or OpenAI API key. These must be provided in the `.env` file. Which provider should be the default?

## Open Questions

1. **LLM Provider**: Should I default to **Google Gemini** or **OpenAI GPT-4**? The PRD mentions both. I'll implement Gemini as primary with OpenAI fallback — let me know if you prefer otherwise.
2. **Authentication**: The PRD doesn't specify dashboard auth. Should I implement JWT-based auth for the dashboard, or is API key auth sufficient for MVP?
3. **Deployment Target**: Docker Compose for local dev is clear. Should I also add Kubernetes manifests for production deployment?

---

## Proposed Changes

The system is organized into **4 major components**, each in its own directory:

```
LeadLock AI/
├── leadlock_BE/
│   ├── core_service/          # FastAPI Core API (Tenant CRUD, Admin, Inventory)
│   ├── edge_worker/           # FastAPI Edge Worker (Webhook, AI, Conversations)
│   ├── shared/                # Shared models, schemas, utilities
│   ├── alembic/               # Database migrations
│   ├── alembic.ini
│   ├── requirements.txt
│   └── Dockerfile
├── leadlock_FE/               # Next.js Dashboard (App Router + TypeScript)
├── OpenWA-Internal/           # Existing WhatsApp gateway (no changes)
├── docker-compose.yml         # Full stack orchestration
├── .env.example
└── PRD.md
```

---

### Component 1: Shared Database Layer (`leadlock_BE/shared/`)

The shared package contains all SQLAlchemy models, Pydantic schemas, and utilities used by both services.

#### [NEW] `leadlock_BE/shared/__init__.py`
Empty init for package.

#### [NEW] `leadlock_BE/shared/database.py`
- Async SQLAlchemy engine creation (`create_async_engine` with `asyncpg`)
- Session factory using `async_sessionmaker`
- `get_db` dependency for FastAPI
- Connection pooling config (pool_size=20, max_overflow=10)

#### [NEW] `leadlock_BE/shared/models/__init__.py`
Exports all models.

#### [NEW] `leadlock_BE/shared/models/tenant.py`
```python
class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    business_name: Mapped[str] = mapped_column(String(255))
    vertical_type: Mapped[str] = mapped_column(String(50))  # AUTOMOTIVE, HEALTHCARE, GENERAL
    ai_system_prompt: Mapped[str] = mapped_column(Text)
    whatsapp_session_id: Mapped[str | None] = mapped_column(String(255))  # OpenWA session ID
    openwa_base_url: Mapped[str] = mapped_column(String(512), default="http://openwa-api:2785")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

#### [NEW] `leadlock_BE/shared/models/customer.py`
```python
class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    phone_number: Mapped[str] = mapped_column(String(32))  # E.164
    name: Mapped[str | None] = mapped_column(String(255))
    lead_score: Mapped[str] = mapped_column(String(20), default="COLD")  # COLD, WARM, HOT
    last_contacted_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint("tenant_id", "phone_number"),)
```

#### [NEW] `leadlock_BE/shared/models/session.py`
```python
class CommunicationSession(Base):
    __tablename__ = "communication_sessions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"))
    funnel_stage: Mapped[str] = mapped_column(String(50), default="BROWSING")
    is_human_takeover: Mapped[bool] = mapped_column(default=False)
    context_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

#### [NEW] `leadlock_BE/shared/models/message_log.py`
```python
class MessageLog(Base):
    __tablename__ = "message_logs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("communication_sessions.id"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    direction: Mapped[str] = mapped_column(String(10))  # INBOUND, OUTBOUND
    content: Mapped[str] = mapped_column(Text)
    message_type: Mapped[str] = mapped_column(String(20), default="text")
    wa_message_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

#### [NEW] `leadlock_BE/shared/models/inventory.py`
```python
class Inventory(Base):
    __tablename__ = "inventories"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(30), default="AVAILABLE")
    vertical_data: Mapped[dict] = mapped_column(JSONB, default=dict)  # Schema-agnostic
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
```

#### [NEW] `leadlock_BE/shared/schemas/` (Pydantic V2 schemas)
- `tenant.py` — TenantCreate, TenantUpdate, TenantResponse
- `customer.py` — CustomerCreate, CustomerResponse
- `session.py` — SessionResponse, SessionUpdate
- `inventory.py` — InventoryCreate, InventoryUpdate, InventoryResponse
- `webhook.py` — OpenWAWebhookPayload (matches OpenWA's dispatch format)

#### [NEW] `leadlock_BE/shared/config.py`
- Pydantic `BaseSettings` for all env vars (DATABASE_URL, REDIS_URL, GEMINI_API_KEY, OPENWA_BASE_URL, etc.)

#### [NEW] `leadlock_BE/shared/redis_client.py`
- Async Redis client (using `redis.asyncio`)
- Conversation cache helpers: `get_conversation_history()`, `push_message()`, `set_idempotency_key()`

---

### Component 2: FastAPI Edge Worker (`leadlock_BE/edge_worker/`)

The high-concurrency async service handling webhook ingestion, AI conversation, and outbound messaging.

#### [NEW] `leadlock_BE/edge_worker/__init__.py`

#### [NEW] `leadlock_BE/edge_worker/main.py`
- FastAPI app factory with lifespan (startup/shutdown)
- CORS middleware, logging middleware
- Health check endpoint
- Mounts all routers
- Starts Redis connection pool on startup

#### [NEW] `leadlock_BE/edge_worker/routers/webhook.py`
**The core webhook endpoint** that receives messages from OpenWA:

```
POST /api/v1/webhook/openwa
```

Flow:
1. Extract `idempotencyKey` and `data.id` from the OpenWA webhook payload
2. Redis atomic idempotency check: `SET msg:{message_id} "locked" EX 86400 NX`
3. If duplicate → return `200 OK` immediately
4. Parse sender phone number from `data.from` or `data.phoneNumber`
5. Resolve `tenant_id` by matching the OpenWA `sessionId` to a Tenant's `whatsapp_session_id`
6. Upsert `Customer` record (get_or_create by tenant_id + phone_number)
7. Get or create `CommunicationSession`
8. If `session.is_human_takeover == True` → skip AI, just log and return
9. Build conversation context from Redis cache (`session:{tenant_id}:{phone}`)
10. Call LLM with tenant's `ai_system_prompt` + context + tool definitions
11. Process LLM response (handle tool calls like `query_tenant_inventory`)
12. Send response back via OpenWA API
13. Log messages, update session metadata, push to Redis cache

#### [NEW] `leadlock_BE/edge_worker/routers/health.py`
- `GET /health` — readiness/liveness probe

#### [NEW] `leadlock_BE/edge_worker/services/ai_engine.py`
**The LLM conversation engine:**
- `ConversationEngine` class
- Supports Google Gemini (primary) and OpenAI (fallback)
- Tool/Function calling with structured JSON schemas
- Tools defined: `query_tenant_inventory`, `schedule_appointment`, `escalate_to_human`
- Context window management (last 15 messages from Redis)
- Healthcare safety scanner (regex for emergency keywords → auto-escalate)

#### [NEW] `leadlock_BE/edge_worker/services/tool_executor.py`
**Executes tool calls from the LLM:**
- `query_tenant_inventory` → Queries Inventory table with JSONB filters
- `schedule_appointment` → For healthcare vertical, checks availability slots
- `escalate_to_human` → Sets session to ESCALATED, notifies via WebSocket
- `update_lead_score` → Updates customer lead_score based on conversation signals

#### [NEW] `leadlock_BE/edge_worker/services/openwa_client.py`
**HTTP client for OpenWA outbound messaging:**
- `send_text_message(session_id, chat_id, text)` → `POST /api/sessions/{id}/messages/send-text`
- `send_typing_indicator(session_id, chat_id, duration_ms)` — simulates typing
- Rate limiting: 1.5–3.5s random delay between messages
- Retry logic with exponential backoff

#### [NEW] `leadlock_BE/edge_worker/services/context_manager.py`
**Conversation context handling:**
- Redis key schema: `session:{tenant_id}:{phone_number}`
- Stores last 15 messages as JSON list
- TTL: 24 hours
- Fallback: queries `message_logs` table for last 5 messages

---

### Component 3: FastAPI Core Service (`leadlock_BE/core_service/`)

The admin/management API for the dashboard.

#### [NEW] `leadlock_BE/core_service/__init__.py`

#### [NEW] `leadlock_BE/core_service/main.py`
- FastAPI app with CORS for Next.js dashboard
- JWT auth middleware (optional, API key for MVP)
- Mounts all CRUD routers

#### [NEW] `leadlock_BE/core_service/routers/tenants.py`
Full CRUD for tenants:
- `GET /api/v1/tenants` — List all tenants
- `POST /api/v1/tenants` — Create tenant
- `GET /api/v1/tenants/{id}` — Get tenant details
- `PUT /api/v1/tenants/{id}` — Update tenant (including AI prompt)
- `DELETE /api/v1/tenants/{id}` — Deactivate tenant

#### [NEW] `leadlock_BE/core_service/routers/customers.py`
- `GET /api/v1/tenants/{tenant_id}/customers` — List customers with filters (lead_score, search)
- `GET /api/v1/tenants/{tenant_id}/customers/{id}` — Customer detail with sessions
- `PUT /api/v1/tenants/{tenant_id}/customers/{id}` — Update lead_score, reassign

#### [NEW] `leadlock_BE/core_service/routers/sessions.py`
- `GET /api/v1/tenants/{tenant_id}/sessions` — List all sessions (with funnel_stage filter)
- `GET /api/v1/tenants/{tenant_id}/sessions/{id}` — Session detail with message history
- `PUT /api/v1/tenants/{tenant_id}/sessions/{id}/takeover` — Human takeover
- `PUT /api/v1/tenants/{tenant_id}/sessions/{id}/release` — Release back to AI
- WebSocket endpoint for real-time session streaming

#### [NEW] `leadlock_BE/core_service/routers/inventory.py`
Full CRUD for inventory:
- `GET /api/v1/tenants/{tenant_id}/inventory` — List with JSONB filters
- `POST /api/v1/tenants/{tenant_id}/inventory` — Add inventory item
- `PUT /api/v1/tenants/{tenant_id}/inventory/{id}` — Update item
- `DELETE /api/v1/tenants/{tenant_id}/inventory/{id}` — Remove item
- `POST /api/v1/tenants/{tenant_id}/inventory/bulk` — Bulk import

#### [NEW] `leadlock_BE/core_service/routers/analytics.py`
- `GET /api/v1/tenants/{tenant_id}/analytics` — Dashboard metrics
  - Total conversations, active sessions, lead distribution
  - Funnel stage breakdown
  - Messages per day (last 30 days)
  - AI vs Human response ratio

#### [NEW] `leadlock_BE/core_service/routers/websocket.py`
- WebSocket endpoint `/ws/sessions/{session_id}` for live chat monitoring
- Subscribes to Redis pub/sub channel `session:{session_id}:events`
- Broadcasts new messages in real-time to dashboard

---

### Component 4: Next.js Dashboard (`leadlock_FE/`)

Modern, premium dashboard with dark mode, glassmorphism, and real-time updates.

#### [NEW] Next.js App Router project
- TypeScript strict mode
- Tailwind CSS + Shadcn UI (as specified in PRD)
- App Router with layouts

#### [NEW] `leadlock_FE/src/app/layout.tsx`
- Root layout with persistent sidebar navigation
- Dark mode by default, premium color palette
- Inter font from Google Fonts

#### [NEW] `leadlock_FE/src/app/page.tsx` (Overview Analytics)
- KPI cards: Total Leads, Active Sessions, Conversion Rate, AI Response Time
- Charts: Lead funnel, messages over time, lead score distribution
- Recent activity feed

#### [NEW] `leadlock_FE/src/app/inbox/page.tsx` (Live Inbox Monitor)
- Left panel: Session list grouped by lead state (COLD/WARM/HOT tabs)
- Right panel: Real-time chat stream (read-only AI conversation view)
- **"Take Over Chat"** button → calls `PUT /sessions/{id}/takeover`
- WebSocket connection for real-time message updates
- Typing indicators, message status (sent/delivered)

#### [NEW] `leadlock_FE/src/app/inventory/page.tsx` (Inventory Ledger)
- Data table with search, sort, pagination
- JSONB field rendered as dynamic key-value tags
- Add/Edit modal with dynamic form based on vertical_type
- Bulk import via CSV

#### [NEW] `leadlock_FE/src/app/settings/page.tsx` (AI System Parameter Studio)
- Tenant AI prompt editor (code editor with syntax highlighting)
- Vertical type selector
- WhatsApp session connector (shows OpenWA session status)
- Test conversation playground

#### [NEW] `leadlock_FE/src/components/` (Reusable UI)
- `Sidebar.tsx` — Persistent navigation with icons, active state
- `ChatBubble.tsx` — WhatsApp-style message bubbles
- `LeadBadge.tsx` — Color-coded lead score indicators
- `KPICard.tsx` — Animated metric cards with trend arrows
- `DataTable.tsx` — Sortable, filterable table component

---

### Component 5: Infrastructure (`docker-compose.yml`)

#### [NEW] `docker-compose.yml` (Root level)
Orchestrates the full stack:
- `leadlock-edge-worker` — FastAPI Edge Worker (port 8001)
- `leadlock-core-api` — FastAPI Core Service (port 8000)
- `leadlock-frontend` — Next.js Dashboard (port 3000)
- `postgres` — PostgreSQL 16 (port 5432)
- `redis` — Redis 7 with AOF persistence (port 6379)
- `openwa-api` — Links to existing OpenWA-Internal (port 2785)
- Shared Docker network `leadlock-network`

#### [NEW] `.env.example`
All environment variables with defaults:
```env
DATABASE_URL=postgresql+asyncpg://leadlock:leadlock@postgres:5432/leadlock
REDIS_URL=redis://redis:6379/0
GEMINI_API_KEY=your-key-here
OPENWA_BASE_URL=http://openwa-api:2785
OPENWA_SESSION_ID=default
```

#### [NEW] `leadlock_BE/Dockerfile`
Multi-stage build for both FastAPI services.

#### [NEW] `leadlock_FE/Dockerfile`
Multi-stage build for Next.js.

---

## Data Flow Diagram

```mermaid
sequenceDiagram
    participant WA as WhatsApp User
    participant OWA as OpenWA Gateway
    participant EW as Edge Worker (FastAPI)
    participant R as Redis
    participant DB as PostgreSQL
    participant AI as Gemini/OpenAI LLM
    participant FE as Dashboard (Next.js)

    WA->>OWA: Send WhatsApp message
    OWA->>EW: POST /api/v1/webhook/openwa (webhook dispatch)
    EW->>R: SET msg:{id} EX 86400 NX (idempotency)
    R-->>EW: OK (new) or null (duplicate)
    
    alt New Message
        EW->>DB: Upsert Customer + Get/Create Session
        EW->>R: GET session:{tenant}:{phone} (context)
        R-->>EW: Last 15 messages
        EW->>AI: Chat completion with tools + context
        AI-->>EW: Response (text or tool_call)
        
        alt Tool Call (e.g., query_inventory)
            EW->>DB: Query inventory with JSONB filters
            DB-->>EW: Matching items
            EW->>AI: Send tool result back
            AI-->>EW: Final text response
        end
        
        EW->>OWA: POST /sessions/{id}/messages/send-text
        OWA->>WA: Deliver response via WhatsApp
        EW->>DB: Log messages
        EW->>R: PUSH to conversation cache
        EW->>R: PUBLISH session:{id}:events
        R-->>FE: Real-time update via WebSocket
    end
```

---

## Execution Phases

### Phase 1: Backend Foundation (Priority)
1. Set up shared models, database, Redis client
2. Alembic migrations
3. Edge Worker — webhook endpoint + idempotency
4. Core Service — Tenant & Inventory CRUD
5. Docker Compose with PostgreSQL + Redis

### Phase 2: AI Conversation Engine
1. LLM integration (Gemini + OpenAI)
2. Tool calling framework
3. Context management (Redis cache + DB fallback)
4. OpenWA outbound client with rate limiting
5. Healthcare safety scanner

### Phase 3: Core Service Completion
1. Customer & Session CRUD
2. Analytics endpoints
3. WebSocket for real-time updates
4. Human takeover flow

### Phase 4: Next.js Dashboard
1. Project scaffolding with Tailwind + Shadcn
2. Sidebar layout + dark mode
3. Overview analytics page
4. Live Inbox with real-time chat
5. Inventory management
6. AI Settings studio

### Phase 5: Integration & Polish
1. End-to-end testing with OpenWA
2. Docker Compose full-stack orchestration
3. Error handling, logging, monitoring
4. Documentation

---

## Verification Plan

### Automated Tests
```bash
# Run backend tests
cd leadlock_BE && pytest -v

# Run database migrations
cd leadlock_BE && alembic upgrade head

# Type checking
cd leadlock_FE && npx tsc --noEmit
```

### Manual Verification
- Start full stack with `docker compose up`
- Register a webhook in OpenWA pointing to `http://leadlock-edge-worker:8001/api/v1/webhook/openwa`
- Send a WhatsApp message → verify AI responds
- Open dashboard at `http://localhost:3000` → verify live inbox shows conversation
- Test "Take Over Chat" button
- Add inventory items → verify AI can query them
