import React, { useState } from 'react';
import { ScrollView, View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Alert } from 'react-native';
import { router } from 'expo-router';
import { useLocationStore } from '../../store/useLocationStore';
import { analyzeLocation, describeApiError } from '../../services/api';
import { MaterialCard } from '../../components/MaterialCard';
import { EmptyState } from '../../components/EmptyState';
import { Colors, Palette } from '../../constants/colors';
import { RISK_COLORS } from '../../constants/riskConfig';
import { Type } from '../../constants/typography';
import { Space, Radius } from '../../constants/spacing';
import { BudgetPreference } from '../../types';

const BUDGET_CHIPS: { value: BudgetPreference; label: string }[] = [
  { value: 'any', label: 'Any budget' },
  { value: 'low', label: 'Low cost' },
  { value: 'moderate', label: 'Moderate' },
];

export default function MaterialsScreen() {
  const result = useLocationStore((s) => s.currentResult);
  const setCurrentResult = useLocationStore((s) => s.setCurrentResult);
  // AnalyzeResponse doesn't report which budget_preference produced the
  // current result, so this defaults to "any" (the app-wide default) on
  // first render — from then on it tracks whichever chip was actually
  // tapped here, since a successful re-fetch below stores exactly that
  // value back into this same state.
  const [selectedBudget, setSelectedBudget] = useState<BudgetPreference>('any');
  // Local to this screen only — deliberately not the global store's
  // `loading` flag, which drives a full-screen overlay elsewhere in the
  // app; changing one ranking parameter shouldn't blank the whole screen.
  const [refetching, setRefetching] = useState(false);

  const handleBudgetChange = async (value: BudgetPreference) => {
    if (!result || value === selectedBudget) return;
    // Updates the active chip immediately, before the request even starts,
    // so the tap visibly registers regardless of how long the fetch takes.
    setSelectedBudget(value);
    setRefetching(true);
    try {
      const updated = await analyzeLocation({
        lat: result.coordinates.lat,
        lon: result.coordinates.lon,
        locationName: result.name,
        budgetPreference: value,
      });
      setCurrentResult(updated);
    } catch (e) {
      Alert.alert('Error', describeApiError(e));
    } finally {
      setRefetching(false);
    }
  };

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

  const modColors = RISK_COLORS['Moderate'];
  // Zone IV's zone factor (ZONE_PGA["IV"] in backend/services/inference.py)
  // is 0.24g — used here as the surfaceSa threshold for "Zone IV/V-like
  // demand" rather than re-deriving it from seismicZone, since surfaceSa is
  // the actual value the fragility ranking (and this disclaimer) cares
  // about, and it can exceed 0.24g even in a nominally lower zone once
  // amplification/resonance are folded in.
  const elevatedDemand = result.surfaceSa > 0.24;

  return (
    <ScrollView style={styles.scroll} contentContainerStyle={styles.container}>
      <Text style={styles.title}>Structural system assessment</Text>
      <View style={styles.chipRow}>
        {BUDGET_CHIPS.map((chip) => {
          const active = selectedBudget === chip.value;
          return (
            <TouchableOpacity
              key={chip.value}
              style={[styles.chip, active && styles.chipActive]}
              onPress={() => handleBudgetChange(chip.value)}
              disabled={refetching}
            >
              <Text style={[styles.chipText, active && styles.chipTextActive]}>{chip.label}</Text>
            </TouchableOpacity>
          );
        })}
        {refetching && <ActivityIndicator size="small" color={Colors.primary} style={styles.chipRowSpinner} />}
      </View>

      {elevatedDemand && (
        <View style={[styles.disclaimerBanner, { backgroundColor: modColors.bg, borderLeftColor: modColors.border }]}>
          <Text style={[styles.disclaimerIcon, { color: modColors.dot }]}>⚠</Text>
          <Text style={[styles.disclaimerText, { color: modColors.text }]}>
            All systems face elevated demand here. Rankings show relative performance.
          </Text>
        </View>
      )}

      <View style={{ opacity: refetching ? 0.5 : 1 }}>
        <Text style={styles.sectionLabel}>Recommended structural systems</Text>
        {result.materials.filter(m => m.suitable).map((m, i) => (
          <MaterialCard key={i} material={m} />
        ))}

        <Text style={[styles.sectionLabel, styles.avoidSectionLabel]}>Not recommended at this site</Text>
        {result.materials.filter(m => !m.suitable).map((m, i) => (
          <MaterialCard key={i} material={m} />
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: Colors.background },
  container: { padding: Space.md, paddingBottom: Space.xl + Space.sm },
  title: { ...Type.title, color: Colors.textPrimary, marginBottom: Space.sm + 2 },
  chipRow: { flexDirection: 'row', alignItems: 'center', gap: Space.xs + 2, marginBottom: Space.md },
  chipRowSpinner: { marginLeft: Space.xs },
  chip: {
    height: 32, borderRadius: 16, paddingHorizontal: 14,
    alignItems: 'center', justifyContent: 'center',
    backgroundColor: Colors.surface,
  },
  chipActive: { backgroundColor: Colors.primary },
  chipText: { fontSize: 12, color: Colors.textSecondary },
  chipTextActive: { color: Palette.white, fontWeight: '500' },
  disclaimerBanner: {
    flexDirection: 'row', alignItems: 'flex-start', gap: Space.xs + 2,
    borderLeftWidth: 3, borderRadius: Radius.sm,
    padding: Space.sm + 4, marginBottom: Space.md,
  },
  disclaimerIcon: { fontSize: 14, lineHeight: 16 },
  disclaimerText: { fontSize: 12, flex: 1 },
  sectionLabel: { ...Type.label, color: Colors.textMuted, marginBottom: Space.sm },
  avoidSectionLabel: {
    color: Colors.textSecondary, fontSize: 12, fontWeight: '500',
    marginTop: 20, marginBottom: Space.sm,
  },
});
