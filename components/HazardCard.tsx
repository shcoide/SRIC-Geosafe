import React from 'react';
import { TouchableOpacity, View, Text, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { RISK_COLORS, HAZARD_ICONS } from '../constants/riskConfig';
import { Colors } from '../constants/colors';
import { HazardSummary } from '../types';

interface Props {
  hazard: HazardSummary;
  onPress?: () => void;
}

export const HazardCard: React.FC<Props> = ({ hazard, onPress }) => {
  const colors = RISK_COLORS[hazard.level];
  const iconName = HAZARD_ICONS[hazard.type];
  const iconColor = Colors.hazard[hazard.type];

  return (
    <TouchableOpacity
      style={styles.card}
      onPress={onPress}
      activeOpacity={0.7}
    >
      <MaterialCommunityIcons name={iconName as any} size={22} color={iconColor} />
      <Text style={styles.name}>{hazard.type.charAt(0).toUpperCase() + hazard.type.slice(1)}</Text>
      <Text style={[styles.level, { color: colors.dot }]}>{hazard.level}</Text>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    flex: 1,
    borderWidth: 0.5,
    borderColor: Colors.surface.border,
    borderRadius: 8,
    padding: 10,
    backgroundColor: Colors.surface.background,
    gap: 3,
  },
  name: { fontSize: 10, color: Colors.text.secondary, marginTop: 2 },
  level: { fontSize: 11, fontWeight: '500' },
});
