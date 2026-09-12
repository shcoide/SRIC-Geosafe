import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors, Palette } from '../constants/colors';
import { Type } from '../constants/typography';
import { Space, Radius } from '../constants/spacing';
import { MaterialRecommendation } from '../types';

interface Props {
  material: MaterialRecommendation;
}

const hexToRgba = (hex: string, alpha: number): string => {
  const clean = hex.replace('#', '');
  const value = parseInt(clean, 16);
  const r = (value >> 16) & 255;
  const g = (value >> 8) & 255;
  const b = value & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

export const MaterialCard: React.FC<Props> = ({ material }) => {
  const pct = Math.round(material.collapseProbability * 100);
  const pillColors = material.suitable
    ? { bg: Palette.src_measured_bg, text: Palette.src_measured_text }
    : { bg: Palette.risk_vhi_bg, text: Palette.risk_vhi_text };

  return (
    <View
      style={[
        styles.container,
        {
          borderLeftColor: material.suitable ? Colors.primary : Colors.divider,
          backgroundColor: material.suitable ? Palette.white : hexToRgba(Palette.stone50, 0.6),
        },
      ]}
    >
      <View style={styles.headerRow}>
        <Text style={styles.rankNumeral}>{material.rank}</Text>
        <Text style={styles.name}>{material.name}</Text>
        <View style={[styles.collapsePill, { backgroundColor: pillColors.bg }]}>
          <Text style={[styles.collapsePillText, { color: pillColors.text }]}>{pct}% collapse</Text>
        </View>
      </View>

      <Text style={styles.reason}>{material.reason}</Text>

      <View style={styles.footerRow}>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{material.isCode}</Text>
        </View>
        <Text style={styles.costLabel}>{material.costLabel}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: Palette.white,
    borderWidth: 1,
    borderColor: Colors.border,
    borderLeftWidth: 3,
    borderRadius: Radius.md,
    padding: 14,
    marginBottom: Space.sm,
  },
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: Space.sm },
  // Deliberate one-off, per the redesign spec — a document list marker, not
  // a UI badge, so it isn't drawn from the shared Type scale.
  rankNumeral: { fontSize: 22, fontWeight: '200', color: Colors.textMuted, width: 28 },
  name: { ...Type.heading, color: Colors.textPrimary, flex: 1 },
  collapsePill: { borderRadius: 3, paddingHorizontal: Space.xs + 2, paddingVertical: 2 },
  collapsePillText: { fontSize: 10, fontWeight: '500' },
  reason: { ...Type.bodySmall, color: Colors.textSecondary, marginTop: 6, marginBottom: 8 },
  footerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  badge: {
    alignSelf: 'flex-start',
    backgroundColor: Colors.surface,
    borderRadius: 2,
    paddingHorizontal: Space.sm,
    paddingVertical: 2,
  },
  badgeText: { ...Type.mono, fontSize: 9, color: Colors.textMuted },
  costLabel: { fontSize: 10, color: Colors.textMuted },
});
