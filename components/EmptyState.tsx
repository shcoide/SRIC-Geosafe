import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors } from '../constants/colors';
import { Type } from '../constants/typography';
import { Space, Radius } from '../constants/spacing';

interface Props {
  icon?: keyof typeof MaterialCommunityIcons.glyphMap;
  title: string;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<Props> = ({
  icon = 'map-marker-off-outline',
  title,
  message,
  actionLabel,
  onAction,
}) => {
  return (
    <View style={styles.container}>
      <MaterialCommunityIcons name={icon} size={40} color={Colors.textMuted} />
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.message}>{message}</Text>
      {actionLabel && onAction && (
        <TouchableOpacity style={styles.actionBtn} onPress={onAction}>
          <Text style={styles.actionBtnText}>{actionLabel}</Text>
        </TouchableOpacity>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: Space.xl,
    paddingVertical: Space.xl + Space.lg + 4,
    gap: Space.sm - 2,
  },
  title: { ...Type.heading, color: Colors.textPrimary, marginTop: Space.sm + 2 },
  message: { ...Type.bodySmall, color: Colors.textSecondary, textAlign: 'center' },
  actionBtn: {
    marginTop: Space.sm + 6,
    borderWidth: 1,
    borderColor: Colors.primaryBorder,
    borderRadius: Radius.md,
    paddingHorizontal: Space.lg - 6,
    paddingVertical: Space.sm + 4,
    backgroundColor: Colors.primaryLight,
  },
  actionBtnText: { ...Type.bodySmall, fontWeight: '500', color: Colors.primary },
});
