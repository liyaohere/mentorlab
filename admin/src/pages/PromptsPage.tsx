import { useEffect, useState } from 'react';
import { getPrompt, updatePrompt } from '../api';

const ARMS = ['c1', 'c2', 'c3'];
const ARM_LABELS: Record<string, string> = {
  c1: 'C1 Single',
  c2: 'C2 Integrated',
  c3: 'C3 Competing',
};

export default function PromptsPage() {
  const [selectedArm, setSelectedArm] = useState('c1');
  const [content, setContent] = useState('');
  const [original, setOriginal] = useState('');
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');

  const load = (arm: string) => {
    getPrompt(arm).then((d) => {
      setContent(d.content);
      setOriginal(d.content);
      setMsg('');
    }).catch((e) => setMsg(e.message));
  };

  useEffect(() => { load(selectedArm); }, [selectedArm]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updatePrompt(selectedArm, content);
      setOriginal(content);
      setMsg('Prompt updated successfully.');
    } catch (e: any) {
      setMsg(e.message);
    } finally {
      setSaving(false);
    }
  };

  const hasChanges = content !== original;

  return (
    <div>
      <h1 className="page-title">System Prompts</h1>

      <div className="btn-row" style={{ marginBottom: 16 }}>
        {ARMS.map((arm) => (
          <button
            key={arm}
            className={`btn ${selectedArm === arm ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSelectedArm(arm)}
          >
            {ARM_LABELS[arm] || arm}
          </button>
        ))}
      </div>

      {msg && <div className="msg msg-success">{msg}</div>}

      <div className="card">
        <div className="card-title">Arm: {selectedArm}</div>
        <div className="form-group">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            spellCheck={false}
          />
        </div>
        <div className="btn-row">
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving || !hasChanges}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
          {hasChanges && (
            <button className="btn btn-secondary" onClick={() => setContent(original)}>
              Revert
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
