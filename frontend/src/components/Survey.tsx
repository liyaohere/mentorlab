// frontend/src/components/Survey.tsx
import { useState } from 'preact/hooks';
import { useStore } from '../store';
import { apiFetch } from '../utils/api';

const SURVEY_QUESTIONS = [
  { key: 'cognitive_load', label: 'How mentally demanding was this task?' },
  { key: 'perceived_confusion', label: 'How clear was the advice you received?' },
  { key: 'trust_in_advice', label: 'To what extent did you trust the advice?' },
  { key: 'confidence', label: 'How confident are you in the cause you identified?' },
  { key: 'ownership', label: 'To what extent does this plan feel like YOUR plan?' },
  { key: 'perceived_disagreement', label: 'To what extent did the causes in the advice feel in tension with one another?' },
  { key: 'perceived_breadth', label: 'To what extent did the advice cover multiple dimensions of your strategic situation?' }
];

export function Survey() {
  const { conversationId, setPhase, logout } = useStore();
  const [scores, setScores] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);

  const handleSelect = (key: string, value: number) => {
    setScores(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async () => {
    if (Object.keys(scores).length < SURVEY_QUESTIONS.length) {
      alert("Please answer all questions before submitting.");
      return;
    }

    setLoading(true);
    try {
      await apiFetch(`/interview/${conversationId}/survey`, {
        method: 'POST',
        body: JSON.stringify(scores)
      });
      setPhase('complete');
    } catch (err) {
      console.error("Survey submission failed", err);
      setLoading(false);
    }
  };

  return (
    <div className="survey-container">
      <h2>Quick Feedback</h2>
      <p className="instruction">Please rate your experience from 1 (Not at all) to 7 (Extremely).</p>

      <div className="survey-list">
        {SURVEY_QUESTIONS.map(q => (
          <div key={q.key} className="survey-item">
            <label>{q.label}</label>
            <div className="likert-scale">
              {[1, 2, 3, 4, 5, 6, 7].map(val => (
                <button
                  key={val}
                  type="button"
                  className={`likert-btn ${scores[q.key] === val ? 'selected' : ''}`}
                  onClick={() => handleSelect(q.key, val)}
                >
                  {val}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <button className="btn-primary full-width" onClick={handleSubmit} disabled={loading}>
        {loading ? 'Submitting...' : 'Finish Interview'}
      </button>
    </div>
  );
}
