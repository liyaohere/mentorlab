import React, { useEffect, useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Linking } from 'react-native';
import { COLORS, API_URL } from '../utils/constants';

const APP_VERSION = '1.0.0';

interface VersionInfo {
  latest_version: string;
  update_available: boolean;
  force_update: boolean;
  download_url: string;
}

export default function UpdateBanner() {
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    checkVersion();
  }, []);

  const checkVersion = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/version?current=${APP_VERSION}`);
      if (response.ok) {
        const data = await response.json();
        if (data.update_available) {
          setVersionInfo(data);
        }
      }
    } catch {
      // Silently fail — version check is not critical
    }
  };

  if (!versionInfo || dismissed) return null;

  return (
    <View style={[styles.banner, versionInfo.force_update && styles.bannerForce]}>
      <View style={styles.textContainer}>
        <Text style={styles.bannerTitle}>
          {versionInfo.force_update ? 'Update Required' : 'Update Available'}
        </Text>
        <Text style={styles.bannerText}>
          Version {versionInfo.latest_version} is available.
          {versionInfo.force_update
            ? ' You must update to continue using the app.'
            : ' Tap to download.'}
        </Text>
      </View>
      <View style={styles.actions}>
        <TouchableOpacity
          style={styles.updateButton}
          onPress={() => Linking.openURL(versionInfo.download_url)}
        >
          <Text style={styles.updateButtonText}>Update</Text>
        </TouchableOpacity>
        {!versionInfo.force_update && (
          <TouchableOpacity onPress={() => setDismissed(true)}>
            <Text style={styles.dismissText}>Later</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    backgroundColor: COLORS.primary + '15',
    borderBottomWidth: 1,
    borderBottomColor: COLORS.primary + '30',
    padding: 12,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
  },
  bannerForce: {
    backgroundColor: COLORS.error + '15',
    borderBottomColor: COLORS.error + '30',
  },
  textContainer: { flex: 1 },
  bannerTitle: { fontSize: 14, fontWeight: '700', color: COLORS.primary, marginBottom: 2 },
  bannerText: { fontSize: 12, color: COLORS.textSecondary, lineHeight: 16 },
  actions: { alignItems: 'center', gap: 8 },
  updateButton: {
    backgroundColor: COLORS.primary,
    paddingVertical: 6,
    paddingHorizontal: 16,
    borderRadius: 6,
  },
  updateButtonText: { color: COLORS.textOnPrimary, fontSize: 13, fontWeight: '600' },
  dismissText: { fontSize: 12, color: COLORS.textSecondary },
});
