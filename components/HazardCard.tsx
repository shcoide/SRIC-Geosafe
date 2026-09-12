import React from 'react';
import { TouchableOpacity, View, Text, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { RISK_COLORS, HAZARD_ICONS } from '../constants/riskConfig';
import { Colors } from '../constants/colors';
import { Type } from '../constants/typography';
import { Space, Radius } from '../constants/spacing';
import { HazardSummary } from '../types';

interface Props {
  hazard: HazardSummary;
  onPress?: () => void;
}

const hexToRgba = (hex: string, alpha: number): string => {
  const clean = hex.replace('#', '');
  const value = parseInt(clean, 16);
  const r = (value >> 16) & 255;
  const g = (value >> 8) & 255;
  const b = value & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

export const HazardCard: React.FC<Props> = ({ hazard, onPress }) => {
  const colors = RISK_COLORS[hazard.level];
  const iconName = HAZARD_ICONS[hazard.type];

  return (
    <TouchableOpacity
      style={[
        styles.card,
        {
          backgroundColor: hexToRgba(colors.bg, 0.5),
          borderLeftColor: colors.dot,
        },
      ]}
      onPress={onPress}
      activeOpacity={0.7}
    >
      <View style={styles.iconRow}>
        <MaterialCommunityIcons name={iconName as any} size={18} color={colors.dot} />
        <Text style={styles.name}>{hazard.type.charAt(0).toUpperCase() + hazard.type.slice(1)}</Text>
      </View>
      <Text style={[styles.level, { color: colors.text }]}>{hazard.level}</Text>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    width: '48%',
    height: 88,
    justifyContent: 'space-between',
    borderLeftWidth: 3,
    borderRadius: Radius.sm,
    padding: Space.sm,
  },
  iconRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  name: { ...Type.label, fontSize: 10, color: Colors.textSecondary },
  level: { ...Type.heading },
});
