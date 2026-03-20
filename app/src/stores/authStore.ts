import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import * as api from '../services/api';
import { Participant } from '../types';

interface AuthState {
  token: string | null;
  participant: Participant | null;
  isLoading: boolean;
  isReady: boolean;

  loadToken: () => Promise<void>;
  register: (data: {
    invite_code: string;
    name: string;
    phone_number?: string;
    venture_name?: string;
    venture_description?: string;
    industry_vertical?: string;
  }) => Promise<void>;
  recordConsent: (studyConsent: boolean, audioConsent: boolean) => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  participant: null,
  isLoading: false,
  isReady: false,

  loadToken: async () => {
    try {
      const token = await SecureStore.getItemAsync('auth_token');
      const participantJson = await SecureStore.getItemAsync('participant');
      if (token && participantJson) {
        api.setAuthToken(token);
        set({
          token,
          participant: JSON.parse(participantJson),
          isReady: true,
        });
      } else {
        set({ isReady: true });
      }
    } catch {
      set({ isReady: true });
    }
  },

  register: async (data) => {
    set({ isLoading: true });
    try {
      const response = await api.register(data);
      await SecureStore.setItemAsync('auth_token', response.access_token);
      await SecureStore.setItemAsync('participant', JSON.stringify(response.participant));
      api.setAuthToken(response.access_token);
      set({
        token: response.access_token,
        participant: response.participant,
        isLoading: false,
      });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  recordConsent: async (studyConsent: boolean, audioConsent: boolean) => {
    set({ isLoading: true });
    try {
      const updated = await api.recordConsent({
        study_consent: studyConsent,
        audio_consent: audioConsent,
      });
      await SecureStore.setItemAsync('participant', JSON.stringify(updated));
      set({ participant: updated, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  logout: async () => {
    await SecureStore.deleteItemAsync('auth_token');
    await SecureStore.deleteItemAsync('participant');
    api.setAuthToken(null);
    set({ token: null, participant: null });
  },
}));
