'use client';

import { useState } from 'react';

export default function SettingsPage() {
  const [systemPrompt, setSystemPrompt] = useState(
    "You are an AI sales assistant for an automotive dealership. Your goal is to qualify leads and schedule test drives. Only recommend cars from our inventory. Never promise discounts."
  );
  const [openwaUrl, setOpenwaUrl] = useState("http://openwa-api:2785");
  const [sessionId, setSessionId] = useState("session_01");

  return (
    <div className="animate-fade-in" style={{ maxWidth: '800px' }}>
      <div style={{ marginBottom: '2.5rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '0.5rem' }}>AI Agent Settings</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
          Configure the AI's behavior, connection to OpenWA, and business details.
        </p>
      </div>

      <div className="glass-card" style={{ marginBottom: '2rem' }}>
        <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border)' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>System Prompt (Brain)</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            This defines how the AI talks to customers. It is sent as the system instruction to Gemini/OpenAI.
          </p>
        </div>
        <div style={{ padding: '1.5rem' }}>
          <textarea
            className="input-field"
            style={{ minHeight: '150px', resize: 'vertical', fontFamily: 'monospace', fontSize: '0.875rem' }}
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
          />
          <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'flex-end' }}>
            <button className="btn-primary">Save Prompt</button>
          </div>
        </div>
      </div>

      <div className="glass-card" style={{ marginBottom: '2rem' }}>
        <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border)' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>OpenWA Integration</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            Connect to your internal OpenWA instance to send/receive WhatsApp messages.
          </p>
        </div>
        <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: 500 }}>
              OpenWA Base URL
            </label>
            <input
              type="text"
              className="input-field"
              value={openwaUrl}
              onChange={(e) => setOpenwaUrl(e.target.value)}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: 500 }}>
              WhatsApp Session ID
            </label>
            <input
              type="text"
              className="input-field"
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="status-dot online" />
              <span style={{ fontSize: '0.875rem', color: '#10b981', fontWeight: 500 }}>Connected to WhatsApp</span>
            </div>
            <button className="btn-primary">Update Connection</button>
          </div>
        </div>
      </div>

      <div className="glass-card">
        <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border)' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#ef4444' }}>Danger Zone</h2>
        </div>
        <div style={{ padding: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: '1rem' }}>Clear all conversations</div>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>This will delete all sessions and messages for this tenant.</div>
          </div>
          <button className="btn-danger">Clear Data</button>
        </div>
      </div>
    </div>
  );
}
