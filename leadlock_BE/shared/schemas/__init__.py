"""
LeadLock AI — Pydantic Schemas
Request/response schemas for all API endpoints.
"""

from .tenant import TenantCreate, TenantUpdate, TenantResponse
from .customer import CustomerCreate, CustomerUpdate, CustomerResponse
from .session import SessionResponse, SessionUpdate, SessionDetailResponse, MessageLogResponse
from .inventory import InventoryCreate, InventoryUpdate, InventoryResponse
from .webhook import OpenWAWebhookPayload

__all__ = [
    "TenantCreate",
    "TenantUpdate",
    "TenantResponse",
    "CustomerCreate",
    "CustomerUpdate",
    "CustomerResponse",
    "SessionResponse",
    "SessionUpdate",
    "SessionDetailResponse",
    "MessageLogResponse",
    "InventoryCreate",
    "InventoryUpdate",
    "InventoryResponse",
    "OpenWAWebhookPayload",
]
