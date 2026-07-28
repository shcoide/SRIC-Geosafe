import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { RISK_COLORS } from '../constants/riskConfig';

interface Props {
  risk: 'Low' | 'Moderate' | 'High' | 'Very High';
  zone: string;
  surfacePga: number;
  vs30: number;
}

export const RiskBanner: React.FC<Props> = ({ risk, zone, surfacePga, vs30 }) => {
  const colors = RISK_COLORS[risk];
  return (
    <View style={[styles.container, { backgroundColor: colors.bg, borderColor: colors.border }]}>
      <Text style={[styles.label, { color: colors.text }]}>Overall seismic risk</Text>
      <Text style={[styles.riskText, { color: colors.text }]}>{risk}</Text>
      <Text style={[styles.meta, { color: colors.text }]}>
        IS 1893 Zone {zone} · Surface PGA {surfacePga.toFixed(2)}g · Vs30 {Math.round(vs30)} m/s
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    borderRadius: 10,
    borderWidth: 0.5,
    padding: 14,
    marginBottom: 12,
  },
  label: { fontSize: 11, fontWeight: '500', letterSpacing: 0.4, marginBottom: 2 },
  riskText: { fontSize: 22, fontWeight: '500', marginBottom: 2 },
  meta: { fontSize: 11, opacity: 0.8 },
});
