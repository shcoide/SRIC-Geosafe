import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity,
  StyleSheet, Alert
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { SearchBar } from '../../components/SearchBar';
import { LoadingOverlay } from '../../components/LoadingOverlay';
import { CoverageBadge } from '../../components/CoverageBadge';
import { useLocationStore } from '../../store/useLocationStore';
import { analyzeLocation, getCoverage, checkCoverage, describeApiError } from '../../services/api';
import { searchLocations } from '../../services/geocoding';
import { getCurrentCoordinates, reverseGeocode } from '../../services/location';
import { SearchResult, CoverageRegion } from '../../types';
import { Colors } from '../../constants/colors';
import { RISK_COLORS, ZONE_RISK } from '../../constants/riskConfig';

export default function HomeScreen() {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<SearchResult[]>([]);
  const { loading, setLoading, setCurrentResult, addRecentSearch, recentSearches } =
    useLocationStore();

  const [regions, setRegions] = useState<CoverageRegion[]>([]);
  const [regionsError, setRegionsError] = useState<string | null>(null);
  const [expandedRegionId, setExpandedRegionId] = useState<string | null>(null);
  const [searchNote, setSearchNote] = useState<{ name: string; distanceKm: number } | null>(null);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setRegions(await getCoverage());
      } catch (e) {
        setRegionsError(describeApiError(e));
      }
    })();
  }, []);

  const handleSearch = useCallback((text: string) => {
    setQuery(text);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (text.length < 3) { setSuggestions([]); return; }

    debounceRef.current = setTimeout(async () => {
      const results = await searchLocations(text);
      setSuggestions(results);
    }, 400);
  }, []);

  const handleSelect = useCallback(async (item: SearchResult) => {
    setQuery('');
    setSuggestions([]);
    setSearchNote(null);

    try {
      // Advisory only — never blocks the search. Shown briefly so the user
      // actually sees it before the full analysis takes over the screen.
      const coverage = await checkCoverage(item.lat, item.lon).catch(() => null);
      if (coverage && !coverage.inCoverage && coverage.nearestRegion) {
        setSearchNote({ name: coverage.nearestRegion.name, distanceKm: coverage.nearestRegion.distanceKm });
        await new Promise((resolve) => setTimeout(resolve, 900));
      }

      setLoading(true);
      const result = await analyzeLocation({
        lat: item.lat,
        lon: item.lon,
        locationName: item.name,
      });
      setCurrentResult(result);
      addRecentSearch(item);
      router.push(`/results/${result.locationId}`);
    } catch (e: any) {
      Alert.alert('Error', describeApiError(e));
    } finally {
      setLoading(false);
      setSearchNote(null);
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

  const toggleExpanded = (id: string) => {
    setExpandedRegionId((prev) => (prev === id ? null : id));
  };

  const handleViewOnMap = (region: CoverageRegion) => {
    router.push({ pathname: '/(tabs)/map', params: { regionId: region.id } });
  };

  if (loading) return <LoadingOverlay message="Analysing location seismic risk…" />;

  const calibratedCount = regions.filter((r) => r.dataQuality === 'calibrated').length;

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView style={styles.container} contentContainerStyle={styles.containerContent}>
        <Text style={styles.appTitle}>GeoSafe</Text>
        <Text style={styles.appSub}>Seismic risk intelligence for any location</Text>

        <SearchBar
          value={query}
          onChangeText={handleSearch}
          onGpsPress={handleGps}
        />

        {searchNote && (
          <View style={styles.searchNote}>
            <Text style={styles.searchNoteText}>
              Outside calibrated coverage — nearest region is {searchNote.name} ({searchNote.distanceKm.toFixed(0)} km away). This analysis will use regional estimates.
            </Text>
          </View>
        )}

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

        {regionsError && (
          <View style={styles.errorBanner}>
            <Text style={styles.errorBannerText}>Coverage data unavailable: {regionsError}</Text>
          </View>
        )}

        {regions.length > 0 && (
          <View style={styles.coverageSection}>
            <Text style={styles.coverageSummary}>
              {calibratedCount} of {regions.length} covered regions have point-calibrated data; the rest are city-scale regional estimates. Searches outside these regions also return a regional estimate.
            </Text>

            {regions.map((region) => {
              const expanded = expandedRegionId === region.id;
              const zoneColor = RISK_COLORS[ZONE_RISK[region.seismicZone] as keyof typeof RISK_COLORS];
              return (
                <View key={region.id} style={styles.regionCard}>
                  <TouchableOpacity style={styles.regionCardHeader} onPress={() => toggleExpanded(region.id)}>
                    <View style={styles.regionCardHeaderText}>
                      <Text style={styles.regionName}>{region.name}</Text>
                      <Text style={styles.regionState}>{region.state}</Text>
                    </View>
                    <View style={[styles.zoneBadge, { backgroundColor: zoneColor.bg, borderColor: zoneColor.border }]}>
                      <Text style={[styles.zoneBadgeText, { color: zoneColor.text }]}>Zone {region.seismicZone}</Text>
                    </View>
                  </TouchableOpacity>

                  <View style={styles.regionMetaRow}>
                    <CoverageBadge quality={region.dataQuality} compact />
                    <Text style={styles.regionCount}>
                      {region.counts.calibratedPoints} calibrated point{region.counts.calibratedPoints === 1 ? '' : 's'}
                    </Text>
                  </View>

                  {expanded && (
                    <View style={styles.pointsList}>
                      {region.calibratedPoints.length === 0 ? (
                        <Text style={styles.noPointsText}>No calibrated points in this region yet.</Text>
                      ) : (
                        region.calibratedPoints.map((point) => (
                          <TouchableOpacity
                            key={point.name}
                            style={styles.pointRow}
                            onPress={() => handleSelect({
                              name: point.name,
                              displayName: `${point.name}, ${region.name}`,
                              lat: point.lat,
                              lon: point.lon,
                            })}
                          >
                            <Text style={styles.pointName}>{point.name}</Text>
                            {point.hasSptData && <Text style={styles.pointSpt}>SPT-N surveyed</Text>}
                          </TouchableOpacity>
                        ))
                      )}
                    </View>
                  )}

                  <TouchableOpacity style={styles.viewMapBtn} onPress={() => handleViewOnMap(region)}>
                    <Text style={styles.viewMapBtnText}>View on map</Text>
                  </TouchableOpacity>
                </View>
              );
            })}
          </View>
        )}

        {suggestions.length === 0 && recentSearches.length > 0 && (
          <>
            <Text style={styles.sectionLabel}>Recent searches</Text>
            {recentSearches.map((item, i) => (
              <TouchableOpacity
                key={i}
                style={styles.recentItem}
                onPress={() => handleSelect(item)}
              >
                <Text style={styles.recentName}>{item.name}</Text>
                <Text style={styles.recentSub}>{item.displayName}</Text>
              </TouchableOpacity>
            ))}
          </>
        )}

        {suggestions.length === 0 && recentSearches.length === 0 && regions.length === 0 && !regionsError && (
          <View style={styles.emptyState}>
            <Text style={styles.emptyText}>Search any Indian city or district to see its seismic risk profile and construction recommendations.</Text>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#fff' },
  container: { flex: 1 },
  containerContent: { padding: 16, paddingBottom: 40 },
  appTitle: { fontSize: 26, fontWeight: '500', color: Colors.text.primary, marginBottom: 2 },
  appSub: { fontSize: 13, color: Colors.text.secondary, marginBottom: 20 },
  sectionLabel: {
    fontSize: 10, fontWeight: '500', color: Colors.text.muted,
    textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8, marginTop: 8,
  },
  searchNote: {
    backgroundColor: Colors.surface.secondary, borderRadius: 8, padding: 10, marginTop: 10,
  },
  searchNoteText: { fontSize: 11, color: Colors.text.secondary, lineHeight: 16 },
  suggestions: {
    borderWidth: 0.5, borderColor: Colors.surface.border,
    borderRadius: 10, overflow: 'hidden', marginTop: 12,
  },
  suggestion: {
    padding: 12, borderBottomWidth: 0.5, borderBottomColor: Colors.surface.border,
  },
  suggestionText: { fontSize: 13, color: Colors.text.primary },
  errorBanner: { backgroundColor: '#FCEBEB', borderRadius: 8, padding: 10, marginTop: 12 },
  errorBannerText: { fontSize: 11, color: '#791F1F' },
  coverageSection: { marginTop: 20 },
  coverageSummary: { fontSize: 12, color: Colors.text.secondary, lineHeight: 18, marginBottom: 12 },
  regionCard: {
    borderWidth: 0.5, borderColor: Colors.surface.border, borderRadius: 10,
    padding: 12, marginBottom: 10,
  },
  regionCardHeader: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 },
  regionCardHeaderText: { flex: 1 },
  regionName: { fontSize: 14, fontWeight: '500', color: Colors.text.primary },
  regionState: { fontSize: 11, color: Colors.text.muted, marginTop: 1 },
  zoneBadge: { borderRadius: 6, borderWidth: 0.5, paddingHorizontal: 8, paddingVertical: 3 },
  zoneBadgeText: { fontSize: 11, fontWeight: '500' },
  regionMetaRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 8 },
  regionCount: { fontSize: 11, color: Colors.text.secondary },
  pointsList: { marginTop: 8, borderTopWidth: 0.5, borderTopColor: Colors.surface.border, paddingTop: 8, gap: 2 },
  noPointsText: { fontSize: 11, color: Colors.text.muted, fontStyle: 'italic' },
  pointRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingVertical: 6,
  },
  pointName: { fontSize: 12, color: Colors.primary, fontWeight: '500' },
  pointSpt: { fontSize: 10, color: Colors.text.muted },
  viewMapBtn: { marginTop: 8, alignSelf: 'flex-start' },
  viewMapBtnText: { fontSize: 11, fontWeight: '500', color: Colors.primary },
  recentItem: {
    paddingVertical: 10, borderBottomWidth: 0.5, borderBottomColor: Colors.surface.border,
  },
  recentName: { fontSize: 13, fontWeight: '500', color: Colors.text.primary },
  recentSub: { fontSize: 11, color: Colors.text.secondary, marginTop: 1 },
  emptyState: { alignItems: 'center', paddingHorizontal: 24, paddingTop: 60 },
  emptyText: { fontSize: 14, color: Colors.text.secondary, textAlign: 'center', lineHeight: 22 },
});
