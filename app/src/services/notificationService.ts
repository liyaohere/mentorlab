import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import * as api from './api';

// Configure notification behavior
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

/**
 * Register for push notifications and send the FCM token to the server.
 */
export async function registerForPushNotifications(): Promise<string | null> {
  if (!Device.isDevice) {
    console.log('Push notifications require a physical device');
    return null;
  }

  // Check/request permissions
  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== 'granted') {
    console.log('Push notification permission not granted');
    return null;
  }

  // Android: create notification channel
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('mentorlab_messages', {
      name: 'Mentor Messages',
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#1B5E20',
    });
  }

  try {
    // Get the Expo push token (works with FCM under the hood)
    const projectId = Constants.expoConfig?.extra?.eas?.projectId;
    const tokenData = await Notifications.getExpoPushTokenAsync({
      projectId,
    });
    const token = tokenData.data;

    // Send token to backend
    await api.updateProfile({ fcm_token: token });

    console.log('Push notification token registered:', token);
    return token;
  } catch (error) {
    console.error('Failed to get push token:', error);
    return null;
  }
}

/**
 * Listen for notification taps and return a cleanup function.
 * The callback receives the conversation-related data from the notification.
 */
export function addNotificationResponseListener(
  callback: (data: { type?: string; message_id?: string }) => void,
): () => void {
  const subscription = Notifications.addNotificationResponseReceivedListener(
    (response) => {
      const data = response.notification.request.content.data as Record<string, string>;
      callback(data);
    },
  );

  return () => subscription.remove();
}

/**
 * Check if the app was opened from a notification (cold start).
 */
export async function getLastNotificationResponse(): Promise<{
  type?: string;
  message_id?: string;
} | null> {
  const response = await Notifications.getLastNotificationResponseAsync();
  if (response) {
    return response.notification.request.content.data as Record<string, string>;
  }
  return null;
}
