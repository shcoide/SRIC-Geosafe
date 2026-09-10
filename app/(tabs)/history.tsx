import React from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { useLocationStore } from '../../store/useLocationStore';
import { analyzeLocation } from '../../services/api';
import { Colors, Palette } from '../../constants/colors';
import { Type } from '../../constants/typography';
import { Space, Radius } from '../../constants/spacing';
import { SearchResult } from '../../types';

export default function HistoryScreen() {
  const { recentSearches, setCurrentResult, setLoading } = useLocationStore();

  const handleSelect = async (item: SearchResult) => {
    setLoading(true);
    try {
      const result = await analyzeLocation({ lat: item.lat, lon: item.lon, locationName: item.name });
      setCurrentResult(result);
      router.push(`/results/${result.locationId}`);
    } finally {
      setLoading(false);
    }
  };

  if (recentSearches.length === 0) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.empty}>
          <Text style={styles.emptyText}>No recent searches yet. Search a location to get started.</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <FlatList
        data={recentSearches}
        keyExtractor={(_, i) => String(i)}
        contentContainerStyle={{ padding: Space.md }}
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.item} onPress={() => handleSelect(item)}>
            <Text style={styles.name}>{item.name}</Text>
            <Text style={styles.sub}>{item.displayName}</Text>
          </TouchableOpacity>
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: Space.lg },
  emptyText: { ...Type.bodySmall, color: Colors.textSecondary, textAlign: 'center' },
  item: {
    backgroundColor: Palette.white,
    borderWidth: 1, borderColor: Colors.border, borderRadius: Radius.md,
    padding: Space.sm + 4, marginBottom: Space.sm,
  },
  name: { ...Type.heading, color: Colors.textPrimary },
  sub: { ...Type.bodySmall, color: Colors.textSecondary, marginTop: 1 },
});
