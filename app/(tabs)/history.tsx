import React from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, SafeAreaView } from 'react-native';
import { router } from 'expo-router';
import { useLocationStore } from '../../store/useLocationStore';
import { analyzeLocation } from '../../services/api';
import { Colors } from '../../constants/colors';
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
        contentContainerStyle={{ padding: 16 }}
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
  safe: { flex: 1, backgroundColor: '#fff' },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 },
  emptyText: { fontSize: 14, color: Colors.text.secondary, textAlign: 'center' },
  item: { paddingVertical: 12, borderBottomWidth: 0.5, borderBottomColor: Colors.surface.border },
  name: { fontSize: 14, fontWeight: '500', color: Colors.text.primary },
  sub: { fontSize: 12, color: Colors.text.secondary, marginTop: 2 },
});
