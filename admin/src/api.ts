const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

// Dashboard
export const getDashboard = (cohort?: string) =>
  request<any>(`/api/v1/admin/dashboard${cohort ? `?cohort_id=${cohort}` : ''}`);

// Participants
export const getParticipants = (cohort?: string) =>
  request<any>(`/api/v1/admin/participants${cohort ? `?cohort_id=${cohort}` : ''}`);

export async function uploadParticipantsCSV(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch(`${API_URL}/api/v1/admin/participants/upload`, {
    method: 'POST',
    body: formData,
  });
  return response.json();
}

// Prompts
export const getPrompt = (arm: string) => request<any>(`/api/v1/admin/prompts/${arm}`);
export const updatePrompt = (arm: string, content: string) =>
  request<any>(`/api/v1/admin/prompts`, { method: 'PUT', body: JSON.stringify({ arm, content }) });

// Schedule
export const getSchedule = (cohortId: string) =>
  request<any>(`/api/v1/admin/schedule/${cohortId}`);
export const setSchedule = (data: any) =>
  request<any>(`/api/v1/admin/schedule`, { method: 'PUT', body: JSON.stringify(data) });
export const triggerConversations = (cohortId: string) =>
  request<any>(`/api/v1/admin/trigger/${cohortId}`, { method: 'POST' });

// Export (returns download URLs)
export const exportTranscriptsUrl = (cohort?: string) =>
  `${API_URL}/api/v1/admin/export/transcripts${cohort ? `?cohort_id=${cohort}` : ''}`;
export const exportSurveysUrl = (cohort?: string) =>
  `${API_URL}/api/v1/admin/export/surveys${cohort ? `?cohort_id=${cohort}` : ''}`;
