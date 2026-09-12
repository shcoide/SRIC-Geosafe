import React from 'react';
import { ScrollView, View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { router } from 'expo-router';
import { RiskBanner } from '../../components/RiskBanner';
import { HazardCard } from '../../components/HazardCard';
import { EmptyState } from '../../components/EmptyState';
import { useLocationStore } from '../../store/useLocationStore';
import { Colors, Palette } from '../../constants/colors';
import { Type } from '../../constants/typography';
import { Space, Radius } from '../../constants/spacing';

export default function ResultsOverview() {
  const result = useLocationStore((s) => s.currentResult);
  if (!result) {
    return (
      <EmptyState
        title="No location selected"
        message="Search for a location from the Search tab to see its hazard overview here."
        actionLabel="Go to search"
        onAction={() => router.replace('/(tabs)')}
      />
    );
  }

  return (
    <ScrollView style={styles.scroll} contentContainerStyle={styles.container}>
      <Text style={styles.locationName}>{result.name}</Text>
      <Text style={styles.coords}>
        {result.coordinates.lat.toFixed(4)}°N · {result.coordinates.lon.toFixed(4)}°E
      </Text>

      <RiskBanner
        risk={result.overallRisk as any}
        zone={result.seismicZone}
        surfacePga={result.surfacePga}
        vs30={result.vs30}
        siteClassVs30={result.siteClassVs30}
      />

      <Text style={styles.sectionLabel}>Hazard breakdown</Text>
      <View style={styles.hazardGrid}>
        {result.hazards.map((h, i) => (
          <HazardCard
            key={i}
            hazard={h}
            onPress={() => h.type === 'earthquake' && router.push('/results/earthquake')}
          />
        ))}
      </View>

      <Text style={styles.sectionLabel}>Key statistics</Text>
      <View style={styles.statsGrid}>
        <View style={styles.statBox}>
          <Text style={styles.statNum}>{result.earthquakes.length}</Text>
          <Text style={styles.statLabel}>Earthquakes M≥4 (50 yr)</Text>
        </View>
        <View style={styles.statBox}>
          <Text style={styles.statNum}>
            {result.earthquakes.length > 0
              ? Math.max(...result.earthquakes.map((e) => e.magnitude)).toFixed(1)
              : 'N/A'}
          </Text>
          <Text style={styles.statLabel}>Max magnitude nearby</Text>
        </View>
        {result.distanceToFault !== null && (
          <View style={styles.statBox}>
            <Text style={styles.statNum}>{Math.round(result.distanceToFault)} km</Text>
            <Text style={styles.statLabel}>Nearest active fault</Text>
          </View>
        )}
        <View style={styles.statBox}>
          <Text style={styles.statNum}>{result.liquefactionRisk}</Text>
          <Text style={styles.statLabel}>Liquefaction risk</Text>
        </View>
      </View>

      <TouchableOpacity style={styles.primaryBtn} onPress={() => router.push('/results/materials')}>
        <Text style={styles.primaryBtnText}>View material recommendations</Text>
      </TouchableOpacity>
      <TouchableOpacity style={styles.secondaryBtn} onPress={() => router.push('/results/guidelines')}>
        <Text style={styles.secondaryBtnText}>View architectural guidelines</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: Colors.background },
  container: { padding: Space.md, paddingBottom: 32 },
  locationName: { ...Type.title, color: Colors.textPrimary, marginBottom: Space.xs / 2 },
  coords: { ...Type.mono, color: Colors.textMuted, marginBottom: Space.md },
  sectionLabel: {
    ...Type.label, color: Colors.textMuted,
    marginTop: Space.lg, marginBottom: Space.sm,
  },
  hazardGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: Space.sm },
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: Space.sm },
  statBox: {
    width: '47%', backgroundColor: Palette.white,
    borderWidth: 1, borderColor: Colors.border,
    borderRadius: Radius.sm, padding: Space.sm + 4,
  },
  statNum: { ...Type.title, color: Colors.textPrimary },
  statLabel: { ...Type.label, color: Colors.textSecondary, marginTop: Space.xs / 2 },
  primaryBtn: {
    marginTop: Space.sm, borderRadius: Radius.md,
    paddingVertical: Space.md - 2, alignItems: 'center',
    backgroundColor: Colors.primary,
  },
  primaryBtnText: { ...Type.body, fontWeight: '500', color: Palette.white },
  secondaryBtn: {
    marginTop: Space.sm, borderRadius: Radius.md,
    paddingVertical: Space.md - 2, alignItems: 'center',
    backgroundColor: Palette.white, borderWidth: 1, borderColor: Colors.primaryBorder,
  },
  secondaryBtnText: { ...Type.body, fontWeight: '500', color: Colors.primary },
});
