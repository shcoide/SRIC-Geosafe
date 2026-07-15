import React, { useState, useCallback } from 'react';
import {
  View, Text, FlatList, TouchableOpacity,
  StyleSheet, SafeAreaView, Alert
} from 'react-native';
import { router } from 'expo-router';
import { SearchBar } from '../../components/SearchBar';
import { LoadingOverlay } from '../../components/LoadingOverlay';
import { useLocationStore } from '../../store/useLocationStore';
import { analyzeLocation } from '../../services/api';
import { searchLocations } from '../../services/geocoding';
import { getCurrentCoordinates, reverseGeocode } from '../../services/location';
import { SearchResult } from '../../types';
import { Colors } from '../../constants/colors';

export default function HomeScreen() {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<SearchResult[]>([]);
  const { loading, setLoading, setCurrentResult, addRecentSearch, recentSearches } =
    useLocationStore();

  const handleSearch = useCallback(async (text: string) => {
    setQuery(text);
    if (text.length >= 3) {
      const results = await searchLocations(text);
      setSuggestions(results);
    } else {
      setSuggestions([]);
    }
  }, []);

  const handleSelect = useCallback(async (item: SearchResult) => {
    setQuery('');
    setSuggestions([]);
    setLoading(true);
    try {
      const result = await analyzeLocation({
        lat: item.lat,
        lon: item.lon,
        locationName: item.name,
      });
      setCurrentResult(result);
      addRecentSearch(item);
      router.push(`/results/${result.locationId}`);
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Could not analyse this location. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleGps = useCallback(async () => {
    setLoading(true);
    try {
      const coords = await getCurrentCoordinates();
      const name = await reverseGeocode(coords.lat, coords.lon);
      await handleSelect({ name, displayName: name, lat: coords.lat, lon: coords.lon });
    } catch (e: any) {
      Alert.alert('Location error', e.message);
      setLoading(false);
    }
  }, [handleSelect]);

  if (loading) return <LoadingOverlay message="Analysing location seismic risk…" />;

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <Text style={styles.appTitle}>GeoSafe</Text>
        <Text style={styles.appSub}>Seismic risk intelligence for any location</Text>

        <SearchBar
          value={query}
          onChangeText={handleSearch}
          onGpsPress={handleGps}
        />

        {suggestions.length > 0 && (
          <View style={styles.suggestions}>
            {suggestions.map((item, i) => (
              <TouchableOpacity
                key={i}
                style={styles.suggestion}
                onPress={() => handleSelect(item)}
              >
                <Text style={styles.suggestionText}>{item.displayName}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {suggestions.length === 0 && recentSearches.length > 0 && (
          <>
            <Text style={styles.sectionLabel}>Recent searches</Text>
            <FlatList
              data={recentSearches}
              keyExtractor={(_, i) => String(i)}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={styles.recentItem}
                  onPress={() => handleSelect(item)}
                >
                  <Text style={styles.recentName}>{item.name}</Text>
                  <Text style={styles.recentSub}>{item.displayName}</Text>
                </TouchableOpacity>
              )}
            />
          </>
        )}

        {suggestions.length === 0 && recentSearches.length === 0 && (
          <View style={styles.emptyState}>
            <Text style={styles.emptyText}>Search any Indian city or district to see its seismic risk profile and construction recommendations.</Text>
          </View>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#fff' },
  container: { flex: 1, padding: 16 },
  appTitle: { fontSize: 26, fontWeight: '500', color: Colors.text.primary, marginBottom: 2 },
  appSub: { fontSize: 13, color: Colors.text.secondary, marginBottom: 20 },
  sectionLabel: {
    fontSize: 10, fontWeight: '500', color: Colors.text.muted,
    textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8,
  },
  suggestions: {
    borderWidth: 0.5, borderColor: Colors.surface.border,
    borderRadius: 10, overflow: 'hidden', marginBottom: 12,
  },
  suggestion: {
    padding: 12, borderBottomWidth: 0.5, borderBottomColor: Colors.surface.border,
  },
  suggestionText: { fontSize: 13, color: Colors.text.primary },
  recentItem: {
    paddingVertical: 10, borderBottomWidth: 0.5, borderBottomColor: Colors.surface.border,
  },
  recentName: { fontSize: 13, fontWeight: '500', color: Colors.text.primary },
  recentSub: { fontSize: 11, color: Colors.text.secondary, marginTop: 1 },
  emptyState: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 24 },
  emptyText: { fontSize: 14, color: Colors.text.secondary, textAlign: 'center', lineHeight: 22 },
});
