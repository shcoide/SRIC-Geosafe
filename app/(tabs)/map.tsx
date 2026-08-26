import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, Alert,
} from 'react-native';
import {
  MapView, Camera, ShapeSource, FillLayer, LineLayer, CircleLayer,
  RasterSource, RasterLayer, PointAnnotation, type CameraRef,
} from '@maplibre/maplibre-react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { useLocationStore } from '../../store/useLocationStore';
import { getCoverage, checkCoverage, analyzeLocation, describeApiError, SLOW_REQUEST_THRESHOLD_MS, isBackendWarmed } from '../../services/api';
import { reverseGeocode } from '../../services/location';
import { useSlowRequest } from '../../hooks/useSlowRequest';
import { CoverageBadge } from '../../components/CoverageBadge';
import { Colors } from '../../constants/colors';
import { SOURCE_COLORS } from '../../constants/riskConfig';
import { CoverageRegion, CoverageCheckResult } from '../../types';

const DEBOUNCE_MS = 300;

// MapTiler (free tier, account required, no billing) if a key is set;
// otherwise plain OpenStreetMap raster tiles, which need no signup at all —
// the zero-setup path for offline/CI use. See README ("Coverage Map Screen").
const MAPTILER_KEY = process.env.EXPO_PUBLIC_MAPTILER_KEY;
const TILE_URL_TEMPLATE = MAPTILER_KEY
  ? `https://api.maptiler.com/maps/streets-v2/{z}/{x}/{y}.png?key=${MAPTILER_KEY}`
  : 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';

// Empty base style — the actual basemap imagery comes from our own
// RasterSource/RasterLayer below, not a hosted MapLibre demo style, so this
// has no dependency on any third-party style server. Declared outside the
// component so it's a stable reference (avoids re-parsing the style natively
// on every render).
const EMPTY_STYLE = { version: 8 as const, sources: {}, layers: [] };

const INDIA_CENTER: [number, number] = [80, 22.5]; // MapLibre uses [lon, lat]
const INDIA_ZOOM = 4;

