import { useEffect, useState } from 'react';
import { exportTranscriptsUrl, exportSurveysUrl } from '../api';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ExportRecord {
  id: string;
  type: string;
  cohort_id: string | null;
  row_count: number;
  downloaded_at: string;
}

export default function ExportPage() {
  const [history, setHistory] = useState<ExportRecord[]>([]);

  const loadHistory = () => {
    fetch(`${API_URL}/api/v1/admin/export/history`)
      .then((r) => r.json())
      .then((d) => setHistory(d.exports || []))
      .catch(console.error);
  };

  useEffect(() => { loadHistory(); }, []);

  // Reload history after download (small delay for the server to log it)
  const handleDownload = () => {
    setTimeout(loadHistory, 2000);
  };

  return (
    <div>
      <h1 className="page-title">Data Export</h1>

      <div className="card">
        <div className="card-title">Chat Transcripts</div>
        <p style={{ fontSize: 13, color: '#757575', marginBottom: 12 }}>
          Download all chat messages as CSV. Each file has a timestamped name.<br />
          Columns include <strong>conversation_number</strong> (sequential per participant) and{' '}
          <strong>message_order</strong> (sequential within a conversation) so you can group
          messages that belong to the same chat session.
        </p>
        <a
          className="btn btn-primary"
          href={exportTranscriptsUrl()}
          download
          onClick={handleDownload}
          style={{ textDecoration: 'none' }}
        >
          Download Transcripts CSV
        </a>
      </div>

      <div className="card">
        <div className="card-title">Survey Responses</div>
        <p style={{ fontSize: 13, color: '#757575', marginBottom: 12 }}>
          Download all survey responses as CSV. Each file has a timestamped name.
        </p>
        <a
          className="btn btn-primary"
          href={exportSurveysUrl()}
          download
          onClick={handleDownload}
          style={{ textDecoration: 'none' }}
        >
          Download Surveys CSV
        </a>
      </div>

      <div className="card">
        <div className="card-title">Download History</div>
        {history.length === 0 ? (
          <p style={{ fontSize: 13, color: '#757575' }}>No exports yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Type</th>
                <th>Rows</th>
                <th>Cohort</th>
                <th>Downloaded At</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.id}>
                  <td>
                    <span className={`badge ${h.type === 'transcripts' ? 'badge-analytic' : 'badge-constructive'}`}>
                      {h.type}
                    </span>
                  </td>
                  <td>{h.row_count} rows</td>
                  <td>{h.cohort_id || 'all'}</td>
                  <td>{h.downloaded_at ? new Date(h.downloaded_at).toLocaleString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
