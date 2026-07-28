import React from 'react';
import { ScrollView, View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { router } from 'expo-router';
import { RiskBanner } from '../../components/RiskBanner';
import { HazardCard } from '../../components/HazardCard';
import { EmptyState } from '../../components/EmptyState';
import { useLocationStore } from '../../store/useLocationStore';
import { Colors } from '../../constants/colors';

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

      <TouchableOpacity style={styles.actionBtn} onPress={() => router.push('/results/materials')}>
        <Text style={styles.actionBtnText}>View material recommendations</Text>
      </TouchableOpacity>
      <TouchableOpacity style={styles.actionBtn} onPress={() => router.push('/results/guidelines')}>
        <Text style={styles.actionBtnText}>View architectural guidelines</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: '#fff' },
  container: { padding: 16, paddingBottom: 40 },
  locationName: { fontSize: 20, fontWeight: '500', color: Colors.text.primary, marginBottom: 2 },
  coords: { fontSize: 12, color: Colors.text.muted, marginBottom: 14 },
  sectionLabel: {
    fontSize: 10, fontWeight: '500', color: Colors.text.muted,
    textTransform: 'uppercase', letterSpacing: 0.5, marginTop: 16, marginBottom: 8,
  },
  hazardGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  statBox: {
    width: '47%', backgroundColor: Colors.surface.secondary,
    borderRadius: 8, padding: 12,
  },
  statNum: { fontSize: 18, fontWeight: '500', color: Colors.text.primary },
  statLabel: { fontSize: 10, color: Colors.text.secondary, marginTop: 2 },
  actionBtn: {
    marginTop: 10, borderWidth: 0.5, borderColor: Colors.primaryBorder,
    borderRadius: 10, padding: 14, alignItems: 'center', backgroundColor: Colors.primaryLight,
  },
  actionBtnText: { fontSize: 14, fontWeight: '500', color: Colors.primary },
});
