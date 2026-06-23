import { useStore } from './store';
import { Login } from './components/Login';
import { Intake } from './components/Intake';
import { Diagnosis } from './components/Diagnosis';
import { Response } from './components/Response';
import { Survey } from './components/Survey';
import './style.css';

export function App() {
  const { phase, logout } = useStore();

  return (
    <main>
      {phase === 'login' && <Login />}
      {phase === 'intake' && <Intake />}
      {(phase === 'analyzing' || phase === 'diagnosis') && <Diagnosis />}
      {phase === 'response' && <Response />}
      {phase === 'survey' && <Survey />}
      {phase === 'complete' && (
        <div className="complete-screen">
          <h1>Thank You!</h1>
          <p>Your responses have been successfully recorded.</p>
          <button className="btn-secondary" onClick={logout} style={{ marginTop: 24 }}>
            Return to Home
          </button>
        </div>
      )}
    </main>
  );
}
