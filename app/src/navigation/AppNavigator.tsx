import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAuthStore } from '../stores/authStore';
import { COLORS } from '../utils/constants';

import WelcomeScreen from '../screens/WelcomeScreen';
import RegisterScreen from '../screens/RegisterScreen';
import ConsentScreen from '../screens/ConsentScreen';
import ConversationListScreen from '../screens/ConversationListScreen';
import ChatScreen from '../screens/ChatScreen';
import SurveyScreen from '../screens/SurveyScreen';
import SettingsScreen from '../screens/SettingsScreen';

const Stack = createNativeStackNavigator();

function AuthStack() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
      }}
    >
      <Stack.Screen name="Welcome" component={WelcomeScreen} />
      <Stack.Screen
        name="Register"
        component={RegisterScreen}
        options={{ headerShown: true, title: 'Register' }}
      />
      <Stack.Screen
        name="Consent"
        component={ConsentScreen}
        options={{ headerShown: true, title: 'Consent' }}
      />
    </Stack.Navigator>
  );
}

function MainStack() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: COLORS.primary },
        headerTintColor: COLORS.textOnPrimary,
        headerTitleStyle: { fontWeight: '600' },
      }}
    >
      <Stack.Screen
        name="ConversationList"
        component={ConversationListScreen}
        options={({ navigation }) => ({
          title: 'MentorLab',
          headerRight: () => (
            <React.Fragment>
              <SettingsButton onPress={() => navigation.navigate('Settings')} />
            </React.Fragment>
          ),
        })}
      />
      <Stack.Screen
        name="Chat"
        component={ChatScreen}
        options={{ title: 'Conversation' }}
      />
      <Stack.Screen
        name="Survey"
        component={SurveyScreen}
        options={{ title: 'Survey' }}
      />
      <Stack.Screen
        name="Settings"
        component={SettingsScreen}
        options={{ title: 'Settings' }}
      />
    </Stack.Navigator>
  );
}

function SettingsButton({ onPress }: { onPress: () => void }) {
  const { Text, TouchableOpacity } = require('react-native');
  return (
    <TouchableOpacity onPress={onPress} style={{ padding: 8 }}>
      <Text style={{ color: COLORS.textOnPrimary, fontSize: 20 }}>⚙</Text>
    </TouchableOpacity>
  );
}

export default function AppNavigator() {
  const { token, participant } = useAuthStore();

  // Show auth flow if no token, or if enrolled but not yet consented
  const needsAuth = !token;
  const needsConsent = participant && !participant.consent_at;

  if (needsAuth) {
    return <AuthStack />;
  }

  if (needsConsent) {
    return (
      <Stack.Navigator screenOptions={{ headerShown: true }}>
        <Stack.Screen name="Consent" component={ConsentScreen} options={{ title: 'Consent' }} />
      </Stack.Navigator>
    );
  }

  return <MainStack />;
}
