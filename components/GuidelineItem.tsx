import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors } from '../constants/colors';
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
  item: { paddingVertical: 12, borderBottomWidth: 0.5, borderBottomColor: Colors.surface.border },
  category: { fontSize: 10, color: Colors.text.muted, marginBottom: 3 },
  rec: { fontSize: 13, fontWeight: '500', color: Colors.text.primary, marginBottom: 3 },
  detail: { fontSize: 12, color: Colors.text.secondary, lineHeight: 18 },
  codeBadge: {
    alignSelf: 'flex-start', marginTop: 6,
    backgroundColor: Colors.surface.secondary,
    borderWidth: 0.5, borderColor: Colors.surface.border,
    borderRadius: 4, paddingHorizontal: 6, paddingVertical: 2,
  },
  codeText: { fontSize: 9, color: Colors.text.muted },
});
