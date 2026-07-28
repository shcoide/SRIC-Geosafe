import React from 'react';
import { ScrollView, View, Text, StyleSheet } from 'react-native';
import { router } from 'expo-router';
import { useLocationStore } from '../../store/useLocationStore';
import { EmptyState } from '../../components/EmptyState';
import { Colors } from '../../constants/colors';

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

  return (
    <ScrollView style={{ flex: 1, backgroundColor: '#fff' }} contentContainerStyle={styles.container}>
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
      </View>

      {classesDisagree && (
        <View style={styles.warningBanner}>
          <Text style={styles.warningTitle}>Vs30 and SPT-N site class disagree</Text>
          <Text style={styles.warningBody}>
            Class {result.siteClassVs30} (Vs30) vs. Class {result.siteClassSpt} (SPT-N) at this location.
            This discrepancy is documented in Indian soils — a shallow weathered crust can register a
            stiffer SPT-N refusal even where the deeper Vs30-averaged profile is soft — and is not a data error.
          </Text>
        </View>
      )}

      <Text style={styles.sectionLabel}>Recent earthquakes (300 km radius)</Text>
      {result.earthquakes.map((eq, i) => (
        <View key={i} style={styles.eqRow}>
          <View>
            <Text style={styles.eqMag}>M {eq.magnitude.toFixed(1)}</Text>
            <Text style={styles.eqInfo}>{eq.place} · {eq.year} · depth {eq.depth} km</Text>
          </View>
          <View style={[styles.pill, eq.magnitude >= 6 ? styles.pillHigh : eq.magnitude >= 5 ? styles.pillMod : styles.pillLow]}>
            <Text style={[styles.pillText, eq.magnitude >= 6 ? styles.pillTextHigh : eq.magnitude >= 5 ? styles.pillTextMod : styles.pillTextLow]}>
              {eq.magnitude >= 6 ? 'Strong' : eq.magnitude >= 5 ? 'Moderate' : 'Light'}
            </Text>
          </View>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, paddingBottom: 40 },
  card: { borderWidth: 0.5, borderColor: Colors.surface.border, borderRadius: 10, padding: 14, marginBottom: 16 },
  warningBanner: { backgroundColor: '#FAEEDA', borderWidth: 0.5, borderColor: '#FAC775', borderRadius: 10, padding: 12, marginBottom: 16 },
  warningTitle: { fontSize: 12, fontWeight: '500', color: '#633806', marginBottom: 4 },
  warningBody: { fontSize: 11, color: '#633806', lineHeight: 16 },
  cardHead: { fontSize: 10, fontWeight: '500', color: Colors.text.muted, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 10 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 6, borderBottomWidth: 0.5, borderBottomColor: Colors.surface.border },
  rowLabel: { fontSize: 12, color: Colors.text.secondary },
  rowValue: { fontSize: 12, fontWeight: '500', color: Colors.text.primary },
  sectionLabel: { fontSize: 10, fontWeight: '500', color: Colors.text.muted, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 10 },
  eqRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 0.5, borderBottomColor: Colors.surface.border },
  eqMag: { fontSize: 15, fontWeight: '500', color: Colors.text.primary },
  eqInfo: { fontSize: 10, color: Colors.text.secondary, marginTop: 2 },
  pill: { borderRadius: 10, paddingHorizontal: 8, paddingVertical: 3, borderWidth: 0.5 },
  pillHigh: { backgroundColor: '#FCEBEB', borderColor: '#F7C1C1' },
  pillMod: { backgroundColor: '#FAEEDA', borderColor: '#FAC775' },
  pillLow: { backgroundColor: '#E6F1FB', borderColor: '#B5D4F4' },
  pillText: { fontSize: 10, fontWeight: '500' },
  pillTextHigh: { color: '#791F1F' },
  pillTextMod: { color: '#633806' },
  pillTextLow: { color: '#0C447C' },
});
