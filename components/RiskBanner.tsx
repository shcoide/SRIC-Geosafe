import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { RISK_COLORS } from '../constants/riskConfig';
import { Colors, Palette } from '../constants/colors';
import { Type } from '../constants/typography';
import { Space } from '../constants/spacing';

interface Props {
  risk: 'Low' | 'Moderate' | 'High' | 'Very High';
  zone: string;
  surfacePga: number;
  vs30: number;
  siteClassVs30?: string;
}

export const RiskBanner: React.FC<Props> = ({ risk, zone, surfacePga, vs30, siteClassVs30 }) => {
  const colors = RISK_COLORS[risk];
  return (
    <View style={[styles.container, { borderLeftColor: colors.dot }]}>
      <View style={styles.zoneRow}>
        <View style={[styles.zonePill, { backgroundColor: colors.dot }]}>
          <Text style={styles.zonePillText}>Zone {zone}</Text>
        </View>
        <Text style={styles.isCode}>IS 1893:2016</Text>
      </View>

      <Text style={[styles.riskText, { color: colors.text }]}>{risk}</Text>
      <Text style={styles.descriptor}>Seismic risk at this site</Text>

      <View style={styles.divider} />

      <View style={styles.dataRow}>
        <View style={styles.dataItem}>
          <Text style={styles.dataLabel}>PGA</Text>
          <Text style={styles.dataValue}>{surfacePga.toFixed(2)}g</Text>
        </View>
        <View style={styles.vDivider} />
        <View style={styles.dataItem}>
          <Text style={styles.dataLabel}>Vs30</Text>
          <Text style={styles.dataValue}>{Math.round(vs30)} m/s</Text>
        </View>
        {siteClassVs30 ? (
          <>
            <View style={styles.vDivider} />
            <View style={styles.dataItem}>
              <Text style={styles.dataLabel}>Site class</Text>
              <Text style={styles.dataValue}>{siteClassVs30}</Text>
            </View>
          </>
        ) : null}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: Palette.white,
    borderLeftWidth: 4,
    borderTopWidth: 0.5,
    borderRightWidth: 0.5,
    borderBottomWidth: 0.5,
    borderColor: Colors.border,
    borderTopRightRadius: 6,
    borderBottomRightRadius: 6,
    padding: Space.md,
    marginBottom: Space.md,
  },
  zoneRow: { flexDirection: 'row', alignItems: 'center', gap: Space.sm, marginBottom: 10 },
  zonePill: { borderRadius: 3, paddingHorizontal: Space.sm, paddingVertical: 3 },
  zonePillText: { fontSize: 11, fontWeight: '500', color: Palette.white },
  isCode: { fontSize: 11, color: Colors.textMuted },
  riskText: { fontSize: 40, fontWeight: '200', letterSpacing: -1 },
  descriptor: { fontSize: 13, color: Colors.textSecondary, marginBottom: 14 },
  divider: { height: 1, backgroundColor: Colors.divider, marginBottom: 12 },
  dataRow: { flexDirection: 'row', alignItems: 'flex-start' },
  dataItem: { paddingHorizontal: Space.sm },
  dataLabel: { fontSize: 10, color: Colors.textMuted, marginBottom: 2 },
  dataValue: { ...Type.mono, fontSize: 13, color: Colors.textPrimary },
  vDivider: { width: 1, height: 28, backgroundColor: Colors.border },
});
