const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Admin API key — set after login, persisted in sessionStorage
let adminKey: string | null = sessionStorage.getItem('admin_key');

export function setAdminKey(key: string) {
  adminKey = key;
  sessionStorage.setItem('admin_key', key);
}

export function getAdminKey(): string | null {
  return adminKey;
}

export function logout() {
  adminKey = null;
  sessionStorage.removeItem('admin_key');
}

export function isLoggedIn(): boolean {
  return !!adminKey;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (adminKey) {
    headers['X-Admin-Key'] = adminKey;
  }

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (response.status === 401) {
    logout();
    window.location.reload();
    throw new Error('Session expired');
  }
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

// Login
export async function login(password: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/admin/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Login failed' }));
    throw new Error(err.detail || 'Invalid password');
  }
  const data = await response.json();
  setAdminKey(data.api_key);
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
  const headers: Record<string, string> = {};
  if (adminKey) headers['X-Admin-Key'] = adminKey;
  const response = await fetch(`${API_URL}/api/v1/admin/participants/upload`, {
    method: 'POST',
    headers,
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

// Export (download URLs need the key as query param since <a> tags can't set headers)
export const exportTranscriptsUrl = (cohort?: string) => {
  const params = new URLSearchParams();
  if (cohort) params.set('cohort_id', cohort);
  return `${API_URL}/api/v1/admin/export/transcripts?${params}`;
};
export const exportSurveysUrl = (cohort?: string) => {
  const params = new URLSearchParams();
  if (cohort) params.set('cohort_id', cohort);
  return `${API_URL}/api/v1/admin/export/surveys?${params}`;
};
