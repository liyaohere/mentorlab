import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
} from 'react-native';
import { useAuthStore } from '../stores/authStore';
import { COLORS } from '../utils/constants';

const CONSENT_TEXT = `INFORMED CONSENT FOR RESEARCH PARTICIPATION

Study Title: AI-Assisted Entrepreneurial Mentoring
Principal Investigator: Xilan Zhang, Stanford University

PURPOSE
You are invited to participate in a research study about entrepreneurial mentoring. This study explores how AI-based mentoring tools can support entrepreneurs in developing their businesses.

WHAT YOU WILL DO
- Chat with an AI mentor through this app for approximately 6-8 weeks
- Receive weekly messages from your mentor and respond at your convenience
- Complete brief surveys about your business progress
- You may use text or voice messages to communicate

DATA COLLECTION
- Your chat messages will be stored securely and used for research purposes
- If you choose to send voice messages, the audio recordings will also be stored
- Survey responses will be collected at baseline, midpoint, and endline
- All data will be de-identified before analysis

RISKS AND BENEFITS
- There are minimal risks to participation
- You may benefit from the mentoring guidance provided
- Your participation contributes to research on entrepreneurship support

VOLUNTARY PARTICIPATION
- Your participation is entirely voluntary
- You may withdraw at any time without penalty
- To withdraw, go to Settings > Leave Study

CONFIDENTIALITY
- Your data will be stored securely and accessed only by the research team
- Results will be reported in aggregate; individual responses will not be identified
- Data will be retained for a minimum of 5 years per Stanford policy

CONTACT
For questions about this study, contact: xilan@stanford.edu
For questions about your rights as a participant, contact the Stanford IRB at (650) 723-2480.`;

export default function ConsentScreen({ navigation }: any) {
  const { recordConsent, isLoading } = useAuthStore();
  const [studyConsent, setStudyConsent] = useState(false);
  const [audioConsent, setAudioConsent] = useState(false);

  const handleAgree = async () => {
    try {
      await recordConsent(studyConsent, audioConsent);
      // Navigation will happen automatically via the auth state change
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to record consent.');
    }
  };

  return (
    <View style={styles.container}>
      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
        <Text style={styles.title}>Informed Consent</Text>
        <Text style={styles.subtitle}>Please read carefully before proceeding</Text>

        <View style={styles.consentBox}>
          <Text style={styles.consentText}>{CONSENT_TEXT}</Text>
        </View>
      </ScrollView>

      <View style={styles.footer}>
        <TouchableOpacity
          style={styles.checkbox}
          onPress={() => setStudyConsent(!studyConsent)}
        >
          <View style={[styles.checkboxBox, studyConsent && styles.checkboxChecked]}>
            {studyConsent && <Text style={styles.checkmark}>✓</Text>}
          </View>
          <Text style={styles.checkboxLabel}>
            I have read and agree to participate in this study *
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.checkbox}
          onPress={() => setAudioConsent(!audioConsent)}
        >
          <View style={[styles.checkboxBox, audioConsent && styles.checkboxChecked]}>
            {audioConsent && <Text style={styles.checkmark}>✓</Text>}
          </View>
          <Text style={styles.checkboxLabel}>
            I consent to voice message recording for research (optional)
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.button, (!studyConsent || isLoading) && styles.buttonDisabled]}
          onPress={handleAgree}
          disabled={!studyConsent || isLoading}
        >
          <Text style={styles.buttonText}>
            {isLoading ? 'Starting...' : 'Start'}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  scroll: { flex: 1 },
  scrollContent: { padding: 24 },
  title: { fontSize: 24, fontWeight: 'bold', color: COLORS.textPrimary, marginBottom: 4 },
  subtitle: { fontSize: 14, color: COLORS.textSecondary, marginBottom: 16 },
  consentBox: {
    backgroundColor: COLORS.surface,
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  consentText: { fontSize: 13, lineHeight: 20, color: COLORS.textPrimary },
  footer: {
    padding: 24,
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
    backgroundColor: COLORS.background,
  },
  checkbox: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 16 },
  checkboxBox: {
    width: 24,
    height: 24,
    borderWidth: 2,
    borderColor: COLORS.border,
    borderRadius: 4,
    marginRight: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkboxChecked: { backgroundColor: COLORS.primary, borderColor: COLORS.primary },
  checkmark: { color: COLORS.textOnPrimary, fontSize: 16, fontWeight: 'bold' },
  checkboxLabel: { flex: 1, fontSize: 14, color: COLORS.textPrimary, lineHeight: 20 },
  button: {
    backgroundColor: COLORS.primary,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: COLORS.textOnPrimary, fontSize: 18, fontWeight: '600' },
});
