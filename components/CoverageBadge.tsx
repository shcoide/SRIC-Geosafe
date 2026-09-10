import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { SOURCE_COLORS, SOURCE_LABELS, SOURCE_LABELS_COMPACT } from '../constants/riskConfig';
import { Type } from '../constants/typography';
import { Space } from '../constants/spacing';
import { SiteDataSource, HazardSource } from '../types';

interface Props {
  // Coarse, region-level summary — "does this region have any calibrated
  // survey point at all" (used on the home screen's region cards).
  quality?: 'calibrated' | 'regional';
  // Fine-grained, point-level tier — what a specific tapped point would
  // actually resolve to (used on the map's coverage-check bottom sheet), or
  // a HazardSummary's provenance (used on the hazard overview screen).
  source?: SiteDataSource | HazardSource;
  compact?: boolean;
}

export const CoverageBadge: React.FC<Props> = ({ quality, source, compact }) => {
  const { color, label } = source
    ? { color: SOURCE_COLORS[source], label: (compact ? SOURCE_LABELS_COMPACT : SOURCE_LABELS)[source] }
    : quality === 'calibrated'
    ? { color: SOURCE_COLORS.measured, label: 'Point-calibrated' }
    : { color: SOURCE_COLORS.interpolated, label: 'Regional estimate only' };

  return (
    <View style={[styles.badge, compact && styles.badgeCompact, { backgroundColor: color.bg }]}>
      <Text
        style={[styles.text, { color: color.text }]}
        numberOfLines={compact ? 2 : undefined}
        ellipsizeMode="tail"
      >
        {label}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    // Almost square, technical — not the softer radii used for cards or
    // inputs elsewhere (Radius.sm/md/lg). Background alone carries the
    // information; no border, no dot.
    borderRadius: 2,
    paddingHorizontal: Space.sm,
    paddingVertical: Space.xs,
  },
  badgeCompact: { paddingHorizontal: Space.xs, paddingVertical: 2, maxWidth: '100%' },
  text: { ...Type.badge },
});
