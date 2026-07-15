import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors } from '../constants/colors';
import { MaterialRecommendation } from '../types';

interface Props {
  material: MaterialRecommendation;
}

const rankColors = [
  { bg: '#E1F5EE', text: '#085041' },
  { bg: '#E6F1FB', text: '#0C447C' },
  { bg: '#F1EFE8', text: '#444441' },
];

export const MaterialCard: React.FC<Props> = ({ material }) => {
  const rc = rankColors[Math.min(material.rank - 1, 2)];
  return (
    <View style={styles.container}>
      <View style={[styles.rank, { backgroundColor: rc.bg }]}>
        <Text style={[styles.rankText, { color: rc.text }]}>{material.rank}</Text>
      </View>
      <View style={styles.content}>
        <Text style={styles.name}>{material.name}</Text>
        <Text style={styles.reason}>{material.reason}</Text>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{material.isCode}</Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    paddingVertical: 10,
    borderBottomWidth: 0.5,
    borderBottomColor: Colors.surface.border,
  },
  rank: {
    width: 22,
    height: 22,
    borderRadius: 11,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 1,
  },
  rankText: { fontSize: 10, fontWeight: '600' },
  content: { flex: 1 },
  name: { fontSize: 13, fontWeight: '500', color: Colors.text.primary, marginBottom: 2 },
  reason: { fontSize: 11, color: Colors.text.secondary, lineHeight: 16 },
  badge: {
    alignSelf: 'flex-start',
    marginTop: 4,
    backgroundColor: Colors.surface.secondary,
    borderWidth: 0.5,
    borderColor: Colors.surface.border,
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  badgeText: { fontSize: 9, color: Colors.text.muted },
});
