export interface Participant {
  id: string;
  name: string;
  arm: 'c1' | 'c2' | 'c3';
  venture_name: string | null;
  venture_description: string | null;
  industry_vertical: string | null;
  status: 'enrolled' | 'active' | 'completed' | 'dropped';
  cohort_id: string | null;
  consent_at: string | null;
  audio_consent: boolean;
}

export interface Conversation {
  id: string;
  week_number: number | null;
  initiated_by: 'system' | 'participant';
  created_at: string;
  ended_at: string | null;
  last_message?: Message | null;
}

export interface Message {
  id: string;
  client_id: string | null;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  input_method: 'text' | 'voice';
  created_at: string;
  sync_status: 'synced' | 'pending' | 'failed';
}

export interface AuthResponse {
  participant_id: string;
  access_token: string;
  token_type: string;
  participant: Participant;
}

export interface SendMessageResponse {
  user_message: Message;
  assistant_message: Message;
}

export interface SyncResult {
  client_id: string;
  user_message: Message | null;
  assistant_message: Message | null;
  status: 'synced' | 'error';
  error: string | null;
}
