import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors } from '../constants/colors';
import { Type } from '../constants/typography';
import { Space } from '../constants/spacing';
import { MaterialRecommendation } from '../types';

interface Props {
  material: MaterialRecommendation;
}

export const MaterialCard: React.FC<Props> = ({ material }) => {
  return (
    <View style={styles.container}>
      <Text style={styles.rankNumeral}>{material.rank}</Text>
      <View style={styles.content}>
        <Text style={styles.name}>{material.name}</Text>
        <Text style={styles.reason}>{material.reason}</Text>
        {/* material.note carries the relative-vs-absolute framing
            (backend/services/inference.py's get_materials()) — suitable
            is a relative top-two/bottom-two ranking, not an absolute
            safety threshold, and this line is what tells the user that,
            not just the raw percentage. */}
        <Text style={styles.probability}>{material.note}</Text>
        <View style={styles.badgeRow}>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{material.isCode}</Text>
          </View>
          <Text style={styles.costLabel}>{material.costLabel}</Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Space.md,
    paddingVertical: Space.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  // Deliberate one-off, per the redesign spec — a document list marker, not
  // a UI badge, so it isn't drawn from the shared Type scale.
  rankNumeral: { fontSize: 28, fontWeight: '200', color: Colors.textMuted, width: 32 },
  content: { flex: 1 },
  name: { ...Type.heading, color: Colors.textPrimary, marginBottom: Space.xs },
  reason: { ...Type.bodySmall, color: Colors.textSecondary },
  probability: { ...Type.label, color: Colors.textMuted, marginTop: Space.xs },
  badgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: Space.xs,
  },
  badge: {
    alignSelf: 'flex-start',
    backgroundColor: Colors.surface,
    // Matches CoverageBadge's radius, not Radius.sm — same small technical
    // pill treatment used for every IS-code/source tag across the app.
    borderRadius: 2,
    paddingHorizontal: Space.sm,
    paddingVertical: 2,
  },
  badgeText: { ...Type.mono, color: Colors.textMuted },
  costLabel: { ...Type.label, color: Colors.textMuted },
});
