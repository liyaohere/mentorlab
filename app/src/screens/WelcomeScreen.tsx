import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { COLORS } from '../utils/constants';

export default function WelcomeScreen({ navigation }: any) {
  const [code, setCode] = useState('');

  const handleContinue = () => {
    const trimmed = code.trim().toUpperCase();
    if (trimmed.length < 6) {
      Alert.alert('Invalid Code', 'Please enter a valid invite code.');
      return;
    }
    navigation.navigate('Register', { inviteCode: trimmed });
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.content}>
        <Text style={styles.title}>MentorLab</Text>
        <Text style={styles.subtitle}>Your AI business mentor</Text>

        <View style={styles.inputContainer}>
          <Text style={styles.label}>Enter your invite code</Text>
          <TextInput
            style={styles.input}
            value={code}
            onChangeText={setCode}
            placeholder="e.g. TEST001A"
            placeholderTextColor={COLORS.textSecondary}
            autoCapitalize="characters"
            maxLength={8}
            autoFocus
          />
        </View>

        <TouchableOpacity
          style={[styles.button, !code.trim() && styles.buttonDisabled]}
          onPress={handleContinue}
          disabled={!code.trim()}
        >
          <Text style={styles.buttonText}>Continue</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 32,
  },
  title: {
    fontSize: 36,
    fontWeight: 'bold',
    color: COLORS.primary,
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: COLORS.textSecondary,
    textAlign: 'center',
    marginBottom: 48,
  },
  inputContainer: {
    marginBottom: 24,
  },
  label: {
    fontSize: 14,
    color: COLORS.textSecondary,
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 12,
    padding: 16,
    fontSize: 20,
    textAlign: 'center',
    letterSpacing: 4,
    color: COLORS.textPrimary,
    backgroundColor: COLORS.surface,
  },
  button: {
    backgroundColor: COLORS.primary,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonText: {
    color: COLORS.textOnPrimary,
    fontSize: 18,
    fontWeight: '600',
  },
});
