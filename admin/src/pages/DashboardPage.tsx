import { useEffect, useState } from 'react';
import { getDashboard } from '../api';

const ARM_COLORS: Record<string, string> = {
  control: '#1565C0',
  analytic: '#E65100',
  constructive: '#2E7D32',
};
const ARM_LABELS: Record<string, string> = {
  control: 'Control',
  analytic: 'Info Optimization',
  constructive: 'Reframing',
};

export default function DashboardPage() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="msg msg-error">{error}</div>;
  if (!data) return <p style={{ padding: 24, color: '#9e9e9e' }}>Loading dashboard...</p>;

  const totalMsgs = data.total_user_messages + data.total_ai_messages;

  return (
    <div>
      <h1 className="page-title">Dashboard</h1>

      {/* Top-level stats */}
      <div className="stat-grid">
        <div className="stat-card stat-card-accent">
          <div className="stat-value">{data.total_participants}</div>
          <div className="stat-label">Participants</div>
        </div>
        <div className="stat-card stat-card-secondary">
          <div className="stat-value">{data.total_conversations}</div>
          <div className="stat-label">Conversations</div>
        </div>
        <div className="stat-card stat-card-info">
          <div className="stat-value">{totalMsgs}</div>
          <div className="stat-label">Total Messages</div>
        </div>
        <div className="stat-card stat-card-warn">
          <div className="stat-value">${data.estimated_ai_cost_usd}</div>
          <div className="stat-label">Est. Token Cost</div>
        </div>
      </div>

      {/* Activity + Input Methods row */}
      <div className="section-grid">
        <div className="card">
          <div className="card-title">Activity</div>
          <div className="metric-row">
            <span className="metric-label">Messages today</span>
            <span className="metric-value">{data.messages_today}</span>
          </div>
          <div className="metric-row">
            <span className="metric-label">Messages this week</span>
            <span className="metric-value">{data.messages_this_week}</span>
          </div>
          <div className="metric-row">
            <span className="metric-label">Avg messages / conversation</span>
            <span className="metric-value">{data.avg_messages_per_conversation}</span>
          </div>
          <div className="metric-row">
            <span className="metric-label">Participants with memory</span>
            <span className="metric-value">{data.participants_with_memory}</span>
          </div>
        </div>

        <div className="card">
          <div className="card-title">Input Methods</div>
          {Object.entries(data.input_methods || {}).map(([method, count]) => {
            const pct = totalMsgs > 0 ? Math.round(((count as number) / data.total_user_messages) * 100) : 0;
            return (
              <div key={method} style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14 }}>
                  <span style={{ textTransform: 'capitalize' }}>{method}</span>
                  <span style={{ fontWeight: 600 }}>{count as number} ({pct}%)</span>
                </div>
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${pct}%`, background: method === 'voice' ? '#1B5E20' : '#9e9e9e' }} />
                </div>
              </div>
            );
          })}
          <div className="metric-row" style={{ marginTop: 8 }}>
            <span className="metric-label">User messages</span>
            <span className="metric-value">{data.total_user_messages}</span>
          </div>
          <div className="metric-row">
            <span className="metric-label">AI messages</span>
            <span className="metric-value">{data.total_ai_messages}</span>
          </div>
        </div>
      </div>

      {/* Arms breakdown + Status row */}
      <div className="section-grid">
        <div className="card">
          <div className="card-title">Experiment Arms</div>
          {['control', 'analytic', 'constructive'].map((arm) => {
            const participants = data.by_arm?.[arm] || 0;
            const msgs = data.user_messages_by_arm?.[arm] || 0;
            const convs = data.conversations_by_arm?.[arm] || 0;
            return (
              <div className="arm-row" key={arm}>
                <div className="arm-name">
                  <span className={`badge badge-${arm}`}>{ARM_LABELS[arm]}</span>
                </div>
                <div className="arm-stats">
                  {participants} participants · {convs} convs · {msgs} msgs
                </div>
              </div>
            );
          })}
        </div>

        <div className="card">
          <div className="card-title">Participant Status</div>
          {Object.entries(data.by_status || {}).map(([status, count]) => {
            const pct = data.total_participants > 0 ? Math.round(((count as number) / data.total_participants) * 100) : 0;
            return (
              <div key={status} style={{ marginBottom: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14 }}>
                  <span><span className={`badge badge-${status}`}>{status}</span></span>
                  <span style={{ fontWeight: 600 }}>{count as number} ({pct}%)</span>
                </div>
                <div className="progress-bar">
                  <div className="progress-fill" style={{
                    width: `${pct}%`,
                    background: status === 'active' ? '#2E7D32' : status === 'enrolled' ? '#E65100' : '#C62828',
                  }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent conversations */}
      <div className="card">
        <div className="card-title">Recent Conversations</div>
        {(data.recent_conversations || []).length === 0 ? (
          <p style={{ color: '#9e9e9e', fontSize: 14, padding: '12px 0' }}>No conversations yet</p>
        ) : (
          data.recent_conversations.map((c: any) => (
            <div className="recent-item" key={c.id}>
              <span className={`badge badge-${c.arm}`} style={{ width: 90, textAlign: 'center' }}>
                {ARM_LABELS[c.arm] || c.arm}
              </span>
              <div style={{ flex: 1 }}>
                <div className="recent-title">{c.title}</div>
                <div className="recent-meta">{c.participant} · Week {c.week || '?'}</div>
              </div>
              <div className="recent-meta">
                {new Date(c.created_at).toLocaleDateString()} {new Date(c.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
