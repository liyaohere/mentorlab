import React, { useEffect, useRef } from 'react';
import { ActivityIndicator, View, StyleSheet } from 'react-native';
import { NavigationContainer, NavigationContainerRef } from '@react-navigation/native';
import { StatusBar } from 'expo-status-bar';
import { useAuthStore } from './stores/authStore';
import { useConversationStore } from './stores/conversationStore';
import AppNavigator from './navigation/AppNavigator';
import {
  registerForPushNotifications,
  addNotificationResponseListener,
  getLastNotificationResponse,
} from './services/notificationService';
import { COLORS } from './utils/constants';

export default function App() {
  const { isReady, token, loadToken } = useAuthStore();
  const navigationRef = useRef<NavigationContainerRef<any>>(null);

  useEffect(() => {
    loadToken();
  }, []);

  // Register for push notifications when authenticated
  useEffect(() => {
    if (token) {
      registerForPushNotifications();
    }
  }, [token]);

  // Handle notification taps (when app is in foreground/background)
  useEffect(() => {
    const cleanup = addNotificationResponseListener((data) => {
      if (data.type === 'new_message') {
        // Refresh conversations to show the new message
        useConversationStore.getState().fetchConversations();
      }
    });

    // Handle cold-start notification tap
    getLastNotificationResponse().then((data) => {
      if (data?.type === 'new_message') {
        useConversationStore.getState().fetchConversations();
      }
    });

    return cleanup;
  }, []);

  if (!isReady) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="large" color={COLORS.primary} />
      </View>
    );
  }

  return (
    <NavigationContainer ref={navigationRef}>
      <StatusBar style="auto" />
      <AppNavigator />
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLORS.background,
  },
});
