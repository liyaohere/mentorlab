import { useEffect, useState } from 'react';
import { getDashboard } from '../api';

export default function DashboardPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => { getDashboard().then(setData).catch(console.error); }, []);

  if (!data) return <p>Loading...</p>;

  return (
    <div>
      <h1 className="page-title">Dashboard</h1>

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-value">{data.total_participants}</div>
          <div className="stat-label">Total Participants</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.by_status?.active || 0}</div>
          <div className="stat-label">Active</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.total_ai_messages}</div>
          <div className="stat-label">AI Messages Sent</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">${data.estimated_ai_cost_usd}</div>
          <div className="stat-label">Est. AI Cost</div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Participants by Arm</div>
        <table>
          <thead><tr><th>Arm</th><th>Count</th><th>User Messages</th></tr></thead>
          <tbody>
            {['control', 'analytic', 'constructive'].map((arm) => (
              <tr key={arm}>
                <td><span className={`badge badge-${arm}`}>{arm}</span></td>
                <td>{data.by_arm?.[arm] || 0}</td>
                <td>{data.user_messages_by_arm?.[arm] || 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <div className="card-title">Input Methods</div>
        <table>
          <thead><tr><th>Method</th><th>Count</th></tr></thead>
          <tbody>
            {Object.entries(data.input_methods || {}).map(([method, count]) => (
              <tr key={method}><td>{method}</td><td>{count as number}</td></tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <div className="card-title">Status Breakdown</div>
        <table>
          <thead><tr><th>Status</th><th>Count</th></tr></thead>
          <tbody>
            {Object.entries(data.by_status || {}).map(([status, count]) => (
              <tr key={status}>
                <td><span className={`badge badge-${status}`}>{status}</span></td>
                <td>{count as number}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
