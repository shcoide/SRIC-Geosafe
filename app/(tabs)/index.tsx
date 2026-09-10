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
import { SearchResult, CoverageRegion, BudgetPreference } from '../../types';
import { Colors, Palette } from '../../constants/colors';
import { Type } from '../../constants/typography';
import { Space, Radius } from '../../constants/spacing';
import { RISK_COLORS, ZONE_RISK } from '../../constants/riskConfig';

const BUDGET_OPTIONS: { value: BudgetPreference; label: string }[] = [
  { value: 'any', label: 'Any budget' },
  { value: 'low', label: 'Low cost' },
  { value: 'moderate', label: 'Moderate budget' },
];

export default function HomeScreen() {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<SearchResult[]>([]);
  const [budgetPreference, setBudgetPreference] = useState<BudgetPreference>('any');
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
        budgetPreference,
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
  }, [budgetPreference]);

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
        <Text style={styles.appSub}>Site-specific seismic assessment</Text>

        <SearchBar
          value={query}
          onChangeText={handleSearch}
          onGpsPress={handleGps}
        />

        <View style={styles.budgetRow}>
          {BUDGET_OPTIONS.map((opt) => {
            const active = budgetPreference === opt.value;
            return (
              <TouchableOpacity
                key={opt.value}
                style={[styles.budgetChip, active && styles.budgetChipActive]}
                onPress={() => setBudgetPreference(opt.value)}
              >
                <Text style={[styles.budgetChipText, active && styles.budgetChipTextActive]}>{opt.label}</Text>
              </TouchableOpacity>
            );
          })}
        </View>

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
  safe: { flex: 1, backgroundColor: Colors.background },
  container: { flex: 1 },
  containerContent: { padding: Space.md, paddingBottom: Space.xl + Space.sm },
  appTitle: { ...Type.title, color: Colors.textPrimary, marginBottom: Space.xs / 2 },
  appSub: { ...Type.bodySmall, color: Colors.textMuted, marginBottom: Space.lg - 4 },
  sectionLabel: {
    ...Type.label, color: Colors.textMuted,
    marginBottom: Space.sm, marginTop: Space.sm,
  },
  budgetRow: { flexDirection: 'row', gap: Space.sm, marginTop: Space.sm + 2 },
  budgetChip: {
    paddingHorizontal: Space.sm + 2, paddingVertical: Space.xs + 2,
    borderRadius: Radius.md, borderWidth: 1, borderColor: Colors.border,
    backgroundColor: Palette.white,
  },
  budgetChipActive: { backgroundColor: Colors.primaryLight, borderColor: Colors.primary },
  budgetChipText: { ...Type.label, color: Colors.textSecondary },
  budgetChipTextActive: { color: Colors.primary, fontWeight: '500' },
  searchNote: {
    backgroundColor: Colors.surface, borderRadius: Radius.sm, padding: Space.sm + 2, marginTop: Space.sm + 2,
  },
  searchNoteText: { ...Type.label, color: Colors.textSecondary },
  suggestions: {
    borderWidth: 1, borderColor: Colors.border,
    borderRadius: Radius.md, overflow: 'hidden', marginTop: Space.sm + 4,
  },
  suggestion: {
    padding: Space.sm + 4, borderBottomWidth: 0.5, borderBottomColor: Colors.border,
  },
  suggestionText: { ...Type.bodySmall, color: Colors.textPrimary },
  errorBanner: { backgroundColor: RISK_COLORS['Very High'].bg, borderRadius: Radius.sm, padding: Space.sm + 2, marginTop: Space.sm + 4 },
  errorBannerText: { ...Type.label, color: RISK_COLORS['Very High'].text },
  coverageSection: { marginTop: Space.lg - 4 },
  coverageSummary: { ...Type.bodySmall, color: Colors.textSecondary, marginBottom: Space.sm + 4 },
  regionCard: {
    backgroundColor: Palette.white,
    borderWidth: 1, borderColor: Colors.border, borderRadius: Radius.md,
    padding: Space.sm + 4, marginBottom: Space.sm + 2,
  },
  regionCardHeader: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: Space.sm },
  regionCardHeaderText: { flex: 1 },
  regionName: { ...Type.heading, color: Colors.textPrimary },
  regionState: { ...Type.bodySmall, color: Colors.textSecondary, marginTop: 1 },
  zoneBadge: { borderRadius: Radius.sm, borderWidth: 1, paddingHorizontal: Space.sm, paddingVertical: 3 },
  zoneBadgeText: { ...Type.label, fontWeight: '500' },
  regionMetaRow: { flexDirection: 'row', alignItems: 'center', gap: Space.sm, marginTop: Space.sm },
  regionCount: { ...Type.label, color: Colors.textSecondary },
  pointsList: { marginTop: Space.sm, borderTopWidth: 0.5, borderTopColor: Colors.border, paddingTop: Space.sm, gap: 2 },
  noPointsText: { ...Type.label, color: Colors.textMuted, fontStyle: 'italic' },
  pointRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingVertical: Space.xs + 2,
  },
  pointName: { ...Type.bodySmall, color: Colors.primary, fontWeight: '500' },
  pointSpt: { ...Type.label, color: Colors.textMuted },
  viewMapBtn: { marginTop: Space.sm, alignSelf: 'flex-start' },
  viewMapBtnText: { ...Type.label, fontWeight: '500', color: Colors.primary },
  recentItem: {
    backgroundColor: Palette.white,
    borderWidth: 1, borderColor: Colors.border, borderRadius: Radius.md,
    padding: Space.sm + 4, marginBottom: Space.sm,
  },
  recentName: { ...Type.heading, color: Colors.textPrimary },
  recentSub: { ...Type.bodySmall, color: Colors.textSecondary, marginTop: 1 },
  emptyState: { alignItems: 'center', paddingHorizontal: Space.lg, paddingTop: Space.xl + Space.lg },
  emptyText: { ...Type.body, color: Colors.textSecondary, textAlign: 'center' },
});
