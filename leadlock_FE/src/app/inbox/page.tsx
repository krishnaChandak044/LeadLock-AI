'use client';

import { useState, useEffect } from 'react';
import type { CommunicationSession, SessionDetail } from '@/lib/api';
import { api, DEMO_TENANT_ID } from '@/lib/api';

// Mock data
const mockSessions: CommunicationSession[] = [
  { id: 'sess_1', tenant_id: 't_1', customer_id: 'c_1', funnel_stage: 'QUALIFYING', is_human_takeover: false, context_metadata: {}, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
  { id: 'sess_2', tenant_id: 't_1', customer_id: 'c_2', funnel_stage: 'ESCALATED', is_human_takeover: true, context_metadata: {}, created_at: new Date(Date.now() - 3600000).toISOString(), updated_at: new Date(Date.now() - 3600000).toISOString() },
];

const mockDetail: SessionDetail = {
  session: mockSessions[0],
  customer_name: 'John Doe',
  customer_phone: '+1555010203',
  customer_lead_score: 'WARM',
  messages: [
    { id: 'msg_1', session_id: 'sess_1', direction: 'INBOUND', content: 'Hi, I am interested in buying a car.', message_type: 'text', wa_message_id: 'wa_1', sender_phone: '+1555010203', created_at: new Date(Date.now() - 300000).toISOString() },
    { id: 'msg_2', session_id: 'sess_1', direction: 'OUTBOUND', content: 'Hello John! Welcome to our dealership. What kind of vehicle are you looking for?', message_type: 'text', wa_message_id: 'wa_2', sender_phone: null, created_at: new Date(Date.now() - 290000).toISOString() },
    { id: 'msg_3', session_id: 'sess_1', direction: 'INBOUND', content: 'An SUV, ideally under 30k.', message_type: 'text', wa_message_id: 'wa_3', sender_phone: '+1555010203', created_at: new Date(Date.now() - 250000).toISOString() },
  ],
  total_messages: 3,
};

export default function InboxPage() {
  const [sessions, setSessions] = useState<CommunicationSession[]>([]);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [reply, setReply] = useState('');

  useEffect(() => {
    api.getSessions(DEMO_TENANT_ID).then(data => {
      setSessions(data);
      if (data.length > 0) setActiveSession(data[0].id);
    }).catch(console.error);
  }, []);

  useEffect(() => {
    if (activeSession) {
      api.getSessionDetail(DEMO_TENANT_ID, activeSession).then(setDetail).catch(console.error);
    }
  }, [activeSession]);

  const handleTakeover = () => {
    if (!detail) return;
    const isTakeover = !detail.session.is_human_takeover;
    setDetail({
      ...detail,
      session: { ...detail.session, is_human_takeover: isTakeover }
    });
    setSessions(sessions.map(s => s.id === detail.session.id ? { ...s, is_human_takeover: isTakeover } : s));
  };

  const handleSend = () => {
    if (!reply.trim() || !detail) return;
    const newMsg = {
      id: `msg_${Date.now()}`,
      session_id: detail.session.id,
      direction: 'OUTBOUND' as const,
      content: reply,
      message_type: 'text',
      wa_message_id: null,
      sender_phone: null,
      created_at: new Date().toISOString()
    };
    setDetail({
      ...detail,
      messages: [...detail.messages, newMsg]
    });
    setReply('');
  };

  return (
    <div className="animate-fade-in" style={{ height: 'calc(100vh - 4rem)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '0.5rem' }}>Live Inbox</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
          Monitor AI conversations and take over when needed.
        </p>
      </div>

      <div style={{ display: 'flex', gap: '1.5rem', flex: 1, minHeight: 0 }}>
        {/* Session List */}
        <div className="glass-card" style={{ width: '320px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '1rem', borderBottom: '1px solid var(--border)' }}>
            <input
              type="text"
              placeholder="Search conversations..."
              className="input-field"
            />
          </div>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {sessions.map((s) => (
              <div
                key={s.id}
                onClick={() => setActiveSession(s.id)}
                style={{
                  padding: '1rem',
                  borderBottom: '1px solid var(--border)',
                  cursor: 'pointer',
                  background: activeSession === s.id ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
                  borderLeft: activeSession === s.id ? '3px solid var(--accent-primary)' : '3px solid transparent',
                  transition: 'all 0.2s ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>
                    {s.id === 'sess_1' ? 'John Doe' : 'Jane Smith'}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {new Date(s.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className={`stage-badge ${s.funnel_stage.toLowerCase()}`}>
                    {s.funnel_stage}
                  </span>
                  {s.is_human_takeover && (
                    <span style={{ fontSize: '0.7rem', color: '#ef4444', fontWeight: 600, background: 'rgba(239, 68, 68, 0.1)', padding: '2px 6px', borderRadius: '4px' }}>
                      HUMAN
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Chat Area */}
        <div className="glass-card" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          {detail ? (
            <>
              {/* Chat Header */}
              <div style={{ padding: '1.25rem', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
                    <div style={{ fontWeight: 600, fontSize: '1.125rem' }}>{detail.customer_name || detail.customer_phone}</div>
                    <span className={`lead-badge ${detail.customer_lead_score.toLowerCase()}`}>{detail.customer_lead_score}</span>
                  </div>
                  <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>{detail.customer_phone}</div>
                </div>
                <div>
                  <button
                    onClick={handleTakeover}
                    className={detail.session.is_human_takeover ? 'btn-outline' : 'btn-danger'}
                    style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                  >
                    {detail.session.is_human_takeover ? 'Resume AI Agent' : 'Takeover Conversation'}
                  </button>
                </div>
              </div>

              {/* Chat Messages */}
              <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {detail.messages.map((msg) => (
                  <div key={msg.id} className={`chat-bubble ${msg.direction.toLowerCase()}`}>
                    <div style={{ marginBottom: '0.25rem' }}>{msg.content}</div>
                    <div style={{ fontSize: '0.65rem', color: msg.direction === 'INBOUND' ? 'var(--text-muted)' : 'rgba(255,255,255,0.7)', textAlign: 'right' }}>
                      {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                ))}
              </div>

              {/* Chat Input */}
              <div style={{ padding: '1.25rem', borderTop: '1px solid var(--border)', background: 'var(--bg-card)' }}>
                {detail.session.is_human_takeover ? (
                  <div style={{ display: 'flex', gap: '0.75rem' }}>
                    <input
                      type="text"
                      className="input-field"
                      placeholder="Type a message to the customer..."
                      value={reply}
                      onChange={(e) => setReply(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    />
                    <button className="btn-primary" onClick={handleSend}>Send</button>
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.875rem', padding: '0.5rem 0' }}>
                    AI Agent is actively managing this conversation. Takeover to send manual messages.
                  </div>
                )}
              </div>
            </>
          ) : (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
              Select a conversation to view details
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
