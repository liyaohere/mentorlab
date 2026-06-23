// frontend/src/components/Intake.tsx
import { useState, useEffect, useRef } from 'preact/hooks';
import { useStore } from '../store';
import { apiFetch } from '../utils/api';
import { VoiceInput } from './VoiceInput';

interface Message {
  id: string;
  role: 'ai' | 'user';
  text: string;
}

export function Intake() {
  const { setInterviewData, setPhase } = useStore();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [convId, setConvId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    async function startInterview() {
      try {
        const data = await apiFetch<any>('/interview/start', { method: 'POST' });
        setConvId(data.conversation_id);
        setInterviewData(data.conversation_id, data.condition);
        setMessages([{ id: 'init', role: 'ai', text: data.first_question }]);
      } catch (err) {
        console.error("Failed to start interview", err);
      } finally {
        setLoading(false);
      }
    }
    startInterview();
  }, []);

  const handleSend = async (e: Event) => {
    e.preventDefault();
    if (!input.trim() || !convId || loading) return;

    const userText = input.trim();
    setInput('');
    setLoading(true);
    setMessages(prev => [...prev, { id: Date.now().toString(), role: 'user', text: userText }]);

    try {
      const data = await apiFetch<any>(`/interview/${convId}/intake`, {
        method: 'POST',
        body: JSON.stringify({ answer: userText, question_index: questionIndex }),
      });

      if (data.intake_complete) {
        setMessages(prev => [...prev, { id: 'done', role: 'ai', text: 'Thank you. Give me a moment to analyze your situation...' }]);
        setTimeout(() => setPhase('analyzing'), 1500);
      } else {
        const acks = ["Got it.", "Thank you.", "Thanks for sharing that."];
        const ack = acks[questionIndex % acks.length];
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          role: 'ai',
          text: `${ack} ${data.next_question}`
        }]);
        setQuestionIndex(prev => prev + 1);
      }
    } catch (err) {
      console.error("Failed to send answer", err);
      setMessages(prev => [...prev, { id: 'err', role: 'ai', text: 'Network error, please try again.' }]);
    } finally {
      setLoading(false);
    }
  };

  // 处理语音识别返回的结果
  const handleTranscription = (text: string) => {
    // 追加到输入框现有内容的末尾，并加个空格
    setInput(prev => prev ? `${prev} ${text}` : text);
  };

  return (
    <div className="chat-layout">
      <header className="chat-header">
        <h2>Your AI Advisor</h2>
      </header>

      <div className="chat-messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`chat-bubble-row ${msg.role}`}>
            <div className={`chat-bubble ${msg.role}`}>
              <span className="bubble-label">{msg.role === 'ai' ? 'AI Advisor' : 'You'}</span>
              <p>{msg.text}</p>
            </div>
          </div>
        ))}
        {loading && messages.length > 0 && (
          <div className="chat-bubble-row ai">
            <div className="chat-bubble ai thinking">Thinking...</div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-area" onSubmit={handleSend}>
        <input
          type="text"
          className="chat-input"
          placeholder="Type or speak your answer..."
          value={input}
          onInput={(e) => setInput((e.target as HTMLInputElement).value)}
          disabled={loading}
        />

        {/* 在发送按钮左侧插入语音按钮 */}
        {convId && (
          <VoiceInput
            conversationId={convId}
            onTranscription={handleTranscription}
            disabled={loading}
          />
        )}

        <button type="submit" className="chat-submit" disabled={!input.trim() || loading}>
          Send
        </button>
      </form>
    </div>
  );
}
