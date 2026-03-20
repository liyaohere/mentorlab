import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import { useAuthStore } from '../stores/authStore';
import { COLORS } from '../utils/constants';

export default function SettingsScreen() {
  const { participant, logout } = useAuthStore();

  const handleLeaveStudy = () => {
    Alert.alert(
      'Leave Study',
      'Are you sure you want to withdraw from the study? This cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Leave Study',
          style: 'destructive',
          onPress: async () => {
            await logout();
          },
        },
      ],
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Profile</Text>
        <View style={styles.row}>
          <Text style={styles.label}>Name</Text>
          <Text style={styles.value}>{participant?.name}</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>Venture</Text>
          <Text style={styles.value}>{participant?.venture_name || 'Not set'}</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>Industry</Text>
          <Text style={styles.value}>{participant?.industry_vertical || 'Not set'}</Text>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Study</Text>
        <View style={styles.row}>
          <Text style={styles.label}>Status</Text>
          <Text style={styles.value}>{participant?.status}</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>Audio consent</Text>
          <Text style={styles.value}>
            {participant?.audio_consent ? 'Yes' : 'No'}
          </Text>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>About</Text>
        <View style={styles.row}>
          <Text style={styles.label}>App version</Text>
          <Text style={styles.value}>1.0.0</Text>
        </View>
      </View>

      <TouchableOpacity style={styles.leaveButton} onPress={handleLeaveStudy}>
        <Text style={styles.leaveButtonText}>Leave Study</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.surface, padding: 24 },
  section: { marginBottom: 24 },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: COLORS.textSecondary,
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 12,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  label: { fontSize: 15, color: COLORS.textPrimary },
  value: { fontSize: 15, color: COLORS.textSecondary },
  leaveButton: {
    marginTop: 32,
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: COLORS.error,
    alignItems: 'center',
  },
  leaveButtonText: { color: COLORS.error, fontSize: 16, fontWeight: '600' },
});
