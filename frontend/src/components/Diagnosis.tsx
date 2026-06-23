// frontend/src/components/Diagnosis.tsx
import { useState, useEffect, useRef } from 'preact/hooks';
import { useStore } from '../store';
import { apiFetch } from '../utils/api';

export function Diagnosis() {
  const { conversationId, condition, setPhase, setDiagnosisData } = useStore();
  const [loading, setLoading] = useState(true);
  const [diagnoses, setDiagnoses] = useState<string[]>([]);
  const [promptText, setPromptText] = useState('');

  // C3 专用的选择状态
  const [selectedReading, setSelectedReading] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // 隐形计时器
  const startTimeRef = useRef<number>(0);

  // 挂载时立即请求 AI 生成诊断
  useEffect(() => {
    async function fetchDiagnosis() {
      if (!conversationId) return;
      try {
        const data = await apiFetch<any>(`/interview/${conversationId}/generate-diagnosis`, {
          method: 'POST'
        });
        setDiagnoses(data.diagnoses);
        setPromptText(data.response_prompt);
        // 数据加载完毕，开始计时
        startTimeRef.current = Date.now();
      } catch (err) {
        console.error("Diagnosis generation failed", err);
      } finally {
        setLoading(false);
      }
    }
    fetchDiagnosis();
  }, [conversationId]);

  const handleContinue = async () => {
    if (!conversationId) return;
    setSubmitting(true);

    // 计算阅读时间 (秒)
    const readingTimeSeconds = Math.round((Date.now() - startTimeRef.current) / 1000);
    setDiagnosisData(promptText, readingTimeSeconds);

    try {
      // 如果是 C3 条件，需要把选择结果发给后端
      if (condition === 'competing' && selectedReading !== null) {
        await apiFetch(`/interview/${conversationId}/selection`, {
          method: 'POST',
          body: JSON.stringify({ selection_choice: selectedReading })
        });
      }
      setPhase('response');
    } catch (err) {
      console.error("Failed to submit selection", err);
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="diagnosis-loading">
        <div className="spinner"></div>
        <p>Analyzing your business context...</p>
        <p className="sub-text">This usually takes 15-30 seconds.</p>
      </div>
    );
  }

  // C3 实验组：暴露分歧
  if (condition === 'competing') {
    const labels = ["One reading of your situation:", "A different reading:", "A third possibility:"];

    return (
      <div className="diagnosis-container">
        <h2>We analyzed your situation</h2>
        <p className="instruction">Please review these different perspectives on your core challenge.</p>

        <div className="cards-wrapper">
          {diagnoses.map((diag, index) => (
            <div
              key={index}
              className={`diagnosis-card ${selectedReading === index ? 'selected' : ''}`}
              onClick={() => setSelectedReading(index)}
            >
              <h3 className="card-label">{labels[index]}</h3>
              <p>{diag}</p>
            </div>
          ))}
        </div>

        <div className="selection-area">
          <p className="selection-question">Which of the three readings is closest to how you see your situation?</p>
          <button
            className="btn-primary full-width"
            onClick={handleContinue}
            disabled={selectedReading === null || submitting}
          >
            {submitting ? 'Processing...' : 'Continue'}
          </button>
        </div>
      </div>
    );
  }

  // C1 和 C2 实验组：展示单一结果
  return (
    <div className="diagnosis-container">
      <h2>Your Business Diagnosis</h2>
      <div className="diagnosis-card single">
        <p>{diagnoses[0]}</p>
      </div>
      <button
        className="btn-primary full-width"
        onClick={handleContinue}
        disabled={submitting}
      >
        {submitting ? 'Processing...' : 'Continue'}
      </button>
    </div>
  );
}
