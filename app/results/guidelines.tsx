import React from 'react';
import { ScrollView, View, Text, StyleSheet } from 'react-native';
import { useLocationStore } from '../../store/useLocationStore';
import { Colors } from '../../constants/colors';

export default function GuidelinesScreen() {
  const result = useLocationStore((s) => s.currentResult);
  if (!result) return null;

  return (
    <ScrollView style={{ flex: 1, backgroundColor: '#fff' }} contentContainerStyle={styles.container}>
      {result.guidelines.map((g, i) => (
        <View key={i} style={styles.item}>
          <Text style={styles.category}>{g.category}</Text>
          <Text style={styles.rec}>{g.recommendation}</Text>
          <Text style={styles.detail}>{g.detail}</Text>
          <View style={styles.codeBadge}>
            <Text style={styles.codeText}>{g.isCodeRef}</Text>
          </View>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, paddingBottom: 40 },
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
