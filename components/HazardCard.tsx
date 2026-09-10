import React from 'react';
import { TouchableOpacity, Text, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { RISK_COLORS, HAZARD_ICONS } from '../constants/riskConfig';
import { Colors } from '../constants/colors';
import { Type } from '../constants/typography';
import { Space, Radius } from '../constants/spacing';
import { HazardSummary } from '../types';
import { CoverageBadge } from './CoverageBadge';

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

// Card width is proportional to risk severity, not identical — a Very High
// hazard should visually dominate a Low one in the same row.
const SEVERITY_FLEX: Record<HazardSummary['level'], number> = {
  'Very High': 2.5,
  'High': 2,
  'Moderate': 1.5,
  'Low': 1,
};

export const HazardCard: React.FC<Props> = ({ hazard, onPress }) => {
  const colors = RISK_COLORS[hazard.level];
  const iconName = HAZARD_ICONS[hazard.type];

  return (
    <TouchableOpacity
      style={[
        styles.card,
        {
          flex: SEVERITY_FLEX[hazard.level],
          backgroundColor: hexToRgba(colors.bg, 0.7),
          borderLeftColor: colors.dot,
        },
      ]}
      onPress={onPress}
      activeOpacity={0.7}
    >
      <MaterialCommunityIcons name={iconName as any} size={20} color={colors.dot} />
      <Text style={styles.name}>{hazard.type.charAt(0).toUpperCase() + hazard.type.slice(1)}</Text>
      <Text style={[styles.level, { color: colors.text }]}>{hazard.level}</Text>
      <CoverageBadge source={hazard.source} compact />
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    borderLeftWidth: 2,
    borderRadius: Radius.sm,
    padding: Space.sm,
    gap: Space.xs / 2,
  },
  name: { ...Type.label, color: Colors.textSecondary, marginTop: Space.xs / 2 },
  level: { ...Type.bodySmall, fontWeight: '500' },
});
