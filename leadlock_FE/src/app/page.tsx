'use client';

import { useEffect, useState } from 'react';
import type { Analytics } from '@/lib/api';
import { api, DEMO_TENANT_ID } from '@/lib/api';

// Mock data for demo — replace with api.getAnalytics() in production
const mockAnalytics: Analytics = {
  overview: {
    total_customers: 1284,
    total_sessions: 3847,
    active_sessions_24h: 42,
    total_messages: 28493,
    inbound_messages: 14891,
    outbound_messages: 13602,
  },
  lead_distribution: { COLD: 687, WARM: 412, HOT: 185 },
  funnel_breakdown: { BROWSING: 2100, QUALIFYING: 980, SCHEDULING: 520, ESCALATED: 247 },
  response_ratio: { ai_managed: 3412, human_managed: 435 },
  messages_per_day: Array.from({ length: 30 }, (_, i) => ({
    date: new Date(Date.now() - (29 - i) * 86400000).toISOString().split('T')[0],
    count: Math.floor(Math.random() * 500) + 600,
  })),
};

export default function OverviewPage() {
  const [data, setData] = useState<Analytics | null>(null);

  useEffect(() => {
    api.getAnalytics(DEMO_TENANT_ID).then(setData).catch(console.error);
  }, []);

  if (!data) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
        <div style={{ color: 'var(--text-muted)' }}>Loading analytics...</div>
      </div>
    );
  }

  const kpis = [
    {
      label: 'Total Leads',
      value: data.overview.total_customers.toLocaleString(),
      icon: '👥',
      trend: '+12.5%',
      trendUp: true,
    },
    {
      label: 'Active Sessions',
      value: data.overview.active_sessions_24h.toString(),
      icon: '💬',
      trend: '+8.2%',
      trendUp: true,
    },
    {
      label: 'Messages Today',
      value: data.messages_per_day[data.messages_per_day.length - 1]?.count.toLocaleString() || '0',
      icon: '📨',
      trend: '+3.1%',
      trendUp: true,
    },
    {
      label: 'AI Response Rate',
      value: `${Math.round((data.response_ratio.ai_managed / (data.response_ratio.ai_managed + data.response_ratio.human_managed)) * 100)}%`,
      icon: '🤖',
      trend: '+2.4%',
      trendUp: true,
    },
  ];

  const maxMessages = Math.max(...data.messages_per_day.map((d) => d.count));

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '0.5rem' }}>
          Dashboard Overview
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
          Real-time performance metrics across all conversations and leads
        </p>
      </div>

      {/* KPI Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '1.25rem',
          marginBottom: '2rem',
        }}
      >
        {kpis.map((kpi, i) => (
          <div key={kpi.label} className={`kpi-card animate-fade-in delay-${i + 1}`}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
                  {kpi.label}
                </div>
                <div style={{ fontSize: '2rem', fontWeight: 700, lineHeight: 1 }}>
                  {kpi.value}
                </div>
              </div>
              <div style={{ fontSize: '1.5rem' }}>{kpi.icon}</div>
            </div>
            <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
              <span style={{ color: kpi.trendUp ? '#10b981' : '#ef4444', fontSize: '0.75rem', fontWeight: 600 }}>
                {kpi.trendUp ? '↑' : '↓'} {kpi.trend}
              </span>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>vs last month</span>
            </div>
          </div>
        ))}
      </div>

      {/* Charts Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.25rem', marginBottom: '2rem' }}>
        {/* Messages Chart */}
        <div className="glass-card" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: '1rem' }}>Messages Over Time</div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Last 30 days</div>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              Total: {data.overview.total_messages.toLocaleString()}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: '3px', height: '160px' }}>
            {data.messages_per_day.map((day, i) => (
              <div
                key={i}
                style={{
                  flex: 1,
                  height: `${(day.count / maxMessages) * 100}%`,
                  background: `linear-gradient(180deg, var(--accent-primary), rgba(99, 102, 241, 0.3))`,
                  borderRadius: '3px 3px 0 0',
                  minHeight: '4px',
                  transition: 'height 0.5s ease',
                  opacity: 0.7 + (i / data.messages_per_day.length) * 0.3,
                }}
                title={`${day.date}: ${day.count} messages`}
              />
            ))}
          </div>
        </div>

        {/* Lead Distribution */}
        <div className="glass-card" style={{ padding: '1.5rem' }}>
          <div style={{ fontWeight: 600, fontSize: '1rem', marginBottom: '1.5rem' }}>
            Lead Distribution
          </div>
          {Object.entries(data.lead_distribution).map(([score, count]) => {
            const total = Object.values(data.lead_distribution).reduce((a, b) => a + b, 0);
            const pct = ((count / total) * 100).toFixed(1);
            const color = score === 'HOT' ? 'var(--hot)' : score === 'WARM' ? 'var(--warm)' : 'var(--cold)';

            return (
              <div key={score} style={{ marginBottom: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className={`lead-badge ${score.toLowerCase()}`}>{score}</span>
                  </div>
                  <span style={{ fontSize: '0.875rem', fontWeight: 600 }}>{count}</span>
                </div>
                <div style={{ height: '6px', background: 'var(--bg-primary)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${pct}%`,
                      background: color,
                      borderRadius: '3px',
                      transition: 'width 1s ease',
                    }}
                  />
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                  {pct}% of total leads
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
        {/* Funnel Breakdown */}
        <div className="glass-card" style={{ padding: '1.5rem' }}>
          <div style={{ fontWeight: 600, fontSize: '1rem', marginBottom: '1.25rem' }}>
            Funnel Breakdown
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            {Object.entries(data.funnel_breakdown).map(([stage, count]) => {
              const stageColors: Record<string, string> = {
                BROWSING: 'var(--browsing)',
                QUALIFYING: 'var(--qualifying)',
                SCHEDULING: 'var(--scheduling)',
                ESCALATED: 'var(--escalated)',
              };
              return (
                <div
                  key={stage}
                  style={{
                    padding: '1rem',
                    background: 'var(--bg-primary)',
                    borderRadius: 'var(--radius-sm)',
                    borderLeft: `3px solid ${stageColors[stage] || '#6366f1'}`,
                  }}
                >
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.375rem' }}>
                    {stage}
                  </div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{count}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* AI vs Human */}
        <div className="glass-card" style={{ padding: '1.5rem' }}>
          <div style={{ fontWeight: 600, fontSize: '1rem', marginBottom: '1.25rem' }}>
            AI vs Human Response
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
            {/* Donut-like visual */}
            <div style={{ position: 'relative', width: 120, height: 120 }}>
              <svg viewBox="0 0 36 36" style={{ transform: 'rotate(-90deg)', width: '100%', height: '100%' }}>
                <circle cx="18" cy="18" r="15.9" fill="none" stroke="var(--bg-primary)" strokeWidth="3" />
                <circle
                  cx="18" cy="18" r="15.9" fill="none"
                  stroke="var(--accent-primary)"
                  strokeWidth="3"
                  strokeDasharray={`${(data.response_ratio.ai_managed / (data.response_ratio.ai_managed + data.response_ratio.human_managed)) * 100}, 100`}
                  strokeLinecap="round"
                />
              </svg>
              <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                  {Math.round((data.response_ratio.ai_managed / (data.response_ratio.ai_managed + data.response_ratio.human_managed)) * 100)}%
                </div>
                <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>AI</div>
              </div>
            </div>
            <div>
              <div style={{ marginBottom: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: 'var(--accent-primary)' }} />
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>AI Managed</span>
                </div>
                <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>
                  {data.response_ratio.ai_managed.toLocaleString()}
                </div>
              </div>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: 'var(--warm)' }} />
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Human Managed</span>
                </div>
                <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>
                  {data.response_ratio.human_managed.toLocaleString()}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
