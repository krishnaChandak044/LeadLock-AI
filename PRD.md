Project Name: LeadLock AI – Distributed Multi-Tenant Conversational Automation PlatformDocument Version: 2.1.0 (Production-Grade & Code-Generation Blueprint)Target Consumer: Advanced AI Systems (Claude 3.5 Sonnet / Opus) / Core Engineering Team1. System Architecture & High-Level DesignLeadLock AI is designed as a decoupled, Event-Driven Microservices Architecture built to isolate compute-heavy AI tasks from steady-state database transactions and management utilities.
                               ┌───────────────────────────┐
                               │   WhatsApp Network / App  │
                               └─────────────┬─────────────┘
                                             │ ▲
                  (Inbound Webhooks / OpenWA)│ │(Outbound Async Responses)
                                             ▼ │
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI EDGE WORKER SERVICE                               │
│ - Non-blocking high-concurrency webhook ingestion.                                     │
│ - Stateful runtime context management (Last 15 messages via Redis cache).              │
│ - LLM Engine (Gemini/OpenAI) Function & Tool Calling execution layer.                  │
└─────────────┬────────────────────────────────────────────────────────────▲─────────────┘
              │                                                            │
              │ (Pushes Background Notifications)                          │ (Pops Event Payload)
              ▼                                                            │
┌──────────────────────────────────────────────────────────────────────────┴─────────────┐
│                            REDIS EVENT BROKER & EVENT BUS                              │
│ - Queue Infrastructure (Celery / BullMQ compliant architecture).                      │
│ - 24-Hour In-Memory Idempotency Cache (Prevents duplicate webhook processing).         │
└─────────────▲────────────────────────────────────────────────────────────┬─────────────┘
              │                                                            │
              │ (Database State Sync / Mutex)                             │ (Pushes Event Outbound)
              ▼                                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              DJANGO CORE MASTER ENGINE                                 │
│ - Next.js REST API Layer (SaaS client endpoints).                                      │
│ - Multi-tenant DB separation (Row-level schema isolation).                             │
│ - Database migration source-of-truth and built-in Admin GUI control panel.            │
└─────────────┬──────────────────────────────────────────────────────────────────────────┘
              ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                             SHARED POSTGRESQL DATA STORE                               │
│ - High-performance relational transaction handling.                                    │
│ - Schema-agnostic `JSONB` data fields for handling multi-vertical extensions.          │
└────────────────────────────────────────────────────────────────────────────────────────┘

1.1 Architectural Component MandateDjango Core Application: Serves as the authoritative source for data validation, relational schemas, user configuration management, multi-tenant billing status, and back-office administration interfaces.FastAPI Edge Worker: Operates as a stateless, highly concurrent asynchronous pipeline handling incoming I/O traffic, conversational structure serialization, and real-time execution loops.Redis Event Bus: Provides system decoupling, temporary conversation history staging, message buffering, and deduplication guarantees.2. Database & Multi-Tenancy ArchitectureThe PostgreSQL instances utilize row-level multi-tenant design parameters. Every database query executed across the application must explicitly anchor to an indexed tenant_id.                  ┌──────────────┐
                  │   Tenants    │
                  └──────┬───────┘
                         │ 1
                         ├───────────────────────────┐
                         │ M                         │ M
                  ┌──────▼───────┐            ┌──────▼───────┐
                  │  Customers   │            │ Inventories  │
                  └──────┬───────┘            └──────────────┘
                         │ 1
                         │
                         │ M
                  ┌──────▼───────┐
                  │   Sessions   │
                  └──────────────┘
2.1 Core Relational Tables (Django ORM Specifications)Tenants TablePython# Models mapping schema characteristics
class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business_name = models.CharField(max_length=255)
    vertical_type = models.CharField(max_length=50, choices=[('AUTOMOTIVE', 'Automotive'), ('HEALTHCARE', 'Healthcare'), ('GENERAL', 'General')])
    ai_system_prompt = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['id', 'vertical_type'])]
Customers TablePythonclass Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=32) # E.164 Strict Format
    lead_score = models.CharField(max_length=20, choices=[('COLD', 'Cold'), ('WARM', 'Warm'), ('HOT', 'Hot')], default='COLD')
    last_contacted_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('tenant', 'phone_number')
        indexes = [models.Index(fields=['tenant', 'phone_number'])]
Sessions TablePythonclass CommunicationSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    funnel_stage = models.CharField(max_length=50, choices=[('BROWSING', 'Browsing'), ('QUALIFYING', 'Qualifying'), ('SCHEDULING', 'Scheduling'), ('ESCALATED', 'Escalated')], default='BROWSING')
    context_metadata = models.JSONField(default=dict) # Tracks unstructured dynamic variables extracted by LLM
    updated_at = models.DateTimeField(auto_now=True)
Inventories Table (Schema-Agnostic Engine Room)Pythonclass Inventory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    status = models.CharField(max_length=30, choices=[('AVAILABLE', 'Available'), ('RESERVED', 'Reserved'), ('SOLD', 'Sold')], default='AVAILABLE')
    vertical_data = models.JSONField(default=dict) # High Performance JSONB Mapping Field

    class Meta:
        indexes = [models.Index(fields=['tenant', 'status'])]
