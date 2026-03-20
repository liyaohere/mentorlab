import NetInfo from '@react-native-community/netinfo';
import * as api from './api';
import * as offlineQueue from './offlineQueue';
import { Message } from '../types';

let isSyncing = false;
let syncListeners: Array<(messages: Message[]) => void> = [];
let errorListeners: Array<(error: string) => void> = [];

const MAX_RETRY_COUNT = 3;
const RETRY_DELAYS = [2000, 4000, 8000]; // exponential backoff

export function onSyncComplete(listener: (messages: Message[]) => void) {
  syncListeners.push(listener);
  return () => {
    syncListeners = syncListeners.filter((l) => l !== listener);
  };
}

export function onSyncError(listener: (error: string) => void) {
  errorListeners.push(listener);
  return () => {
    errorListeners = errorListeners.filter((l) => l !== listener);
  };
}

function notifySyncComplete(messages: Message[]) {
  syncListeners.forEach((listener) => listener(messages));
}

function notifySyncError(error: string) {
  errorListeners.forEach((listener) => listener(error));
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function syncPendingMessages(): Promise<void> {
  if (isSyncing) return;

  const netState = await NetInfo.fetch();
  if (!netState.isConnected) return;

  const pending = await offlineQueue.getPendingMessages();
  if (pending.length === 0) return;

  isSyncing = true;
  try {
    const syncPayload = pending.map((msg) => ({
      conversation_id: msg.conversation_id,
      content: msg.content,
      input_method: msg.input_method,
      client_id: msg.client_id!,
      created_at: msg.created_at,
    }));

    const response = await api.syncMessages(syncPayload);
    const newMessages: Message[] = [];

    for (const result of response.results) {
      if (result.status === 'synced' && result.user_message) {
        await offlineQueue.markSynced(result.client_id, result.user_message.id);
        if (result.assistant_message) {
          await offlineQueue.cacheMessage(result.assistant_message);
          newMessages.push(result.assistant_message);
        }
      } else {
        const retryCount = await offlineQueue.getRetryCount(result.client_id);
        if (retryCount >= MAX_RETRY_COUNT) {
          await offlineQueue.markFailed(result.client_id);
          notifySyncError(
            `Message failed to send after ${MAX_RETRY_COUNT} attempts. Tap to retry.`,
          );
        } else {
          await offlineQueue.markFailed(result.client_id);
        }
      }
    }

    if (newMessages.length > 0) {
      notifySyncComplete(newMessages);
    }
  } catch (error) {
    // Network error — retry with backoff instead of immediately marking failed
    for (const msg of pending) {
      if (msg.client_id) {
        const retryCount = await offlineQueue.getRetryCount(msg.client_id);
        if (retryCount >= MAX_RETRY_COUNT) {
          await offlineQueue.markFailed(msg.client_id);
          notifySyncError(
            `Some messages couldn't be sent. Check your connection and tap to retry.`,
          );
        } else {
          // Leave as pending — will be retried on next sync
          await offlineQueue.incrementRetry(msg.client_id);
        }
      }
    }

    // Schedule a retry with backoff
    const nextRetry = RETRY_DELAYS[Math.min(pending.length - 1, RETRY_DELAYS.length - 1)];
    setTimeout(() => {
      syncPendingMessages();
    }, nextRetry);
  } finally {
    isSyncing = false;
  }
}

// Start listening for network changes
let unsubscribe: (() => void) | null = null;

export function startSyncListener() {
  if (unsubscribe) return;
  unsubscribe = NetInfo.addEventListener((state) => {
    if (state.isConnected) {
      syncPendingMessages();
    }
  });
}

export function stopSyncListener() {
  if (unsubscribe) {
    unsubscribe();
    unsubscribe = null;
  }
}
