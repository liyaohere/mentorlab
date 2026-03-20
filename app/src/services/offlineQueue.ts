import * as SQLite from 'expo-sqlite';
import { v4 as uuidv4 } from 'uuid';
import { Message, Conversation } from '../types';

let db: SQLite.SQLiteDatabase | null = null;

async function getDb(): Promise<SQLite.SQLiteDatabase> {
  if (!db) {
    db = await SQLite.openDatabaseAsync('mentorlab_offline.db');
    await db.execAsync(`
      CREATE TABLE IF NOT EXISTS local_messages (
        client_id TEXT PRIMARY KEY,
        server_id TEXT,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        input_method TEXT DEFAULT 'text',
        created_at TEXT NOT NULL,
        sync_status TEXT DEFAULT 'pending',
        retry_count INTEGER DEFAULT 0
      );
      CREATE TABLE IF NOT EXISTS local_conversations (
        id TEXT PRIMARY KEY,
        week_number INTEGER,
        initiated_by TEXT,
        created_at TEXT,
        last_synced_at TEXT
      );
    `);
  }
  return db;
}

export async function enqueueMessage(
  conversationId: string,
  content: string,
  inputMethod: string = 'text',
): Promise<Message> {
  const database = await getDb();
  const clientId = uuidv4();
  const createdAt = new Date().toISOString();

  await database.runAsync(
    'INSERT INTO local_messages (client_id, conversation_id, role, content, input_method, created_at, sync_status) VALUES (?, ?, ?, ?, ?, ?, ?)',
    [clientId, conversationId, 'user', content, inputMethod, createdAt, 'pending'],
  );

  return {
    id: clientId,
    client_id: clientId,
    conversation_id: conversationId,
    role: 'user',
    content,
    input_method: inputMethod as 'text' | 'voice',
    created_at: createdAt,
    sync_status: 'pending',
  };
}

export async function getPendingMessages(): Promise<Message[]> {
  const database = await getDb();
  const rows = await database.getAllAsync(
    "SELECT * FROM local_messages WHERE sync_status = 'pending' ORDER BY created_at",
  );
  return rows.map((row: any) => ({
    id: row.server_id || row.client_id,
    client_id: row.client_id,
    conversation_id: row.conversation_id,
    role: row.role,
    content: row.content,
    input_method: row.input_method,
    created_at: row.created_at,
    sync_status: row.sync_status,
  }));
}

export async function markSynced(clientId: string, serverId: string): Promise<void> {
  const database = await getDb();
  await database.runAsync(
    "UPDATE local_messages SET server_id = ?, sync_status = 'synced' WHERE client_id = ?",
    [serverId, clientId],
  );
}

export async function markFailed(clientId: string): Promise<void> {
  const database = await getDb();
  await database.runAsync(
    "UPDATE local_messages SET sync_status = 'failed', retry_count = retry_count + 1 WHERE client_id = ?",
    [clientId],
  );
}

export async function getRetryCount(clientId: string): Promise<number> {
  const database = await getDb();
  const row = await database.getFirstAsync(
    'SELECT retry_count FROM local_messages WHERE client_id = ?',
    [clientId],
  ) as any;
  return row?.retry_count || 0;
}

export async function incrementRetry(clientId: string): Promise<void> {
  const database = await getDb();
  await database.runAsync(
    'UPDATE local_messages SET retry_count = retry_count + 1 WHERE client_id = ?',
    [clientId],
  );
}

export async function resetFailed(clientId: string): Promise<void> {
  const database = await getDb();
  await database.runAsync(
    "UPDATE local_messages SET sync_status = 'pending', retry_count = 0 WHERE client_id = ?",
    [clientId],
  );
}

export async function cacheMessage(message: Message): Promise<void> {
  const database = await getDb();
  await database.runAsync(
    `INSERT OR REPLACE INTO local_messages (client_id, server_id, conversation_id, role, content, input_method, created_at, sync_status)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      message.client_id || message.id,
      message.id,
      message.conversation_id,
      message.role,
      message.content,
      message.input_method,
      message.created_at,
      'synced',
    ],
  );
}

export async function getCachedMessages(conversationId: string): Promise<Message[]> {
  const database = await getDb();
  const rows = await database.getAllAsync(
    'SELECT * FROM local_messages WHERE conversation_id = ? ORDER BY created_at',
    [conversationId],
  );
  return rows.map((row: any) => ({
    id: row.server_id || row.client_id,
    client_id: row.client_id,
    conversation_id: row.conversation_id,
    role: row.role,
    content: row.content,
    input_method: row.input_method,
    created_at: row.created_at,
    sync_status: row.sync_status,
  }));
}

export async function cacheConversation(conversation: Conversation): Promise<void> {
  const database = await getDb();
  await database.runAsync(
    `INSERT OR REPLACE INTO local_conversations (id, week_number, initiated_by, created_at, last_synced_at)
     VALUES (?, ?, ?, ?, ?)`,
    [conversation.id, conversation.week_number, conversation.initiated_by, conversation.created_at, new Date().toISOString()],
  );
}

export async function getCachedConversations(): Promise<Conversation[]> {
  const database = await getDb();
  const rows = await database.getAllAsync(
    'SELECT * FROM local_conversations ORDER BY created_at DESC',
  );
  return rows.map((row: any) => ({
    id: row.id,
    week_number: row.week_number,
    initiated_by: row.initiated_by,
    created_at: row.created_at,
    ended_at: null,
  }));
}