3. Functional Specifications by Service Layer3.1 FastAPI Ingestion Engine (Asynchronous Edge)Webhook Endpoint: Exposes a secure, un-throttled endpoint /api/v1/webhook/openwa accepting POST payloads from the local OpenWA Docker container instance.Idempotency Execution Strategy: 1. Extracts unique message_id from the payload envelope.2. Runs a Redis atomic evaluation check: SET message_id "locked" EX 86400 NX.3. If the command returns null, instantly terminates execution with status code 200 OK to gracefully ignore duplicates.Context Preservation Sequence: Fetches conversation log structures from Redis cache using key schemas formatted as session:{tenant_id}:{phone_number}. If empty, pulls the previous 5 history blocks natively out of PostgreSQL via async engine drivers (SQLAlchemy/Tortoise).Deterministic Native Functional Extraction (Tool Calling): The LLM framework must operate via explicit JSON Tool schemas. No model is permitted to freely declare arbitrary textual availability metrics.JSON{
  "name": "query_tenant_inventory",
  "description": "Queries the database for matching products/assets available for purchase or booking based on customer specifications.",
  "parameters": {
    "type": "object",
    "properties": {
      "filters": {
        "type": "object",
        "description": "Extracted key-value criteria from the conversation to query the schema-agnostic database attributes field."
      }
    },
    "required": ["filters"]
  }
}
3.2 Django Management Engine (System Brain)Migration Domain Authority: Only the Django module contains structural definition capabilities. All execution modifications to data states flow exclusively through regular Django commands.Administrative Operations Panel: Exposes the internal administrative structure out-of-the-box, optimized for support analysts to perform critical modifications:Re-assign leads assigned to individual customer service agents.Real-time auditing blocks of raw interaction loops across any target session lifecycle.Manual overrides on custom configuration prompts per unique tenant identity profile.3.3 Asynchronous Queue & Messaging LayersAutomated Anti-Ban Transmission Loop: Outbound transmission jobs directed toward the OpenWA framework must be processed using sliding rate-limit configurations.Naturalized Pacing Controls: Insert mathematical pacing delays between 1.5 and 3.5 seconds before hitting outbound APIs. Send a distinct WebSocket/OpenWA instruction payload initiating a typing_indicator_on loop matching computed target string-length approximations.4. Front-End Architecture & Dashboard UI/UXThe customer profile interacts solely inside WhatsApp. The web frontend serves as the operational dashboard for B2B subscribers.4.1 UI Component Foundation StackCore Application Framework: Next.js (App Router distribution pattern) with TypeScript compiling under strict checking specifications.Presentation Layer Libraries: Tailwind CSS combined with Shadcn UI interface elements.4.2 Dashboard Layout TopographyGlobal Navigation: Lock layout to a non-wrapping persistent left-hand command sidebar tracking key workspace items: Overview Analytics, Live Inbox Monitor, Inventory Ledger, and AI System Parameter Studio.Live Chat Monitor Module:Left Component Window: List views of current sessions grouped by lead state categories (COLD, WARM, HOT).Main Component Window: Read-only stream capturing real-time automated AI messaging loops.Action Controls: A prominent manual override button labeled "Take Over Chat" that instantly sets the session database flag to ESCALATED_TO_HUMAN, halts automated processing, and transfers manual interactive ownership to the workspace user.Inventory Ledger Management Interface: Provides comprehensive workspace access controls to add, update, or remove dynamic entities mapped directly to the relational database tables via background state synchronization pipelines.5. Multi-Vertical Strategy MatrixThe ingestion pipelines evaluate incoming database settings upon message execution boundaries to dynamically load contextual execution assets.Vertical Contextvertical_data JSONB StructureTool Selection Routing PipelineSafety Escalation Failure ProtocolAUTOMOTIVE{"make": "Toyota", "model": "Fortuner", "year": 2022, "price": 1450000, "color": "White"}Triggers query_tenant_inventory using localized parameters to match physical variables.Falls back to human routing if pricing parameter checks fall outside structural operational guidelines.HEALTHCARE{"practitioner": "Dr. Verma", "specialty": "Dental", "available_slots": ["2026-06-24T10:00:00"]}Executes scheduling modules checking atomic availability boundaries against resource timelines.Immediate Short-Circuit: Scans incoming payloads for high-risk medical strings. Bypasses the LLM entirely, flips status to ESCALATED, and sends hardcoded emergency guidance.6. Code Generation System Parameters for ClaudeWhen deploying this operational document to initialize codebase assets, ensure absolute adherence to the formatting parameters below:Eliminate Typing Ambiguities: Any generation containing Python typing strings explicitly mapping to raw Any keywords must be rejected. Use strong variable typing definitions across every function block interface.Explicit Multi-Tenant Boundaries: Every query statement matching database access profiles must contain defensive parameter validation layers checking for explicit, valid tenant_id structures.Local Environment Infrastructure Blueprinting: Compile a clear, cross-platform functional docker-compose.yml asset linking localized environments cleanly, matching the core specifications outlined in this document.Generate production-grade Prisma schema modeling these database entitiesWrite the async FastAPI webhook endpoint with integrated Redis idempotency verificationCreate the Next.js Live Inbox component tracking real-time session states