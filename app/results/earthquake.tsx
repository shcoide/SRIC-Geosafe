import React from 'react';
import { ScrollView, View, Text, StyleSheet } from 'react-native';
import { router } from 'expo-router';
import { useLocationStore } from '../../store/useLocationStore';
import { EmptyState } from '../../components/EmptyState';
import { Colors, Palette } from '../../constants/colors';
import { RISK_COLORS } from '../../constants/riskConfig';
import { Type } from '../../constants/typography';
import { Space, Radius } from '../../constants/spacing';

export default function EarthquakeScreen() {
  const result = useLocationStore((s) => s.currentResult);
  if (!result) {
    return (
      <EmptyState
        icon="pulse"
        title="No earthquake data"
        message="Search for a location from the Search tab to see its earthquake analysis here."
        actionLabel="Go to search"
        onAction={() => router.replace('/(tabs)')}
      />
    );
  }

  const classesDisagree = result.siteClassSpt !== null && result.siteClassSpt !== result.siteClassVs30;
  const disagreeColors = RISK_COLORS.Moderate;

  // "strong"/"moderate" reuse the same risk-level colours the rest of the
  // app uses for High/Moderate; "none"/"indeterminate" fall back to plain
  // muted text — this is an approximation (period proximity only, not a
  // dynamic analysis), so it deliberately doesn't borrow the "Low" green,
  // which would read as a confident all-clear.
  const resonanceLevel = result.resonanceZone === 'strong' ? 'High' : result.resonanceZone === 'moderate' ? 'Moderate' : null;
  const resonanceRowColors = resonanceLevel ? RISK_COLORS[resonanceLevel] : null;

  return (
    <ScrollView style={styles.scroll} contentContainerStyle={styles.container}>
      <View style={styles.card}>
        <Text style={styles.cardHead}>Site parameters</Text>
        {[
          ['IS 1893 Zone', `Zone ${result.seismicZone}`],
          ['Bedrock PGA', `${result.bedrockPga.toFixed(2)}g`],
          ['Amplification factor', `${result.amplificationFactor.toFixed(2)}×`],
          ['Surface PGA', `${result.surfacePga.toFixed(2)}g`],
          ['Vs30', `${Math.round(result.vs30)} m/s`],
          ['Site class (Vs30)', `Class ${result.siteClassVs30}`],
          ['Site class (SPT-N)', result.siteClassSpt ? `Class ${result.siteClassSpt}` : 'Not surveyed'],
          ...(result.distanceToFault !== null
            ? [['Nearest fault', `${Math.round(result.distanceToFault)} km${result.faultName ? ` (${result.faultName})` : ''}`]]
            : []),
          ['Liquefaction risk', result.liquefactionRisk],
        ].map(([label, value]) => (
          <View key={label} style={styles.row}>
            <Text style={styles.rowLabel}>{label}</Text>
            <Text style={styles.rowValue}>{value}</Text>
          </View>
        ))}
        <View
          style={[
            styles.row,
            resonanceRowColors ? { backgroundColor: resonanceRowColors.bg, borderBottomColor: resonanceRowColors.border } : null,
          ]}
        >
          <Text style={[styles.rowLabel, resonanceRowColors ? { color: resonanceRowColors.text } : null]}>
            Building resonance
          </Text>
          <Text style={[styles.rowValue, { color: resonanceRowColors ? resonanceRowColors.text : Colors.textMuted }]}>
            {result.buildingPeriodS.toFixed(2)}s · {result.resonanceZone}
          </Text>
        </View>
      </View>

      {classesDisagree && (
        <View style={[styles.warningBanner, { backgroundColor: disagreeColors.bg, borderColor: disagreeColors.border }]}>
          <Text style={[styles.warningTitle, { color: disagreeColors.text }]}>Vs30 and SPT-N site class disagree</Text>
          <Text style={[styles.warningBody, { color: disagreeColors.text }]}>
            Class {result.siteClassVs30} (Vs30) vs. Class {result.siteClassSpt} (SPT-N) at this location.
            This discrepancy is documented in Indian soils — a shallow weathered crust can register a
            stiffer SPT-N refusal even where the deeper Vs30-averaged profile is soft — and is not a data error.
          </Text>
        </View>
      )}

      <Text style={styles.sectionLabel}>Recent earthquakes (300 km radius)</Text>
      {result.earthquakes.map((eq, i) => {
        const severity = eq.magnitude >= 6 ? 'High' : eq.magnitude >= 5 ? 'Moderate' : 'Low';
        const severityLabel = eq.magnitude >= 6 ? 'Strong' : eq.magnitude >= 5 ? 'Moderate' : 'Light';
        const severityColors = RISK_COLORS[severity];
        return (
          <View key={i} style={styles.eqRow}>
            <View>
              <Text style={styles.eqMag}>M {eq.magnitude.toFixed(1)}</Text>
              <Text style={styles.eqInfo}>{eq.place} · {eq.year} · depth {eq.depth} km</Text>
            </View>
            <View style={[styles.pill, { backgroundColor: severityColors.bg }]}>
              <Text style={[styles.pillText, { color: severityColors.text }]}>{severityLabel}</Text>
            </View>
          </View>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: Colors.background },
  container: { padding: Space.md, paddingBottom: Space.xl + Space.sm },
  card: {
    backgroundColor: Palette.white,
    borderWidth: 1, borderColor: Colors.border, borderRadius: Radius.sm,
    padding: Space.md, marginBottom: Space.md,
  },
  cardHead: { ...Type.label, color: Colors.textMuted, marginBottom: Space.sm + 2 },
  row: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingVertical: Space.sm - 2, borderBottomWidth: 0.5, borderBottomColor: Colors.border,
  },
  rowLabel: { ...Type.bodySmall, color: Colors.textSecondary },
  rowValue: { ...Type.mono, color: Colors.textPrimary },
  warningBanner: { borderWidth: 1, borderRadius: Radius.sm, padding: Space.sm + 4, marginBottom: Space.md },
  warningTitle: { ...Type.bodySmall, fontWeight: '500', marginBottom: Space.xs },
  warningBody: { ...Type.bodySmall },
  sectionLabel: { ...Type.label, color: Colors.textMuted, marginBottom: Space.sm + 2 },
  eqRow: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingVertical: Space.sm + 2, borderBottomWidth: 0.5, borderBottomColor: Colors.border,
  },
  eqMag: { ...Type.heading, color: Colors.textPrimary },
  eqInfo: { ...Type.label, color: Colors.textSecondary, marginTop: Space.xs / 2 },
  // Same 2px radius as CoverageBadge (see components/CoverageBadge.tsx) —
  // every small technical pill/tag in the app shares this treatment.
  pill: { borderRadius: 2, paddingHorizontal: Space.sm, paddingVertical: Space.xs },
  pillText: { ...Type.badge },
});
