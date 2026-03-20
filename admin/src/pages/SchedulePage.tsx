import { useState } from 'react';
import { getSchedule, setSchedule, triggerConversations } from '../api';

export default function SchedulePage() {
  const [cohortId, setCohortId] = useState('pilot_2026');
  const [dayOfWeek, setDayOfWeek] = useState('mon');
  const [hour, setHour] = useState(6);
  const [minute, setMinute] = useState(0);
  const [msg, setMsg] = useState('');
  const [triggerMsg, setTriggerMsg] = useState('');

  const loadSchedule = async () => {
    try {
      const data = await getSchedule(cohortId);
      setDayOfWeek(data.day_of_week);
      setHour(data.hour);
      setMinute(data.minute);
      setMsg('');
    } catch (e: any) {
      setMsg(e.message);
    }
  };

  const handleSave = async () => {
    try {
      await setSchedule({ cohort_id: cohortId, day_of_week: dayOfWeek, hour, minute, timezone: 'UTC' });
      setMsg('Schedule updated.');
    } catch (e: any) {
      setMsg(e.message);
    }
  };

  const handleTrigger = async () => {
    setTriggerMsg('Triggering...');
    try {
      await triggerConversations(cohortId || 'all');
      setTriggerMsg('Conversations triggered successfully!');
    } catch (e: any) {
      setTriggerMsg(`Error: ${e.message}`);
    }
  };

  return (
    <div>
      <h1 className="page-title">Scheduled Sends</h1>

      <div className="card">
        <div className="card-title">Cohort Schedule</div>
        <div className="form-group">
          <label>Cohort ID</label>
          <div className="btn-row">
            <input value={cohortId} onChange={(e) => setCohortId(e.target.value)} style={{ flex: 1 }} />
            <button className="btn btn-secondary" onClick={loadSchedule}>Load</button>
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
          <div className="form-group">
            <label>Day of Week</label>
            <select value={dayOfWeek} onChange={(e) => setDayOfWeek(e.target.value)}>
              {['mon','tue','wed','thu','fri','sat','sun'].map((d) => (
                <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Hour (UTC)</label>
            <input type="number" min={0} max={23} value={hour} onChange={(e) => setHour(+e.target.value)} />
          </div>
          <div className="form-group">
            <label>Minute</label>
            <input type="number" min={0} max={59} value={minute} onChange={(e) => setMinute(+e.target.value)} />
          </div>
        </div>
        <p style={{ fontSize: 12, color: '#757575', marginBottom: 12 }}>
          EAT (East Africa Time) = UTC + 3. So 06:00 UTC = 09:00 EAT.
        </p>
        {msg && <div className="msg msg-success">{msg}</div>}
        <button className="btn btn-primary" onClick={handleSave}>Save Schedule</button>
      </div>

      <div className="card">
        <div className="card-title">Manual Trigger</div>
        <p style={{ fontSize: 13, color: '#757575', marginBottom: 12 }}>
          Manually fire AI-initiated conversations for testing. This will create a new conversation
          and send a push notification to every active participant in the cohort.
        </p>
        {triggerMsg && <div className="msg msg-success">{triggerMsg}</div>}
        <button className="btn btn-danger" onClick={handleTrigger}>
          Trigger Conversations Now
        </button>
      </div>
    </div>
  );
}
