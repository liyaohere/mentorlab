import { useState } from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { isLoggedIn, login, logout } from './api';
import DashboardPage from './pages/DashboardPage';
import ParticipantsPage from './pages/ParticipantsPage';
import ExportPage from './pages/ExportPage';
import PromptsPage from './pages/PromptsPage';
import SchedulePage from './pages/SchedulePage';
import './App.css';

function Nav() {
  return (
    <nav className="nav">
      <div className="nav-brand">MentorLab Admin</div>
      <div className="nav-links">
        <NavLink to="/" end>Dashboard</NavLink>
        <NavLink to="/participants">Participants</NavLink>
        <NavLink to="/prompts">Prompts</NavLink>
        <NavLink to="/schedule">Schedule</NavLink>
        <NavLink to="/export">Export</NavLink>
      </div>
      <button
        className="btn"
        style={{ marginLeft: 'auto', color: 'rgba(255,255,255,0.7)', background: 'none', border: '1px solid rgba(255,255,255,0.3)' }}
        onClick={() => { logout(); window.location.reload(); }}
      >
        Logout
      </button>
    </nav>
  );
}

function LoginPage() {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await login(password);
      window.location.reload();
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#FAFAF8' }}>
      <div style={{ background: 'white', borderRadius: 20, padding: 40, width: 400, boxShadow: '0 4px 24px rgba(0,0,0,0.06)', border: '1px solid #e8e8e8' }}>
        <h1 style={{ color: '#1B5E20', fontSize: 32, marginBottom: 4, fontFamily: "'Newsreader', serif" }}>MentorLab</h1>
        <p style={{ color: '#757575', marginBottom: 32 }}>Admin Dashboard</p>
        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter admin password"
              autoFocus
            />
          </div>
          {error && <div className="msg msg-error">{error}</div>}
          <button className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
            {loading ? 'Logging in...' : 'Log In'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function App() {
  if (!isLoggedIn()) {
    return <LoginPage />;
  }

  return (
    <BrowserRouter basename="/admin">
      <Nav />
      <main className="main">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/participants" element={<ParticipantsPage />} />
          <Route path="/prompts" element={<PromptsPage />} />
          <Route path="/schedule" element={<SchedulePage />} />
          <Route path="/export" element={<ExportPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
