import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
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
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
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
