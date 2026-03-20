import { API_URL } from '../utils/constants';
import { AuthResponse, Conversation, Message, SendMessageResponse, SyncResult } from '../types';

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Auth
export async function register(data: {
  invite_code: string;
  name: string;
  phone_number?: string;
  venture_name?: string;
  venture_description?: string;
  industry_vertical?: string;
}): Promise<AuthResponse> {
  return request('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function recordConsent(data: {
  study_consent: boolean;
  audio_consent: boolean;
}): Promise<any> {
  return request('/api/v1/me/consent', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateProfile(data: Record<string, any>): Promise<any> {
  return request('/api/v1/me', {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

// Conversations
export async function listConversations(): Promise<{ conversations: Conversation[] }> {
  return request('/api/v1/conversations');
}

export async function createConversation(): Promise<{
  conversation: Conversation;
  messages: Message[];
}> {
  return request('/api/v1/conversations', { method: 'POST' });
}

export async function getConversation(id: string): Promise<{
  conversation: Conversation;
  messages: Message[];
}> {
  return request(`/api/v1/conversations/${id}`);
}

// Messages
export async function sendMessage(
  conversationId: string,
  content: string,
  clientId: string,
  inputMethod: string = 'text',
  audioUrl: string | null = null,
): Promise<SendMessageResponse> {
  return request(`/api/v1/conversations/${conversationId}/messages`, {
    method: 'POST',
    body: JSON.stringify({
      content,
      input_method: inputMethod,
      client_id: clientId,
      audio_url: audioUrl,
    }),
  });
}

// Sync
export async function syncMessages(
  messages: Array<{
    conversation_id: string;
    content: string;
    input_method: string;
    client_id: string;
    created_at?: string;
  }>,
): Promise<{ results: SyncResult[] }> {
  return request('/api/v1/sync/messages', {
    method: 'POST',
    body: JSON.stringify({ messages }),
  });
}

// Voice transcription
export async function transcribeAudio(
  audioUri: string,
  conversationId: string = '',
): Promise<{ transcript: string; audio_url: string | null }> {
  const formData = new FormData();

  // Create file object from local URI
  const filename = audioUri.split('/').pop() || 'audio.m4a';
  const match = /\.(\w+)$/.exec(filename);
  const ext = match ? match[1] : 'm4a';
  const mimeType = ext === 'wav' ? 'audio/wav' : ext === 'mp3' ? 'audio/mpeg' : 'audio/m4a';

  formData.append('audio', {
    uri: audioUri,
    name: filename,
    type: mimeType,
  } as any);
  formData.append('conversation_id', conversationId);

  const headers: Record<string, string> = {};
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  const response = await fetch(`${API_URL}/api/v1/voice/transcribe`, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Transcription failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}
