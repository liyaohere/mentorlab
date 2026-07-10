// frontend/src/components/Response.tsx
import { useState, useEffect, useRef } from 'preact/hooks';
import { useStore } from '../store';
import { apiFetch } from '../utils/api';
import { VoiceInput } from './VoiceInput';

export function Response() {
  const { conversationId, responsePrompt, readingTime, setPhase } = useStore();
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);

  const startTimeRef = useRef<number>(0);

  useEffect(() => {
    startTimeRef.current = Date.now();
  }, []);

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    if (!text.trim() || !conversationId || loading) return;

    setLoading(true);
    const writingTimeSeconds = Math.round((Date.now() - startTimeRef.current) / 1000);

    try {
      await apiFetch(`/interview/${conversationId}/response`, {
        method: 'POST',
        body: JSON.stringify({
          text: text.trim(),
          reading_time_seconds: readingTime,
          writing_time_seconds: writingTimeSeconds
        })
      });
      setPhase('survey');
    } catch (err) {
      console.error("Failed to submit response", err);
      setLoading(false);
    }
  };

  const handleTranscription = (transcript: string) => {
    setText(prev => prev ? `${prev} ${transcript}` : transcript);
  };

  return (
    <div className="chat-layout">
      <header className="chat-header">
        <h2>Your Plan</h2>
      </header>

      <div className="chat-messages" style={{ paddingBottom: 0 }}>
        <div className="chat-bubble-row ai">
          <div className="chat-bubble ai">
            <span className="bubble-label">AI Advisor</span>
            <p>{responsePrompt}</p>
          </div>
        </div>
      </div>

      <div className="response-area">
        <form onSubmit={handleSubmit} className="response-form">
          <textarea
            className="response-textarea"
            placeholder="Type or speak your answer here..."
            value={text}
            onInput={(e) => setText((e.target as HTMLTextAreaElement).value)}
            disabled={loading}
          />

          <div style={{ display: 'flex', gap: '12px' }}>
            {conversationId && (
              <VoiceInput
                conversationId={conversationId}
                onTranscription={handleTranscription}
                disabled={loading}
              />
            )}

            <button
              type="submit"
              className="btn-primary"
              style={{ flex: 1 }}
              disabled={!text.trim() || loading}
            >
              {loading ? 'Submitting...' : 'Submit'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
