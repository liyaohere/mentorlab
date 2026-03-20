import React, { useCallback, useEffect, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { COLORS } from '../utils/constants';
import { API_URL } from '../utils/constants';
import * as api from '../services/api';

interface SurveyQuestion {
  id: string;
  text: string;
  type: 'text' | 'number' | 'likert' | 'choice' | 'multi_choice';
  required: boolean;
  options?: string[];
  min_value?: number;
  max_value?: number;
  min_label?: string;
  max_label?: string;
}

interface SurveyConfig {
  type: string;
  title: string;
  description: string;
  questions: SurveyQuestion[];
}

function LikertScale({
  question,
  value,
  onChange,
}: {
  question: SurveyQuestion;
  value: number | null;
  onChange: (v: number) => void;
}) {
  const min = question.min_value || 1;
  const max = question.max_value || 5;
  const points = Array.from({ length: max - min + 1 }, (_, i) => min + i);

  return (
    <View>
      <View style={styles.likertRow}>
        {points.map((p) => (
          <TouchableOpacity
            key={p}
            style={[styles.likertButton, value === p && styles.likertSelected]}
            onPress={() => onChange(p)}
          >
            <Text style={[styles.likertText, value === p && styles.likertTextSelected]}>
              {p}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
      <View style={styles.likertLabels}>
        <Text style={styles.likertLabel}>{question.min_label}</Text>
        <Text style={styles.likertLabel}>{question.max_label}</Text>
      </View>
    </View>
  );
}

function ChoiceGroup({
  options,
  value,
  onChange,
}: {
  options: string[];
  value: string | null;
  onChange: (v: string) => void;
}) {
  return (
    <View>
      {options.map((opt) => (
        <TouchableOpacity
          key={opt}
          style={[styles.choiceOption, value === opt && styles.choiceSelected]}
          onPress={() => onChange(opt)}
        >
          <View style={[styles.radio, value === opt && styles.radioSelected]} />
          <Text style={styles.choiceText}>{opt}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

export default function SurveyScreen({ route, navigation }: any) {
  const { surveyType, weekNumber, title: surveyTitle } = route.params;
  const [config, setConfig] = useState<SurveyConfig | null>(null);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    loadConfig();
  }, [surveyType]);

  const loadConfig = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/surveys/config/${surveyType}`);
      const data = await response.json();
      setConfig(data);
    } catch {
      Alert.alert('Error', 'Could not load survey.');
    } finally {
      setIsLoading(false);
    }
  };

  const setAnswer = (questionId: string, value: any) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  const handleSubmit = async () => {
    if (!config) return;

    // Validate required fields
    for (const q of config.questions) {
      if (q.required && (answers[q.id] === undefined || answers[q.id] === '')) {
        Alert.alert('Required', `Please answer: "${q.text}"`);
        return;
      }
    }

    setIsSubmitting(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/surveys`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${(await import('../stores/authStore')).useAuthStore.getState().token}`,
        },
        body: JSON.stringify({
          survey_type: surveyType,
          week_number: weekNumber || null,
          responses: answers,
        }),
      });

      if (response.ok) {
        Alert.alert('Thank you!', 'Your responses have been recorded.', [
          { text: 'OK', onPress: () => navigation.goBack() },
        ]);
      } else {
        Alert.alert('Error', 'Could not submit survey. Please try again.');
      }
    } catch {
      Alert.alert('Error', 'Could not submit survey. Check your connection.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={COLORS.primary} />
      </View>
    );
  }

  if (!config) {
    return (
      <View style={styles.centered}>
        <Text>Could not load survey.</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>{config.title}</Text>
      {config.description ? (
        <Text style={styles.description}>{config.description}</Text>
      ) : null}

      {config.questions.map((q, idx) => (
        <View key={q.id} style={styles.questionCard}>
          <Text style={styles.questionNumber}>{idx + 1} of {config.questions.length}</Text>
          <Text style={styles.questionText}>
            {q.text}{q.required ? ' *' : ''}
          </Text>

          {q.type === 'text' && (
            <TextInput
              style={styles.textInput}
              value={answers[q.id] || ''}
              onChangeText={(v) => setAnswer(q.id, v)}
              placeholder="Your answer..."
              placeholderTextColor={COLORS.textSecondary}
              multiline
            />
          )}

          {q.type === 'number' && (
            <TextInput
              style={styles.textInput}
              value={answers[q.id]?.toString() || ''}
              onChangeText={(v) => setAnswer(q.id, v ? parseInt(v) || v : '')}
              placeholder="Enter a number..."
              placeholderTextColor={COLORS.textSecondary}
              keyboardType="numeric"
            />
          )}

          {q.type === 'likert' && (
            <LikertScale
              question={q}
              value={answers[q.id] ?? null}
              onChange={(v) => setAnswer(q.id, v)}
            />
          )}

          {q.type === 'choice' && q.options && (
            <ChoiceGroup
              options={q.options}
              value={answers[q.id] ?? null}
              onChange={(v) => setAnswer(q.id, v)}
            />
          )}
        </View>
      ))}

      <TouchableOpacity
        style={[styles.submitButton, isSubmitting && styles.submitDisabled]}
        onPress={handleSubmit}
        disabled={isSubmitting}
      >
        <Text style={styles.submitText}>
          {isSubmitting ? 'Submitting...' : 'Submit'}
        </Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { padding: 24, paddingBottom: 48 },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 24, fontWeight: 'bold', color: COLORS.textPrimary, marginBottom: 4 },
  description: { fontSize: 14, color: COLORS.textSecondary, marginBottom: 24, lineHeight: 20 },
  questionCard: {
    marginBottom: 24,
    padding: 16,
    backgroundColor: COLORS.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  questionNumber: { fontSize: 11, color: COLORS.textSecondary, marginBottom: 4 },
  questionText: { fontSize: 15, color: COLORS.textPrimary, fontWeight: '500', marginBottom: 12, lineHeight: 22 },
  textInput: {
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 8,
    padding: 12,
    fontSize: 15,
    color: COLORS.textPrimary,
    minHeight: 44,
  },
  likertRow: { flexDirection: 'row', justifyContent: 'space-between', gap: 8 },
  likertButton: {
    flex: 1,
    height: 44,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: COLORS.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  likertSelected: { backgroundColor: COLORS.primary, borderColor: COLORS.primary },
  likertText: { fontSize: 16, fontWeight: '600', color: COLORS.textPrimary },
  likertTextSelected: { color: COLORS.textOnPrimary },
  likertLabels: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 },
  likertLabel: { fontSize: 11, color: COLORS.textSecondary, maxWidth: '40%' },
  choiceOption: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
    gap: 12,
  },
  choiceSelected: { backgroundColor: COLORS.primary + '08' },
  radio: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: COLORS.border,
  },
  radioSelected: { borderColor: COLORS.primary, backgroundColor: COLORS.primary },
  choiceText: { fontSize: 15, color: COLORS.textPrimary },
  submitButton: {
    backgroundColor: COLORS.primary,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginTop: 8,
  },
  submitDisabled: { opacity: 0.6 },
  submitText: { color: COLORS.textOnPrimary, fontSize: 18, fontWeight: '600' },
});
