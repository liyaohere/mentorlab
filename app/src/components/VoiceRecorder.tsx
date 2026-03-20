import React, { useRef, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
  Alert,
  Platform,
} from 'react-native';
import { Audio } from 'expo-av';
import { COLORS } from '../utils/constants';

interface VoiceRecorderProps {
  onRecordingComplete: (uri: string) => void;
  disabled?: boolean;
}

export default function VoiceRecorder({ onRecordingComplete, disabled }: VoiceRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const recordingRef = useRef<Audio.Recording | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;

  const startPulse = () => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.3,
          duration: 600,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 600,
          useNativeDriver: true,
        }),
      ]),
    ).start();
  };

  const stopPulse = () => {
    pulseAnim.stopAnimation();
    pulseAnim.setValue(1);
  };

  const startRecording = async () => {
    try {
      const permission = await Audio.requestPermissionsAsync();
      if (!permission.granted) {
        Alert.alert(
          'Microphone Permission',
          'Please allow microphone access to send voice messages.',
        );
        return;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY,
      );

      recordingRef.current = recording;
      setIsRecording(true);
      setDuration(0);
      startPulse();

      // Timer for duration display
      timerRef.current = setInterval(() => {
        setDuration((d) => d + 1);
      }, 1000);
    } catch (error) {
      console.error('Failed to start recording:', error);
      Alert.alert('Error', 'Could not start recording. Please try again.');
    }
  };

  const stopRecording = async () => {
    if (!recordingRef.current) return;

    stopPulse();
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    try {
      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI();
      recordingRef.current = null;
      setIsRecording(false);
      setDuration(0);

      await Audio.setAudioModeAsync({ allowsRecordingIOS: false });

      if (uri) {
        onRecordingComplete(uri);
      }
    } catch (error) {
      console.error('Failed to stop recording:', error);
      setIsRecording(false);
      setDuration(0);
    }
  };

  const cancelRecording = async () => {
    if (!recordingRef.current) return;

    stopPulse();
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    try {
      await recordingRef.current.stopAndUnloadAsync();
      recordingRef.current = null;
    } catch {}
    setIsRecording(false);
    setDuration(0);
  };

  const formatDuration = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  if (isRecording) {
    return (
      <View style={styles.recordingRow}>
        <TouchableOpacity style={styles.cancelButton} onPress={cancelRecording}>
          <Text style={styles.cancelText}>Cancel</Text>
        </TouchableOpacity>

        <View style={styles.durationContainer}>
          <Animated.View
            style={[styles.recordDot, { transform: [{ scale: pulseAnim }] }]}
          />
          <Text style={styles.durationText}>{formatDuration(duration)}</Text>
        </View>

        <TouchableOpacity style={styles.stopButton} onPress={stopRecording}>
          <Text style={styles.stopIcon}>↑</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <TouchableOpacity
      style={[styles.micButton, disabled && styles.micButtonDisabled]}
      onPress={startRecording}
      disabled={disabled}
    >
      <Text style={styles.micIcon}>🎤</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  micButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: COLORS.surface,
    borderWidth: 1,
    borderColor: COLORS.border,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 8,
  },
  micButtonDisabled: { opacity: 0.4 },
  micIcon: { fontSize: 18 },
  recordingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    gap: 12,
  },
  cancelButton: {
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  cancelText: { color: COLORS.error, fontSize: 14, fontWeight: '500' },
  durationContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  recordDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: COLORS.error,
  },
  durationText: { fontSize: 16, fontWeight: '600', color: COLORS.textPrimary },
  stopButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stopIcon: { color: COLORS.textOnPrimary, fontSize: 20, fontWeight: 'bold' },
});
