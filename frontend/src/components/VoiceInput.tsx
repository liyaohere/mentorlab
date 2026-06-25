import { useState, useRef } from 'preact/hooks';
import { apiFetch } from '../utils/api';

interface VoiceInputProps {
  conversationId: string;
  onTranscription: (text: string) => void;
  disabled?: boolean;
}

export function VoiceInput({ conversationId, onTranscription, disabled }: VoiceInputProps) {
  const [status, setStatus] = useState<'idle' | 'recording' | 'transcribing'>('idle');
  const [seconds, setSeconds] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);

  const getMimeType = () => {
    const types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg', 'audio/wav'];
    for (const t of types) {
      if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(t)) {
        return t;
      }
    }
    return '';
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = getMimeType();

      mediaRecorderRef.current = new MediaRecorder(stream, mimeType ? { mimeType } : {});
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorderRef.current.onstop = handleStop;
      mediaRecorderRef.current.start();

      setStatus('recording');
      setSeconds(0);
      timerRef.current = window.setInterval(() => setSeconds(s => s + 1), 1000);
    } catch (err) {
      console.error("Microphone access denied or error:", err);
      alert("Microphone access is required for voice input.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && status === 'recording') {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(t => t.stop());
    }
  };

  const handleStop = async () => {
    if (timerRef.current) clearInterval(timerRef.current);
    setStatus('transcribing');

    const mimeType = mediaRecorderRef.current?.mimeType || 'audio/webm';
    const blob = new Blob(audioChunksRef.current, { type: mimeType });

    const formData = new FormData();
    const ext = mimeType.includes('mp4') ? 'm4a' : mimeType.includes('wav') ? 'wav' : 'webm';

    formData.append('audio', blob, `recording.${ext}`);
    formData.append('conversation_id', conversationId);

    try {
      const token = localStorage.getItem('token');
      const API_BASE = import.meta.env.DEV ? '/api/v1' : 'https://your-production-url.com/api/v1';

      const res = await fetch(`${API_BASE}/voice/transcribe`, {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        body: formData
      });

      if (!res.ok) throw new Error("Transcription failed");
      const data = await res.json();

      onTranscription(data.transcript || data.text);
    } catch (err) {
      console.error("Upload failed", err);
      alert("Transcription failed. Please try again or type your answer.");
    } finally {
      setStatus('idle');
    }
  };

  if (status === 'transcribing') {
    return <div className="voice-status">Transcribing your voice...</div>;
  }

  if (status === 'recording') {
    return (
      <div className="voice-status recording">
        <span className="rec-dot"></span>
        Recording: 0:{seconds.toString().padStart(2, '0')}
        <button type="button" className="btn-stop-rec" onClick={stopRecording}>Stop</button>
      </div>
    );
  }

  return (
    <button
      type="button"
      className="btn-mic"
      onClick={startRecording}
      disabled={disabled}
      title="Tap to speak"
    >
      🎤
    </button>
  );
}
