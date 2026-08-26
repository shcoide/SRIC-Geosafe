import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { SOURCE_COLORS, SOURCE_LABELS } from '../constants/riskConfig';
import { SiteDataSource } from '../types';

interface Props {
  // Coarse, region-level summary — "does this region have any calibrated
  // survey point at all" (used on the home screen's region cards).
  quality?: 'calibrated' | 'regional';
  // Fine-grained, point-level tier — what a specific tapped point would
  // actually resolve to (used on the map's coverage-check bottom sheet).
  source?: SiteDataSource;
  compact?: boolean;
}

export const CoverageBadge: React.FC<Props> = ({ quality, source, compact }) => {
  const { color, label } = source
    ? { color: SOURCE_COLORS[source], label: SOURCE_LABELS[source] }
    : quality === 'calibrated'
    ? { color: SOURCE_COLORS.measured, label: 'Point-calibrated' }
    : { color: SOURCE_COLORS.interpolated, label: 'Regional estimate only' };

  return (
    <View style={[
      styles.badge,
      compact && styles.badgeCompact,
      { backgroundColor: color.bg, borderColor: color.border },
    ]}>
      <View style={[styles.dot, { backgroundColor: color.dot }]} />
      <Text style={[styles.text, { color: color.text }]}>{label}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row', alignItems: 'center', gap: 6, alignSelf: 'flex-start',
    borderRadius: 8, borderWidth: 0.5, paddingHorizontal: 10, paddingVertical: 6,
  },
  badgeCompact: { paddingHorizontal: 8, paddingVertical: 4 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  text: { fontSize: 12, fontWeight: '500' },
});
