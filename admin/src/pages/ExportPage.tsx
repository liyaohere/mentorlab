import { exportTranscriptsUrl, exportSurveysUrl } from '../api';

export default function ExportPage() {
  return (
    <div>
      <h1 className="page-title">Data Export</h1>

      <div className="card">
        <div className="card-title">Chat Transcripts</div>
        <p style={{ fontSize: 13, color: '#757575', marginBottom: 12 }}>
          Download all chat messages as CSV. Columns: participant_id, name, arm, cohort,
          conversation_id, week_number, initiated_by, role, content, input_method, timestamp.
        </p>
        <a className="btn btn-primary" href={exportTranscriptsUrl()} download style={{ textDecoration: 'none' }}>
          Download Transcripts CSV
        </a>
      </div>

      <div className="card">
        <div className="card-title">Survey Responses</div>
        <p style={{ fontSize: 13, color: '#757575', marginBottom: 12 }}>
          Download all survey responses as CSV. Columns: participant_id, name, arm, cohort,
          survey_type, week_number, completed_at, responses_json.
        </p>
        <a className="btn btn-primary" href={exportSurveysUrl()} download style={{ textDecoration: 'none' }}>
          Download Surveys CSV
        </a>
      </div>
    </div>
  );
}
