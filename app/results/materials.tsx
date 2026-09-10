import React from 'react';
import { ScrollView, View, Text, StyleSheet } from 'react-native';
import { router } from 'expo-router';
import { useLocationStore } from '../../store/useLocationStore';
import { MaterialCard } from '../../components/MaterialCard';
import { EmptyState } from '../../components/EmptyState';
import { Colors } from '../../constants/colors';
import { RISK_COLORS } from '../../constants/riskConfig';
import { Type } from '../../constants/typography';
import { Space, Radius } from '../../constants/spacing';

const hexToRgba = (hex: string, alpha: number): string => {
  const clean = hex.replace('#', '');
  const value = parseInt(clean, 16);
  const r = (value >> 16) & 255;
  const g = (value >> 8) & 255;
  const b = value & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

export default function MaterialsScreen() {
  const result = useLocationStore((s) => s.currentResult);
  if (!result) {
    return (
      <EmptyState
        icon="cube-outline"
        title="No material recommendations"
        message="Search for a location from the Search tab to see recommended construction materials here."
        actionLabel="Go to search"
        onAction={() => router.replace('/(tabs)')}
      />
    );
  }

  const veryHigh = RISK_COLORS['Very High'];
  const highRisk = RISK_COLORS['High'];
  // Zone IV's zone factor (ZONE_PGA["IV"] in backend/services/inference.py)
  // is 0.24g — used here as the surfaceSa threshold for "Zone IV/V-like
  // demand" rather than re-deriving it from seismicZone, since surfaceSa is
  // the actual value the fragility ranking (and this disclaimer) cares
  // about, and it can exceed 0.24g even in a nominally lower zone once
  // amplification/resonance are folded in.
  const elevatedDemand = result.surfaceSa > 0.24;

  return (
    <ScrollView style={styles.scroll} contentContainerStyle={styles.container}>
      <Text style={styles.summaryLine}>Zone {result.seismicZone} · NEHRP Class {result.siteClassVs30}</Text>

      {elevatedDemand && (
        <View style={[styles.disclaimerBanner, { backgroundColor: highRisk.bg, borderColor: highRisk.border }]}>
          <Text style={[styles.disclaimerText, { color: highRisk.text }]}>
            All structural systems face elevated seismic demand at this site. Recommendations show relative
            performance — engage a structural engineer before construction.
          </Text>
        </View>
      )}

      <Text style={styles.sectionLabel}>Recommended structural systems</Text>
      {result.materials.filter(m => m.suitable).map((m, i) => (
        <MaterialCard key={i} material={m} />
      ))}

      <Text style={[styles.sectionLabel, { marginTop: Space.lg - 4 }]}>Avoid for this site</Text>
      {result.materials.filter(m => !m.suitable).map((m, i) => (
        <View
          key={i}
          style={[
            styles.avoidRow,
            { backgroundColor: hexToRgba(veryHigh.bg, 0.4), borderLeftColor: veryHigh.border },
          ]}
        >
          <Text style={styles.avoidText}>{m.name}</Text>
          <Text style={styles.avoidReason}>{m.reason}</Text>
          <Text style={styles.avoidProbability}>{m.note}</Text>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: Colors.background },
  container: { padding: Space.md, paddingBottom: Space.xl + Space.sm },
  summaryLine: { ...Type.label, color: Colors.textSecondary, marginBottom: Space.md },
  disclaimerBanner: {
    borderWidth: 1, borderRadius: Radius.sm,
    padding: Space.sm + 4, marginBottom: Space.md,
  },
  disclaimerText: { ...Type.bodySmall },
  sectionLabel: { ...Type.label, color: Colors.textMuted, marginBottom: Space.sm },
  avoidRow: {
    borderLeftWidth: 2,
    paddingVertical: Space.sm, paddingHorizontal: Space.sm + 2,
    marginBottom: Space.xs,
  },
  avoidText: { ...Type.bodySmall, fontWeight: '500', color: Colors.textPrimary },
  avoidReason: { ...Type.bodySmall, color: Colors.textSecondary, marginTop: Space.xs / 2 },
  avoidProbability: { ...Type.label, color: Colors.textMuted, marginTop: Space.xs / 2 },
});
