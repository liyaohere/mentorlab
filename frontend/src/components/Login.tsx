// frontend/src/components/Login.tsx
import { useState } from 'preact/hooks';
import { useStore } from '../store';
import { apiFetch } from '../utils/api';

export function Login() {
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { setAuth, setPhase } = useStore();

  const handleLogin = async (e: Event) => {
    e.preventDefault();
    if (!code.trim()) return;

    setLoading(true);
    setError('');

    try {
      // Assuming a simplified login/register flow using just the invite code
      const data = await apiFetch<any>('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ invite_code: code.trim().toUpperCase(), name: 'Participant' }),
      });

      setAuth(data.access_token);
      setPhase('intake');
    } catch (err: any) {
      setError('Invalid invite code or network error.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-screen">
      <div className="login-card">
        <h1 className="logo">MentorLab</h1>
        <p className="tagline">AI-powered business interview</p>

        <form className="form-box" onSubmit={handleLogin}>
          <label className="field-label">Invite Code</label>
          <input
            type="text"
            className="code-input"
            placeholder="ENTER CODE"
            maxLength={8}
            value={code}
            onInput={(e) => setCode((e.target as HTMLInputElement).value)}
            disabled={loading}
          />

          {error && <div className="error-msg">{error}</div>}

          <button type="submit" className="btn-primary" disabled={loading || !code}>
            {loading ? 'Loading...' : 'Start Interview'}
          </button>
        </form>
      </div>
    </div>
  );
}
