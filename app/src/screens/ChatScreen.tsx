import React, { useCallback, useRef, useState } from 'react';
import {
  View,
  Text,
  FlatList,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { useConversationStore } from '../stores/conversationStore';
import VoiceRecorder from '../components/VoiceRecorder';
import * as api from '../services/api';
import { Message } from '../types';
import { COLORS } from '../utils/constants';

function SyncIcon({ status }: { status: string }) {
  if (status === 'synced') return <Text style={styles.syncIcon}>✓</Text>;
  if (status === 'pending') return <Text style={[styles.syncIcon, styles.pendingIcon]}>◷</Text>;
  return <Text style={[styles.syncIcon, styles.failedIcon]}>!</Text>;
}

function MessageBubble({
  message,
  onRetry,
}: {
  message: Message;
  onRetry?: () => void;
}) {
  const isUser = message.role === 'user';

  return (
    <View style={[styles.bubbleRow, isUser ? styles.bubbleRowRight : styles.bubbleRowLeft]}>
      <View
        style={[
          styles.bubble,
          isUser ? styles.userBubble : styles.assistantBubble,
        ]}
      >
        {isUser && message.input_method === 'voice' && (
          <Text style={styles.voiceBadge}>🎤 Voice</Text>
        )}
        <Text style={isUser ? styles.userText : styles.assistantText}>
          {message.content}
        </Text>
      </View>
      <View style={[styles.meta, isUser ? styles.metaRight : styles.metaLeft]}>
        <Text style={styles.timeText}>
          {new Date(message.created_at).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </Text>
        {isUser && <SyncIcon status={message.sync_status} />}
        {message.sync_status === 'failed' && onRetry && (
          <TouchableOpacity onPress={onRetry}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

function TypingIndicator() {
  return (
    <View style={[styles.bubbleRow, styles.bubbleRowLeft]}>
      <View style={[styles.bubble, styles.assistantBubble, styles.typingBubble]}>
        <ActivityIndicator size="small" color={COLORS.textSecondary} />
        <Text style={styles.typingText}> Thinking...</Text>
      </View>
    </View>
  );
}

function TranscribingIndicator() {
  return (
    <View style={styles.transcribingBar}>
      <ActivityIndicator size="small" color={COLORS.primary} />
      <Text style={styles.transcribingText}>Transcribing voice...</Text>
    </View>
  );
}

export default function ChatScreen({ route }: any) {
  const { conversationId } = route.params;
  const { messages, isSending, fetchMessages, sendMessage, sendVoiceMessage, retryMessage } =
    useConversationStore();
  const [inputText, setInputText] = useState('');
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [voiceAudioUri, setVoiceAudioUri] = useState<string | null>(null);
  const flatListRef = useRef<FlatList>(null);

  const conversationMessages = messages[conversationId] || [];

  useFocusEffect(
    useCallback(() => {
      fetchMessages(conversationId);
    }, [conversationId]),
  );

  const handleSend = async () => {
    const text = inputText.trim();
    if (!text) return;

    const audioUri = voiceAudioUri;
    setInputText('');
    setVoiceAudioUri(null);

    if (audioUri) {
      // Voice message: send with input_method='voice' and audio_url
      await sendVoiceMessage(conversationId, text, audioUri);
    } else {
      await sendMessage(conversationId, text);
    }
  };

  const handleRecordingComplete = async (uri: string) => {
    setIsTranscribing(true);
    try {
      const result = await api.transcribeAudio(uri, conversationId);
      setInputText(result.transcript);
      setVoiceAudioUri(result.audio_url || uri);
    } catch (error: any) {
      Alert.alert(
        'Transcription Failed',
        error.message || 'Could not transcribe audio. Please type your message instead.',
      );
    } finally {
      setIsTranscribing(false);
    }
  };

  const renderItem = ({ item }: { item: Message }) => (
    <MessageBubble
      message={item}
      onRetry={
        item.sync_status === 'failed' && item.client_id
          ? () => retryMessage(item.client_id!)
          : undefined
      }
    />
  );

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      <FlatList
        ref={flatListRef}
        data={conversationMessages}
        keyExtractor={(item) => item.client_id || item.id}
        renderItem={renderItem}
        contentContainerStyle={styles.messageList}
        onContentSizeChange={() =>
          flatListRef.current?.scrollToEnd({ animated: true })
        }
        ListFooterComponent={isSending ? <TypingIndicator /> : null}
      />

      {isTranscribing && <TranscribingIndicator />}

      {voiceAudioUri && inputText && (
        <View style={styles.voicePreviewBar}>
          <Text style={styles.voicePreviewText}>🎤 Voice transcript — edit before sending</Text>
          <TouchableOpacity onPress={() => { setVoiceAudioUri(null); setInputText(''); }}>
            <Text style={styles.voicePreviewCancel}>Clear</Text>
          </TouchableOpacity>
        </View>
      )}

      <View style={styles.inputRow}>
        {!isTranscribing && (
          <>
            <TextInput
              style={styles.textInput}
              value={inputText}
              onChangeText={(text) => {
                setInputText(text);
                // If user edits the transcript significantly, clear voice context
                if (voiceAudioUri && text !== inputText) {
                  // Keep voiceAudioUri — the transcript was just edited
                }
              }}
              placeholder="Type a message..."
              placeholderTextColor={COLORS.textSecondary}
              multiline
              maxLength={2000}
            />
            {inputText.trim() ? (
              <TouchableOpacity style={styles.sendButton} onPress={handleSend}>
                <Text style={styles.sendIcon}>↑</Text>
              </TouchableOpacity>
            ) : (
              <VoiceRecorder
                onRecordingComplete={handleRecordingComplete}
                disabled={isSending}
              />
            )}
          </>
        )}
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.surface },
  messageList: { padding: 16, paddingBottom: 8 },
  bubbleRow: { marginBottom: 12 },
  bubbleRowLeft: { alignItems: 'flex-start' },
  bubbleRowRight: { alignItems: 'flex-end' },
  bubble: {
    maxWidth: '80%',
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  userBubble: {
    backgroundColor: COLORS.userBubble,
    borderBottomRightRadius: 4,
  },
  assistantBubble: {
    backgroundColor: COLORS.assistantBubble,
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  userText: { color: COLORS.textOnPrimary, fontSize: 15, lineHeight: 22 },
  assistantText: { color: COLORS.textPrimary, fontSize: 15, lineHeight: 22 },
  voiceBadge: { fontSize: 11, color: COLORS.textOnPrimary, opacity: 0.7, marginBottom: 2 },
  meta: { flexDirection: 'row', alignItems: 'center', marginTop: 4, gap: 4 },
  metaLeft: { paddingLeft: 4 },
  metaRight: { paddingRight: 4 },
  timeText: { fontSize: 11, color: COLORS.textSecondary },
  syncIcon: { fontSize: 12, color: COLORS.primaryLight },
  pendingIcon: { color: COLORS.pending },
  failedIcon: { color: COLORS.error, fontWeight: 'bold' },
  retryText: { fontSize: 12, color: COLORS.userBubble, fontWeight: '600', marginLeft: 4 },
  typingBubble: { flexDirection: 'row', alignItems: 'center' },
  typingText: { color: COLORS.textSecondary, fontSize: 13 },
  transcribingBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
    gap: 8,
    backgroundColor: COLORS.primary + '10',
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
  },
  transcribingText: { color: COLORS.primary, fontSize: 13, fontWeight: '500' },
  voicePreviewBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 6,
    backgroundColor: COLORS.primary + '10',
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
  },
  voicePreviewText: { fontSize: 12, color: COLORS.primary },
  voicePreviewCancel: { fontSize: 12, color: COLORS.error, fontWeight: '600' },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    padding: 12,
    paddingBottom: Platform.OS === 'ios' ? 28 : 12,
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
    backgroundColor: COLORS.background,
    minHeight: 64,
  },
  textInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 10,
    fontSize: 15,
    maxHeight: 100,
    color: COLORS.textPrimary,
    backgroundColor: COLORS.surface,
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 8,
  },
  sendIcon: { color: COLORS.textOnPrimary, fontSize: 20, fontWeight: 'bold' },
});
