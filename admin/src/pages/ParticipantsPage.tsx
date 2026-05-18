import { useEffect, useRef, useState } from 'react';
import { getParticipants, uploadParticipantsCSV } from '../api';

export default function ParticipantsPage() {
  const [participants, setParticipants] = useState<any[]>([]);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = () => getParticipants().then((d) => setParticipants(d.participants)).catch(console.error);
  useEffect(() => { load(); }, []);

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    try {
      const result = await uploadParticipantsCSV(file);
      setUploadResult(result);
      load();
    } catch (e: any) {
      setUploadResult({ errors: [e.message] });
    }
  };

  return (
    <div>
      <h1 className="page-title">Participants</h1>

      <div className="card">
        <div className="card-title">Upload CSV</div>
        <p style={{ fontSize: 13, color: '#757575', marginBottom: 12 }}>
          CSV columns: name, phone, arm (c1/c2/c3), cohort, industry_vertical
        </p>
        <div className="btn-row">
          <input type="file" accept=".csv" ref={fileRef} />
          <button className="btn btn-primary" onClick={handleUpload}>Upload</button>
        </div>
        {uploadResult && (
          <div className={`msg ${uploadResult.errors?.length ? 'msg-error' : 'msg-success'}`} style={{ marginTop: 12 }}>
            {uploadResult.created != null && <p>Created {uploadResult.created} invite codes</p>}
            {uploadResult.errors?.map((e: string, i: number) => <p key={i}>{e}</p>)}
            {uploadResult.codes?.map((c: any) => (
              <p key={c.invite_code} style={{ fontSize: 13 }}>
                {c.name} → <strong>{c.invite_code}</strong> ({c.arm})
              </p>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-title">All Participants ({participants.length})</div>
        <table>
          <thead>
            <tr>
              <th>Name</th><th>Arm</th><th>Status</th><th>Venture</th>
              <th>Cohort</th><th>Code</th><th>Convs</th><th>Msgs</th>
            </tr>
          </thead>
          <tbody>
            {participants.map((p) => (
              <tr key={p.id}>
                <td>{p.name}</td>
                <td><span className={`badge badge-${p.arm}`}>{p.arm}</span></td>
                <td><span className={`badge badge-${p.status}`}>{p.status}</span></td>
                <td>{p.venture_name || '—'}</td>
                <td>{p.cohort_id || '—'}</td>
                <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{p.invite_code}</td>
                <td>{p.conversation_count}</td>
                <td>{p.message_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
