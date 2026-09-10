import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors } from '../constants/colors';
import { Type } from '../constants/typography';
import { Space } from '../constants/spacing';
import { ArchitecturalGuideline } from '../types';

interface Props {
  guideline: ArchitecturalGuideline;
}

export const GuidelineItem: React.FC<Props> = ({ guideline }) => {
  return (
    <View style={styles.item}>
      <Text style={styles.category}>{guideline.category}</Text>
      <Text style={styles.rec}>{guideline.recommendation}</Text>
      <Text style={styles.detail}>{guideline.detail}</Text>
      <View style={styles.codeBadge}>
        <Text style={styles.codeText}>{guideline.isCodeRef}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  item: { paddingVertical: Space.md - 4, borderBottomWidth: 0.5, borderBottomColor: Colors.border },
  category: { ...Type.label, color: Colors.textMuted, marginBottom: Space.xs - 1 },
  rec: { ...Type.heading, color: Colors.textPrimary, marginBottom: Space.xs - 1 },
  detail: { ...Type.body, color: Colors.textSecondary },
  codeBadge: {
    alignSelf: 'flex-start', marginTop: Space.sm - 2,
    backgroundColor: Colors.surface,
    // Same 2px radius as CoverageBadge/source badges (see components/CoverageBadge.tsx).
    borderRadius: 2,
    paddingHorizontal: Space.sm, paddingVertical: 2,
  },
  codeText: { ...Type.mono, color: Colors.textMuted },
});
