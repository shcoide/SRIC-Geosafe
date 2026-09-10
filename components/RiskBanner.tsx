import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { RISK_COLORS } from '../constants/riskConfig';
import { Colors } from '../constants/colors';
import { Type } from '../constants/typography';
import { Space, Radius } from '../constants/spacing';

interface Props {
  risk: 'Low' | 'Moderate' | 'High' | 'Very High';
  zone: string;
  surfacePga: number;
  vs30: number;
  siteClassVs30?: string;
}

const hexToRgba = (hex: string, alpha: number): string => {
  const clean = hex.replace('#', '');
  const value = parseInt(clean, 16);
  const r = (value >> 16) & 255;
  const g = (value >> 8) & 255;
  const b = value & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

export const RiskBanner: React.FC<Props> = ({ risk, zone, surfacePga, vs30, siteClassVs30 }) => {
  const colors = RISK_COLORS[risk];
  return (
    <View
      style={[
        styles.container,
        { backgroundColor: hexToRgba(colors.bg, 0.6), borderLeftColor: colors.dot },
      ]}
    >
      <Text style={[styles.zoneLine, { color: colors.text }]}>Zone {zone} · IS 1893</Text>

      <Text style={[styles.riskText, { color: colors.text }]}>{risk}</Text>
      <Text style={[styles.descriptor, { color: colors.text }]}>Seismic risk</Text>

      <Text style={styles.dataRow}>
        PGA {surfacePga.toFixed(2)}g  ·  Vs30 {Math.round(vs30)} m/s{siteClassVs30 ? `  ·  Class ${siteClassVs30}` : ''}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    borderRadius: Radius.sm,
    borderLeftWidth: 3,
    paddingVertical: Space.md,
    paddingHorizontal: Space.md,
    marginBottom: Space.md,
  },
  zoneLine: { ...Type.label, marginBottom: Space.sm },
  riskText: { ...Type.riskDisplay },
  descriptor: { ...Type.bodySmall, opacity: 0.75, marginBottom: Space.sm },
  dataRow: { ...Type.mono, color: Colors.textMuted },
});
