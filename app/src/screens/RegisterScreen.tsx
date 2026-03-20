import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useAuthStore } from '../stores/authStore';
import { COLORS, INDUSTRY_VERTICALS } from '../utils/constants';

export default function RegisterScreen({ route, navigation }: any) {
  const { inviteCode } = route.params;
  const { register, isLoading } = useAuthStore();

  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [ventureName, setVentureName] = useState('');
  const [ventureDesc, setVentureDesc] = useState('');
  const [industry, setIndustry] = useState('');
  const [showPicker, setShowPicker] = useState(false);

  const handleSubmit = async () => {
    if (!name.trim()) {
      Alert.alert('Required', 'Please enter your name.');
      return;
    }
    try {
      await register({
        invite_code: inviteCode,
        name: name.trim(),
        phone_number: phone.trim(),
        venture_name: ventureName.trim(),
        venture_description: ventureDesc.trim(),
        industry_vertical: industry,
      });
      navigation.navigate('Consent');
    } catch (error: any) {
      Alert.alert('Registration Failed', error.message || 'Please try again.');
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>Tell us about yourself</Text>

        <View style={styles.field}>
          <Text style={styles.label}>Your Name *</Text>
          <TextInput
            style={styles.input}
            value={name}
            onChangeText={setName}
            placeholder="Full name"
            placeholderTextColor={COLORS.textSecondary}
          />
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Phone Number</Text>
          <TextInput
            style={styles.input}
            value={phone}
            onChangeText={setPhone}
            placeholder="+256..."
            placeholderTextColor={COLORS.textSecondary}
            keyboardType="phone-pad"
          />
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Venture Name</Text>
          <TextInput
            style={styles.input}
            value={ventureName}
            onChangeText={setVentureName}
            placeholder="Your business name"
            placeholderTextColor={COLORS.textSecondary}
          />
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Venture Description</Text>
          <TextInput
            style={[styles.input, styles.textArea]}
            value={ventureDesc}
            onChangeText={setVentureDesc}
            placeholder="What does your business do?"
            placeholderTextColor={COLORS.textSecondary}
            multiline
            numberOfLines={3}
          />
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Industry</Text>
          <TouchableOpacity
            style={styles.picker}
            onPress={() => setShowPicker(!showPicker)}
          >
            <Text style={industry ? styles.pickerText : styles.pickerPlaceholder}>
              {industry || 'Select industry...'}
            </Text>
          </TouchableOpacity>
          {showPicker && (
            <View style={styles.pickerOptions}>
              {INDUSTRY_VERTICALS.map((v) => (
                <TouchableOpacity
                  key={v}
                  style={[styles.pickerOption, industry === v && styles.pickerOptionSelected]}
                  onPress={() => { setIndustry(v); setShowPicker(false); }}
                >
                  <Text style={industry === v ? styles.pickerOptionTextSelected : styles.pickerOptionText}>
                    {v}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          )}
        </View>

        <TouchableOpacity
          style={[styles.button, isLoading && styles.buttonDisabled]}
          onPress={handleSubmit}
          disabled={isLoading}
        >
          <Text style={styles.buttonText}>{isLoading ? 'Registering...' : 'Next'}</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  scroll: { padding: 24, paddingBottom: 48 },
  title: { fontSize: 24, fontWeight: 'bold', color: COLORS.textPrimary, marginBottom: 24 },
  field: { marginBottom: 16 },
  label: { fontSize: 14, color: COLORS.textSecondary, marginBottom: 6 },
  input: {
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 10,
    padding: 14,
    fontSize: 16,
    color: COLORS.textPrimary,
    backgroundColor: COLORS.surface,
  },
  textArea: { height: 80, textAlignVertical: 'top' },
  picker: {
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 10,
    padding: 14,
    backgroundColor: COLORS.surface,
  },
  pickerText: { fontSize: 16, color: COLORS.textPrimary },
  pickerPlaceholder: { fontSize: 16, color: COLORS.textSecondary },
  pickerOptions: {
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 10,
    marginTop: 4,
    backgroundColor: COLORS.background,
  },
  pickerOption: { padding: 12, borderBottomWidth: 1, borderBottomColor: COLORS.border },
  pickerOptionSelected: { backgroundColor: COLORS.primary + '15' },
  pickerOptionText: { fontSize: 15, color: COLORS.textPrimary },
  pickerOptionTextSelected: { fontSize: 15, color: COLORS.primary, fontWeight: '600' },
  button: {
    backgroundColor: COLORS.primary,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginTop: 16,
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: COLORS.textOnPrimary, fontSize: 18, fontWeight: '600' },
});
