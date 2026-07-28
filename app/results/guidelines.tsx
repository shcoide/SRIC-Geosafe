import React from 'react';
import { ScrollView, StyleSheet } from 'react-native';
import { router } from 'expo-router';
import { useLocationStore } from '../../store/useLocationStore';
import { GuidelineItem } from '../../components/GuidelineItem';
import { EmptyState } from '../../components/EmptyState';

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
    <ScrollView style={{ flex: 1, backgroundColor: '#fff' }} contentContainerStyle={styles.container}>
      {result.guidelines.map((g, i) => (
        <GuidelineItem key={i} guideline={g} />
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, paddingBottom: 40 },
});
