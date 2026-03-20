import React, { useCallback, useEffect, useState } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  Alert,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { useConversationStore } from '../stores/conversationStore';
import { useAuthStore } from '../stores/authStore';
import { Conversation } from '../types';
import { COLORS, API_URL } from '../utils/constants';
import { startSyncListener } from '../services/syncService';
import UpdateBanner from '../components/UpdateBanner';

function formatTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

interface PendingSurvey {
  survey_type: string;
  title: string;
  description: string;
  week_number: number | null;
}

export default function ConversationListScreen({ navigation }: any) {
  const { conversations, isLoading, fetchConversations, createConversation } =
    useConversationStore();
  const { token } = useAuthStore();
  const [pendingSurveys, setPendingSurveys] = useState<PendingSurvey[]>([]);

  useEffect(() => {
    startSyncListener();
  }, []);

  const fetchPendingSurveys = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/surveys/pending`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setPendingSurveys(data);
      }
    } catch {}
  };

  useFocusEffect(
    useCallback(() => {
      fetchConversations();
      fetchPendingSurveys();
    }, []),
  );

  const handleNewConversation = async () => {
    try {
      const convId = await createConversation();
      navigation.navigate('Chat', { conversationId: convId });
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Could not start conversation. Check your connection.');
    }
  };

  const renderItem = ({ item }: { item: Conversation }) => {
    const preview = item.last_message?.content || 'No messages yet';
    const truncated = preview.length > 60 ? preview.substring(0, 60) + '...' : preview;
    // Show unread dot if last message is from assistant (AI sent a new message)
    const hasUnread = item.last_message?.role === 'assistant' && item.initiated_by === 'system';

    return (
      <TouchableOpacity
        style={styles.card}
        onPress={() => navigation.navigate('Chat', { conversationId: item.id })}
      >
        <View style={styles.cardHeader}>
          <View style={styles.weekRow}>
            {hasUnread && <View style={styles.unreadDot} />}
            <Text style={[styles.weekLabel, hasUnread && styles.weekLabelUnread]}>
              Week {item.week_number || '?'}
            </Text>
          </View>
          <Text style={styles.timestamp}>
            {formatTime(item.last_message?.created_at || item.created_at)}
          </Text>
        </View>
        <Text style={[styles.preview, hasUnread && styles.previewUnread]} numberOfLines={2}>
          {truncated}
        </Text>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      <UpdateBanner />

      {pendingSurveys.length > 0 && (
        <TouchableOpacity
          style={styles.surveyBanner}
          onPress={() => {
            const survey = pendingSurveys[0];
            navigation.navigate('Survey', {
              surveyType: survey.survey_type,
              weekNumber: survey.week_number,
              title: survey.title,
            });
          }}
        >
          <Text style={styles.surveyBannerText}>
            📋 {pendingSurveys[0].title} — Tap to complete
          </Text>
        </TouchableOpacity>
      )}

      <FlatList
        data={conversations}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        refreshControl={
          <RefreshControl refreshing={isLoading} onRefresh={fetchConversations} />
        }
        contentContainerStyle={conversations.length === 0 ? styles.empty : styles.list}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyTitle}>No conversations yet</Text>
            <Text style={styles.emptyText}>
              Your mentor will reach out soon, or tap + to start a conversation.
            </Text>
          </View>
        }
      />

      <TouchableOpacity style={styles.fab} onPress={handleNewConversation}>
        <Text style={styles.fabText}>+</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.surface },
  surveyBanner: {
    backgroundColor: COLORS.warning + '20',
    borderBottomWidth: 1,
    borderBottomColor: COLORS.warning + '40',
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  surveyBannerText: { fontSize: 14, color: COLORS.warning, fontWeight: '600' },
  list: { padding: 16 },
  card: {
    backgroundColor: COLORS.background,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  weekRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  unreadDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: COLORS.primary,
  },
  weekLabel: { fontSize: 16, fontWeight: '600', color: COLORS.primary },
  weekLabelUnread: { fontWeight: '700' },
  timestamp: { fontSize: 12, color: COLORS.textSecondary },
  preview: { fontSize: 14, color: COLORS.textSecondary, lineHeight: 20 },
  previewUnread: { color: COLORS.textPrimary, fontWeight: '500' },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32 },
  emptyContainer: { alignItems: 'center' },
  emptyTitle: { fontSize: 18, fontWeight: '600', color: COLORS.textPrimary, marginBottom: 8 },
  emptyText: { fontSize: 14, color: COLORS.textSecondary, textAlign: 'center', lineHeight: 20 },
  fab: {
    position: 'absolute',
    bottom: 24,
    right: 24,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
  },
  fabText: { color: COLORS.textOnPrimary, fontSize: 28, fontWeight: '300', marginTop: -2 },
});
