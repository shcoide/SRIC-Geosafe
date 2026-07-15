import React from 'react';
import { ScrollView, View, Text, StyleSheet } from 'react-native';
import { useLocationStore } from '../../store/useLocationStore';
import { MaterialCard } from '../../components/MaterialCard';
import { Colors } from '../../constants/colors';

export default function MaterialsScreen() {
  const result = useLocationStore((s) => s.currentResult);
  if (!result) return null;

  return (
    <ScrollView style={{ flex: 1, backgroundColor: '#fff' }} contentContainerStyle={styles.container}>
      <View style={styles.banner}>
        <Text style={styles.bannerLabel}>Recommendations based on</Text>
        <Text style={styles.bannerMain}>IS 1893 Zone {result.seismicZone} · {result.overallRisk} risk · NEHRP Class {result.siteClass}</Text>
      </View>

      <Text style={styles.sectionLabel}>Recommended structural systems</Text>
      {result.materials.filter(m => m.suitable).map((m, i) => (
        <MaterialCard key={i} material={m} />
      ))}

      <Text style={[styles.sectionLabel, { marginTop: 20 }]}>Avoid for this site</Text>
      {result.materials.filter(m => !m.suitable).map((m, i) => (
        <View key={i} style={styles.avoidRow}>
          <Text style={styles.avoidText}>{m.name}</Text>
          <Text style={styles.avoidReason}>{m.reason}</Text>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, paddingBottom: 40 },
  banner: { backgroundColor: Colors.primaryLight, borderWidth: 0.5, borderColor: Colors.primaryBorder, borderRadius: 10, padding: 12, marginBottom: 16 },
  bannerLabel: { fontSize: 10, color: Colors.primary, marginBottom: 2 },
  bannerMain: { fontSize: 12, fontWeight: '500', color: '#0C447C' },
  sectionLabel: { fontSize: 10, fontWeight: '500', color: Colors.text.muted, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 },
  avoidRow: { paddingVertical: 8, borderBottomWidth: 0.5, borderBottomColor: Colors.surface.border },
  avoidText: { fontSize: 12, fontWeight: '500', color: '#A32D2D' },
  avoidReason: { fontSize: 11, color: Colors.text.secondary, marginTop: 2 },
});