const hexToRgba = (hex: string, alpha: number): string => {
  const clean = hex.replace('#', '');
  const value = parseInt(clean, 16);
  const r = (value >> 16) & 255;
  const g = (value >> 8) & 255;
  const b = value & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

const INTERPOLATED_DOT = SOURCE_COLORS.interpolated.dot;
const MEASURED_DOT = SOURCE_COLORS.measured.dot;

const closeRing = (points: [number, number][]): [number, number][] =>
  points.length > 0 && points[0][0] === points[points.length - 1][0] && points[0][1] === points[points.length - 1][1]
    ? points
    : [...points, points[0]];

const regionsToFeatureCollection = (regionList: CoverageRegion[]): GeoJSON.FeatureCollection => ({
  type: 'FeatureCollection',
  features: regionList.map((region) => ({
    type: 'Feature',
    properties: { id: region.id },
    geometry: {
      type: 'Polygon',
      coordinates: [closeRing(region.boundary.map((p): [number, number] => [p.lon, p.lat]))],
    },
  })),
});

const pointsToFeatureCollection = (regionList: CoverageRegion[]): GeoJSON.FeatureCollection => ({
  type: 'FeatureCollection',
  features: regionList.flatMap((region) =>
    region.calibratedPoints.map((point) => ({
      type: 'Feature' as const,
      properties: { name: point.name },
      geometry: { type: 'Point' as const, coordinates: [point.lon, point.lat] },
    }))
  ),
});

export default function MapScreen() {
  const { setCurrentResult, addRecentSearch } = useLocationStore();
  const params = useLocalSearchParams<{ regionId?: string }>();
  const cameraRef = useRef<CameraRef>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [regions, setRegions] = useState<CoverageRegion[]>([]);
  const [regionsError, setRegionsError] = useState<string | null>(null);

  const [marker, setMarker] = useState<{ lat: number; lon: number } | null>(null);
  const [checkResult, setCheckResult] = useState<CoverageCheckResult | null>(null);
  const [checkLoading, setCheckLoading] = useState(false);
  const [checkError, setCheckError] = useState<string | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const analysisSlow = useSlowRequest(analysisLoading, SLOW_REQUEST_THRESHOLD_MS);
  // Snapshotted when handleRunFullAnalysis fires (not read live) — same
  // reasoning as components/LoadingOverlay.tsx: only the first request of
  // the session, made before the backend has proven itself awake, is
  // plausibly a Render cold start. A ref (not state) since it doesn't need
  // to trigger its own re-render — analysisSlow flipping true is what
  // does that, and this is just read alongside it at that point.
  const analysisWasLikelyColdStart = useRef(false);
  const [zoomLevel, setZoomLevel] = useState(INDIA_ZOOM);

  useEffect(() => {
    (async () => {
      try {
        setRegions(await getCoverage());
      } catch (e) {
        setRegionsError(describeApiError(e));
      }
    })();
  }, []);

  useEffect(() => () => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
  }, []);

  const runCoverageCheck = useCallback(async (lat: number, lon: number) => {
    setCheckLoading(true);
    setCheckError(null);
    try {
      setCheckResult(await checkCoverage(lat, lon));
    } catch (e) {
      setCheckError(describeApiError(e));
    } finally {
      setCheckLoading(false);
    }
  }, []);

  const debouncedCheck = useCallback((lat: number, lon: number) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runCoverageCheck(lat, lon), DEBOUNCE_MS);
  }, [runCoverageCheck]);

  const handleMapPress = useCallback((feature: GeoJSON.Feature) => {
    if (feature.geometry.type !== 'Point') return;
    const [lon, lat] = feature.geometry.coordinates;
    setMarker({ lat, lon });
    runCoverageCheck(lat, lon);
  }, [runCoverageCheck]);

  const handleMarkerDragEnd = useCallback((feature: GeoJSON.Feature) => {
    if (feature.geometry.type !== 'Point') return;
    const [lon, lat] = feature.geometry.coordinates;
    setMarker({ lat, lon });
    debouncedCheck(lat, lon);
  }, [debouncedCheck]);

  const panToRegion = (region: CoverageRegion) => {
    cameraRef.current?.fitBounds(
      [region.bounds.east, region.bounds.north],
      [region.bounds.west, region.bounds.south],
      40,
      500
    );
  };

  // Focuses the region passed via router params (e.g. "View on map" on the
  // home screen's region cards). Re-runs whenever the param or the fetched
  // region list changes, so it works whether this tab was already mounted
  // (tab switches don't remount by default) or just mounted for the first time.
  useEffect(() => {
    if (params.regionId && regions.length > 0) {
      const found = regions.find((r) => r.id === params.regionId);
      if (found) panToRegion(found);
    }
  }, [params.regionId, regions]);

  const handleZoomBy = (delta: number) => {
    cameraRef.current?.zoomTo(zoomLevel + delta, 200);
  };

  const handlePanToNearest = () => {
    const nearest = checkResult?.nearestRegion;
    if (!nearest) return;
    const found = regions.find((r) => r.id === nearest.id);
    if (found) {
      panToRegion(found);
    } else {
      cameraRef.current?.setCamera({
        centerCoordinate: [nearest.center.lon, nearest.center.lat],
        zoomLevel: 9,
        animationDuration: 500,
      });
    }
  };

  const handleRunFullAnalysis = useCallback(async () => {
    if (!marker) return;
    analysisWasLikelyColdStart.current = !isBackendWarmed();
    setAnalysisLoading(true);
    try {
      const name = await reverseGeocode(marker.lat, marker.lon);
      const result = await analyzeLocation({ lat: marker.lat, lon: marker.lon, locationName: name });
      setCurrentResult(result);
      addRecentSearch({ name, displayName: name, lat: marker.lat, lon: marker.lon });
      router.push(`/results/${result.locationId}`);
    } catch (e) {
      Alert.alert('Error', describeApiError(e));
    } finally {
      setAnalysisLoading(false);
    }
  }, [marker]);

  const provisionalRegions = regions.filter((r) => r.geometrySource !== 'survey_hull');
  const surveyRegions = regions.filter((r) => r.geometrySource === 'survey_hull');
  const markerDotColor = checkResult ? SOURCE_COLORS[checkResult.expectedVs30Source].dot : Colors.primary;

  return (
    <View style={styles.container}>
      {regions.length > 0 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipRow} contentContainerStyle={styles.chipRowContent}>
          {regions.map((region) => (
            <TouchableOpacity key={region.id} style={styles.chip} onPress={() => panToRegion(region)}>
              <Text style={styles.chipText}>{region.name}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}

      {regionsError && (
        <View style={styles.errorBanner}>
          <Text style={styles.errorBannerText}>Coverage data unavailable: {regionsError}</Text>
        </View>
      )}

      <View style={styles.mapWrapper}>
        <MapView
          style={styles.map}
          mapStyle={EMPTY_STYLE}
          onPress={handleMapPress}
          onRegionDidChange={(feature) => setZoomLevel(feature.properties.zoomLevel)}
        >
          <Camera ref={cameraRef} defaultSettings={{ centerCoordinate: INDIA_CENTER, zoomLevel: INDIA_ZOOM }} />

          <RasterSource id="basemap" tileUrlTemplates={[TILE_URL_TEMPLATE]} tileSize={256}>
            <RasterLayer id="basemap-layer" />
          </RasterSource>

          {provisionalRegions.length > 0 && (
            <ShapeSource id="regions-provisional" shape={regionsToFeatureCollection(provisionalRegions)}>
              <FillLayer id="regions-provisional-fill" style={{ fillColor: hexToRgba(INTERPOLATED_DOT, 0.08) }} />
              {/* Dashed = a declared rectangle, not yet derived from survey
                  data (see geometrySource in data/site_calibration.py). */}
              <LineLayer
                id="regions-provisional-line"
                style={{ lineColor: hexToRgba(INTERPOLATED_DOT, 0.6), lineWidth: 2, lineDasharray: [8, 8] }}
              />
            </ShapeSource>
          )}
          {surveyRegions.length > 0 && (
            <ShapeSource id="regions-survey" shape={regionsToFeatureCollection(surveyRegions)}>
              <FillLayer id="regions-survey-fill" style={{ fillColor: hexToRgba(INTERPOLATED_DOT, 0.08) }} />
              {/* Solid = a real survey-derived boundary. */}
              <LineLayer
                id="regions-survey-line"
                style={{ lineColor: hexToRgba(INTERPOLATED_DOT, 0.6), lineWidth: 2 }}
              />
            </ShapeSource>
          )}

          {regions.some((r) => r.calibratedPoints.length > 0) && (
            <ShapeSource id="calibrated-points" shape={pointsToFeatureCollection(regions)}>
              {/* MapLibre's circleRadius is in screen pixels, not metres — a
                  true-to-scale circle needs custom per-zoom math, so this uses
                  a fixed pixel radius rather than point.radiusKm. */}
              <CircleLayer
                id="calibrated-points-circle"
                style={{
                  circleRadius: 20,
                  circleColor: hexToRgba(MEASURED_DOT, 0.35),
                  circleStrokeColor: hexToRgba(MEASURED_DOT, 0.9),
                  circleStrokeWidth: 2,
                }}
              />
            </ShapeSource>
          )}

          {marker && (
            <PointAnnotation
              id="check-marker"
              coordinate={[marker.lon, marker.lat]}
              draggable
              onDragEnd={handleMarkerDragEnd}
            >
              <View style={[styles.markerDot, { backgroundColor: markerDotColor }]} />
            </PointAnnotation>
          )}
        </MapView>

        <View style={styles.zoomControls}>
          <TouchableOpacity style={styles.zoomBtn} onPress={() => handleZoomBy(1)}>
            <Text style={styles.zoomBtnText}>+</Text>
          </TouchableOpacity>
          <View style={styles.zoomBtnDivider} />
          <TouchableOpacity style={styles.zoomBtn} onPress={() => handleZoomBy(-1)}>
            <Text style={styles.zoomBtnText}>−</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.legend}>
          <View style={styles.legendRow}>
            <View style={[styles.legendSwatch, styles.legendSwatchDashed, { borderColor: hexToRgba(INTERPOLATED_DOT, 0.8), backgroundColor: hexToRgba(INTERPOLATED_DOT, 0.1) }]} />
            <Text style={styles.legendText}>Region — provisional rectangle</Text>
          </View>
          <View style={styles.legendRow}>
            <View style={[styles.legendSwatch, { borderColor: hexToRgba(INTERPOLATED_DOT, 0.8), backgroundColor: hexToRgba(INTERPOLATED_DOT, 0.1) }]} />
            <Text style={styles.legendText}>Region — real survey boundary</Text>
          </View>
          <View style={styles.legendRow}>
            <View style={[styles.legendSwatch, { borderColor: hexToRgba(MEASURED_DOT, 0.9), backgroundColor: hexToRgba(MEASURED_DOT, 0.4) }]} />
            <Text style={styles.legendText}>Calibrated point (measured)</Text>
          </View>
          <Text style={styles.attribution}>© OpenStreetMap contributors</Text>
        </View>

        {!marker && (
          <View style={styles.hint}>
            <Text style={styles.hintText}>Tap anywhere in India to check data coverage for that point</Text>
          </View>
        )}

        {marker && (
          <View style={styles.sheet}>
            <View style={styles.sheetCoordsRow}>
              <Text style={styles.sheetCoords}>
                {marker.lat.toFixed(4)}°N · {marker.lon.toFixed(4)}°E
              </Text>
              {checkLoading && <ActivityIndicator size="small" color={Colors.primary} />}
            </View>

            {checkLoading && !checkResult && (
              <View style={styles.sheetLoading}>
                <Text style={styles.sheetLoadingText}>Checking coverage…</Text>
              </View>
            )}

            {checkError && <Text style={styles.sheetError}>{checkError}</Text>}

            {checkResult && (
              <View style={{ opacity: checkLoading ? 0.5 : 1, gap: 8 }}>
                {checkResult.regionName && (
                  <Text style={styles.sheetRegion}>Region: {checkResult.regionName}</Text>
                )}

                <CoverageBadge source={checkResult.expectedVs30Source} />

                {!checkResult.inCoverage && (
                  <View style={styles.outsideNotice}>
                    <Text style={styles.outsideNoticeText}>
                      Outside calibrated coverage — results will use regional estimates
                    </Text>
                    {checkResult.nearestRegion && (
                      <View style={styles.nearestRow}>
                        <Text style={styles.nearestText}>
                          Nearest coverage: {checkResult.nearestRegion.name} ({checkResult.nearestRegion.distanceKm.toFixed(0)} km away)
                        </Text>
                        <TouchableOpacity style={styles.panBtn} onPress={handlePanToNearest}>
                          <Text style={styles.panBtnText}>Pan there</Text>
                        </TouchableOpacity>
                      </View>
                    )}
                  </View>
                )}

                <TouchableOpacity
                  style={[styles.analyzeBtn, analysisLoading && styles.analyzeBtnDisabled]}
                  onPress={handleRunFullAnalysis}
                  disabled={analysisLoading}
                >
                  {analysisLoading ? (
                    <ActivityIndicator size="small" color="#fff" />
                  ) : (
                    <Text style={styles.analyzeBtnText}>
                      {checkResult.inCoverage ? 'Run full analysis' : 'Run full analysis (lower confidence)'}
                    </Text>
                  )}
                </TouchableOpacity>

                {analysisLoading && analysisSlow && analysisWasLikelyColdStart.current && (
                  <Text style={styles.slowNotice}>
                    Waking up the server — first request after a while can take up to a minute…
                  </Text>
                )}
              </View>
            )}
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  chipRow: { maxHeight: 44, borderBottomWidth: 0.5, borderBottomColor: Colors.surface.border },
  chipRowContent: { paddingHorizontal: 12, paddingVertical: 8, gap: 8 },
  chip: {
    borderWidth: 0.5, borderColor: Colors.primaryBorder, backgroundColor: Colors.primaryLight,
    borderRadius: 16, paddingHorizontal: 12, paddingVertical: 6,
  },
  chipText: { fontSize: 12, fontWeight: '500', color: Colors.primary },
  errorBanner: { backgroundColor: '#FCEBEB', padding: 8, paddingHorizontal: 12 },
  errorBannerText: { fontSize: 11, color: '#791F1F' },
  mapWrapper: { flex: 1 },
  map: { flex: 1 },
  markerDot: {
    width: 22, height: 22, borderRadius: 11,
    borderWidth: 3, borderColor: '#fff',
    shadowColor: '#000', shadowOpacity: 0.3, shadowRadius: 3, shadowOffset: { width: 0, height: 1 },
    elevation: 4,
  },
  zoomControls: {
    position: 'absolute', top: 12, left: 12,
    backgroundColor: 'rgba(255,255,255,0.95)', borderRadius: 8,
    borderWidth: 0.5, borderColor: Colors.surface.border,
    overflow: 'hidden',
  },
  zoomBtn: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center' },
  zoomBtnText: { fontSize: 18, fontWeight: '600', color: Colors.text.primary },
  zoomBtnDivider: { height: 0.5, backgroundColor: Colors.surface.border },
  legend: {
    position: 'absolute', top: 12, right: 12,
    backgroundColor: 'rgba(255,255,255,0.95)', borderRadius: 8, padding: 8,
    borderWidth: 0.5, borderColor: Colors.surface.border, gap: 4,
  },
  legendRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  legendSwatch: { width: 14, height: 14, borderRadius: 4, borderWidth: 1.5 },
  legendSwatchDashed: { borderStyle: 'dashed' },
  legendText: { fontSize: 10, color: Colors.text.secondary },
  attribution: { fontSize: 9, color: Colors.text.muted, marginTop: 4 },
  hint: {
    position: 'absolute', bottom: 30, left: 20, right: 20,
    backgroundColor: '#fff', borderRadius: 10, padding: 14,
    borderWidth: 0.5, borderColor: Colors.surface.border,
    alignItems: 'center',
  },
  hintText: { fontSize: 13, color: Colors.text.secondary },
  sheet: {
    position: 'absolute', bottom: 0, left: 0, right: 0,
    backgroundColor: '#fff', borderTopLeftRadius: 16, borderTopRightRadius: 16,
    borderWidth: 0.5, borderColor: Colors.surface.border,
    padding: 16, gap: 8,
    shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 8, shadowOffset: { width: 0, height: -2 },
    elevation: 8,
  },
  sheetCoordsRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  sheetCoords: { fontSize: 13, fontWeight: '500', color: Colors.text.primary },
  sheetLoading: { paddingVertical: 4 },
  sheetLoadingText: { fontSize: 12, color: Colors.text.secondary },
  sheetError: { fontSize: 12, color: '#A32D2D' },
  sheetRegion: { fontSize: 12, color: Colors.text.secondary },
  outsideNotice: {
    backgroundColor: Colors.surface.secondary, borderRadius: 8, padding: 10, gap: 6,
  },
  outsideNoticeText: { fontSize: 11, color: Colors.text.secondary, lineHeight: 16 },
  nearestRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 },
  nearestText: { fontSize: 11, color: Colors.text.secondary, flex: 1 },
  panBtn: { borderWidth: 0.5, borderColor: Colors.primaryBorder, borderRadius: 6, paddingHorizontal: 10, paddingVertical: 5 },
  panBtnText: { fontSize: 11, fontWeight: '500', color: Colors.primary },
  analyzeBtn: {
    backgroundColor: Colors.primary, borderRadius: 10, paddingVertical: 13,
    alignItems: 'center', marginTop: 4,
  },
  analyzeBtnDisabled: { opacity: 0.6 },
  analyzeBtnText: { fontSize: 14, fontWeight: '500', color: '#fff' },
  slowNotice: { fontSize: 11, color: Colors.text.secondary, textAlign: 'center', marginTop: 6 },
});
