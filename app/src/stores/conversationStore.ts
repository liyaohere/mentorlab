import { create } from 'zustand';
import * as api from '../services/api';
import * as offlineQueue from '../services/offlineQueue';
import { syncPendingMessages, onSyncComplete } from '../services/syncService';
import { Conversation, Message } from '../types';
import { v4 as uuidv4 } from 'uuid';

interface ConversationState {
  conversations: Conversation[];
  messages: Record<string, Message[]>; // keyed by conversation_id
  isLoading: boolean;
  isSending: boolean;

  fetchConversations: () => Promise<void>;
  fetchMessages: (conversationId: string) => Promise<void>;
  createConversation: () => Promise<string>; // returns conversation_id
  sendMessage: (conversationId: string, content: string) => Promise<void>;
  sendVoiceMessage: (conversationId: string, content: string, audioUrl: string) => Promise<void>;
  retryMessage: (clientId: string) => Promise<void>;
}

export const useConversationStore = create<ConversationState>((set, get) => ({
  conversations: [],
  messages: {},
  isLoading: false,
  isSending: false,

  fetchConversations: async () => {
    set({ isLoading: true });
    try {
      const response = await api.listConversations();
      // Cache conversations locally
      for (const conv of response.conversations) {
        await offlineQueue.cacheConversation(conv);
      }
      set({ conversations: response.conversations, isLoading: false });
    } catch {
      // Fall back to cached data
      const cached = await offlineQueue.getCachedConversations();
      set({ conversations: cached, isLoading: false });
    }
  },

  fetchMessages: async (conversationId: string) => {
    set({ isLoading: true });
    try {
      const response = await api.getConversation(conversationId);
      // Cache messages locally
      for (const msg of response.messages) {
        await offlineQueue.cacheMessage(msg);
      }
      set((state) => ({
        messages: { ...state.messages, [conversationId]: response.messages },
        isLoading: false,
      }));
    } catch {
      // Fall back to cached data
      const cached = await offlineQueue.getCachedMessages(conversationId);
      set((state) => ({
        messages: { ...state.messages, [conversationId]: cached },
        isLoading: false,
      }));
    }
  },

  createConversation: async () => {
    set({ isLoading: true });
    try {
      const response = await api.createConversation();
      const conv = response.conversation;
      // Set last_message from the greeting
      if (response.messages.length > 0) {
        conv.last_message = response.messages[response.messages.length - 1];
      }
      // Cache
      await offlineQueue.cacheConversation(conv);
      for (const msg of response.messages) {
        await offlineQueue.cacheMessage(msg);
      }
      set((state) => ({
        conversations: [conv, ...state.conversations],
        messages: { ...state.messages, [conv.id]: response.messages },
        isLoading: false,
      }));
      return conv.id;
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  sendMessage: async (conversationId: string, content: string) => {
    // 1. Create optimistic local message
    const localMsg = await offlineQueue.enqueueMessage(conversationId, content);

    // 2. Add to state immediately
    set((state) => ({
      messages: {
        ...state.messages,
        [conversationId]: [...(state.messages[conversationId] || []), localMsg],
      },
    }));

    set({ isSending: true });

    try {
      // 3. Try to send to server
      const response = await api.sendMessage(
        conversationId,
        content,
        localMsg.client_id!,
      );

      // 4. Update local message to synced, add AI response
      await offlineQueue.markSynced(localMsg.client_id!, response.user_message.id);
      await offlineQueue.cacheMessage(response.assistant_message);

      set((state) => {
        const msgs = state.messages[conversationId] || [];
        const updated = msgs.map((m) =>
          m.client_id === localMsg.client_id
            ? { ...m, id: response.user_message.id, sync_status: 'synced' as const }
            : m,
        );
        return {
          messages: {
            ...state.messages,
            [conversationId]: [...updated, response.assistant_message],
          },
          isSending: false,
        };
      });
    } catch {
      // Message stays as pending — sync service will retry
      set({ isSending: false });
    }
  },

  sendVoiceMessage: async (conversationId: string, content: string, audioUrl: string) => {
    // Same as sendMessage but with input_method='voice' and audio_url
    const localMsg = await offlineQueue.enqueueMessage(conversationId, content, 'voice');

    set((state) => ({
      messages: {
        ...state.messages,
        [conversationId]: [...(state.messages[conversationId] || []), localMsg],
      },
    }));

    set({ isSending: true });

    try {
      const response = await api.sendMessage(
        conversationId,
        content,
        localMsg.client_id!,
        'voice',
        audioUrl,
      );

      await offlineQueue.markSynced(localMsg.client_id!, response.user_message.id);
      await offlineQueue.cacheMessage(response.assistant_message);

      set((state) => {
        const msgs = state.messages[conversationId] || [];
        const updated = msgs.map((m) =>
          m.client_id === localMsg.client_id
            ? { ...m, id: response.user_message.id, sync_status: 'synced' as const }
            : m,
        );
        return {
          messages: {
            ...state.messages,
            [conversationId]: [...updated, response.assistant_message],
          },
          isSending: false,
        };
      });
    } catch {
      set({ isSending: false });
    }
  },

  retryMessage: async (clientId: string) => {
    await offlineQueue.resetFailed(clientId);
    await syncPendingMessages();
  },
}));

// Listen for sync completions to update state
onSyncComplete((newMessages) => {
  const state = useConversationStore.getState();
  for (const msg of newMessages) {
    const convId = msg.conversation_id;
    const existing = state.messages[convId] || [];
    useConversationStore.setState({
      messages: {
        ...state.messages,
        [convId]: [...existing, msg],
      },
    });
  }
});
