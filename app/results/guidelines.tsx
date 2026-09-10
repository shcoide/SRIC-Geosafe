import React from 'react';
import { ScrollView, StyleSheet } from 'react-native';
import { router } from 'expo-router';
import { useLocationStore } from '../../store/useLocationStore';
import { GuidelineItem } from '../../components/GuidelineItem';
import { EmptyState } from '../../components/EmptyState';
import { Colors } from '../../constants/colors';
import { Space } from '../../constants/spacing';

export default function GuidelinesScreen() {
  const result = useLocationStore((s) => s.currentResult);
  if (!result) {
    return (
      <EmptyState
        icon="clipboard-text-outline"
        title="No design guidelines"
        message="Search for a location from the Search tab to see architectural guidelines here."
        actionLabel="Go to search"
        onAction={() => router.replace('/(tabs)')}
      />
    );
  }

  return (
    <ScrollView style={styles.scroll} contentContainerStyle={styles.container}>
      {result.guidelines.map((g, i) => (
        <GuidelineItem key={i} guideline={g} />
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: Colors.background },
  container: { padding: Space.md, paddingBottom: Space.xl + Space.sm },
});
