import React from 'react';
import { ScrollView, View, Text, StyleSheet } from 'react-native';
import { useLocationStore } from '../../store/useLocationStore';
import { Colors } from '../../constants/colors';

export default function EarthquakeScreen() {
  const result = useLocationStore((s) => s.currentResult);
  if (!result) return null;

  return (
    <ScrollView style={{ flex: 1, backgroundColor: '#fff' }} contentContainerStyle={styles.container}>
      <View style={styles.card}>
        <Text style={styles.cardHead}>Site parameters</Text>
        {[
          ['IS 1893 Zone', `Zone ${result.seismicZone}`],
          ['PGA (10% in 50 yr)', `${result.pga.toFixed(2)}g`],
          ['Vs30', `${Math.round(result.vs30)} m/s (NEHRP Class ${result.siteClass})`],
          ['Nearest fault', `${Math.round(result.distanceToFault)} km`],
          ['Liquefaction risk', result.liquefactionRisk],
        ].map(([label, value]) => (
          <View key={label} style={styles.row}>
            <Text style={styles.rowLabel}>{label}</Text>
            <Text style={styles.rowValue}>{value}</Text>
          </View>
        ))}
      </View>

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
