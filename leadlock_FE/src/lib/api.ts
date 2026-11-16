/**
 * LeadLock AI — API Client
 * Typed HTTP client for the Core Service API.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API Error: ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Types ─────────────────────────────────────────────────────────────

export const DEMO_TENANT_ID = 'eb8a5eff-77c5-48e2-b76b-b1772969be0c';

export interface Tenant {
  id: string;
  business_name: string;
  vertical_type: 'AUTOMOTIVE' | 'HEALTHCARE' | 'GENERAL';
  ai_system_prompt: string;
  whatsapp_session_id: string | null;
  openwa_base_url: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Customer {
  id: string;
  tenant_id: string;
  phone_number: string;
  name: string | null;
  lead_score: 'COLD' | 'WARM' | 'HOT';
  last_contacted_at: string;
  created_at: string;
}

export interface CommunicationSession {
  id: string;
  tenant_id: string;
  customer_id: string;
  funnel_stage: 'BROWSING' | 'QUALIFYING' | 'SCHEDULING' | 'ESCALATED';
  is_human_takeover: boolean;
  context_metadata: Record<string, unknown>;
  updated_at: string;
  created_at: string;
}

export interface MessageLog {
  id: string;
  session_id: string;
  direction: 'INBOUND' | 'OUTBOUND';
  content: string;
  message_type: string;
  wa_message_id: string | null;
  sender_phone: string | null;
  created_at: string;
}

export interface SessionDetail {
  session: CommunicationSession;
  customer_name: string | null;
  customer_phone: string;
  customer_lead_score: string;
  messages: MessageLog[];
  total_messages: number;
}

export interface InventoryItem {
  id: string;
  tenant_id: string;
  name: string;
  status: 'AVAILABLE' | 'RESERVED' | 'SOLD';
  vertical_data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Analytics {
  overview: {
    total_customers: number;
    total_sessions: number;
    active_sessions_24h: number;
    total_messages: number;
    inbound_messages: number;
    outbound_messages: number;
  };
  lead_distribution: Record<string, number>;
  funnel_breakdown: Record<string, number>;
  response_ratio: {
    ai_managed: number;
    human_managed: number;
  };
  messages_per_day: { date: string; count: number }[];
}

// ── API Methods ─────────────────────────────────────────────────────

export const api = {
  // Tenants
  getTenants: () => fetchAPI<Tenant[]>('/api/v1/tenants'),
  getTenant: (id: string) => fetchAPI<Tenant>(`/api/v1/tenants/${id}`),
  createTenant: (data: Partial<Tenant>) =>
    fetchAPI<Tenant>('/api/v1/tenants', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateTenant: (id: string, data: Partial<Tenant>) =>
    fetchAPI<Tenant>(`/api/v1/tenants/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  // Customers
  getCustomers: (tenantId: string, params?: { lead_score?: string; search?: string }) => {
    const query = new URLSearchParams();
    if (params?.lead_score) query.set('lead_score', params.lead_score);
    if (params?.search) query.set('search', params.search);
    const qs = query.toString();
    return fetchAPI<Customer[]>(`/api/v1/tenants/${tenantId}/customers${qs ? `?${qs}` : ''}`);
  },
  getCustomerCounts: (tenantId: string) =>
    fetchAPI<Record<string, number>>(`/api/v1/tenants/${tenantId}/customers/count`),

  // Sessions
  getSessions: (tenantId: string, params?: { funnel_stage?: string }) => {
    const query = new URLSearchParams();
    if (params?.funnel_stage) query.set('funnel_stage', params.funnel_stage);
    const qs = query.toString();
    return fetchAPI<CommunicationSession[]>(
      `/api/v1/tenants/${tenantId}/sessions${qs ? `?${qs}` : ''}`
    );
  },
  getSessionDetail: (tenantId: string, sessionId: string) =>
    fetchAPI<SessionDetail>(`/api/v1/tenants/${tenantId}/sessions/${sessionId}`),
  takeoverSession: (tenantId: string, sessionId: string) =>
    fetchAPI<CommunicationSession>(
      `/api/v1/tenants/${tenantId}/sessions/${sessionId}/takeover`,
      { method: 'PUT' }
    ),
  releaseSession: (tenantId: string, sessionId: string) =>
    fetchAPI<CommunicationSession>(
      `/api/v1/tenants/${tenantId}/sessions/${sessionId}/release`,
      { method: 'PUT' }
    ),

  // Inventory
  getInventory: (tenantId: string, params?: { status?: string }) => {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    const qs = query.toString();
    return fetchAPI<InventoryItem[]>(
      `/api/v1/tenants/${tenantId}/inventory${qs ? `?${qs}` : ''}`
    );
  },
  createInventory: (tenantId: string, data: Partial<InventoryItem>) =>
    fetchAPI<InventoryItem>(`/api/v1/tenants/${tenantId}/inventory`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateInventory: (tenantId: string, itemId: string, data: Partial<InventoryItem>) =>
    fetchAPI<InventoryItem>(`/api/v1/tenants/${tenantId}/inventory/${itemId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  deleteInventory: (tenantId: string, itemId: string) =>
    fetchAPI<void>(`/api/v1/tenants/${tenantId}/inventory/${itemId}`, {
      method: 'DELETE',
    }),

  // Analytics
  getAnalytics: (tenantId: string) =>
    fetchAPI<Analytics>(`/api/v1/tenants/${tenantId}/analytics`),
};
