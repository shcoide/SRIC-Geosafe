import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, Alert,
} from 'react-native';
import { WebView, type WebViewMessageEvent } from 'react-native-webview';
import { router, useLocalSearchParams } from 'expo-router';
import { useLocationStore } from '../../store/useLocationStore';
import { getCoverage, checkCoverage, analyzeLocation, describeApiError, SLOW_REQUEST_THRESHOLD_MS, isBackendWarmed } from '../../services/api';
import { reverseGeocode } from '../../services/location';
import { useSlowRequest } from '../../hooks/useSlowRequest';
import { CoverageBadge } from '../../components/CoverageBadge';
import { Colors, Palette } from '../../constants/colors';
import { Type } from '../../constants/typography';
import { Space, Radius } from '../../constants/spacing';
import { SOURCE_COLORS, RISK_COLORS } from '../../constants/riskConfig';
import { CoverageRegion, CoverageCheckResult } from '../../types';

const DEBOUNCE_MS = 300;

const INDIA_CENTER: [number, number] = [22.5, 80]; // Leaflet uses [lat, lon]
const INDIA_ZOOM = 4;

const hexToRgba = (hex: string, alpha: number): string => {
  const clean = hex.replace('#', '');
  const value = parseInt(clean, 16);
  const r = (value >> 16) & 255;
  const g = (value >> 8) & 255;
  const b = value & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

// Reused as-is from the MapLibre implementation these replace — both are the
// app's existing source-confidence color tokens (constants/riskConfig.ts),
// not literally "blue"/"teal": interpolated is an amber/gold tone, measured
// is green. Kept for consistency with the same provenance-color language
// used everywhere else in the app (CoverageBadge, the map legend below),
// rather than introducing new one-off colors just for this map.
const INTERPOLATED_DOT = SOURCE_COLORS.interpolated.dot;
const MEASURED_DOT = SOURCE_COLORS.measured.dot;

// Builds the self-contained Leaflet page. Loads Leaflet itself from its
// official CDN (unpkg) rather than bundling the library's JS/CSS into this
// template literal — "self-contained" here means no separate .html asset
// file in the project (the whole point of this migration is dropping a
// large *native* dependency; pulling ~40KB gzipped of Leaflet from a CDN at
// runtime, the same way the map tiles themselves are already fetched, costs
// nothing in APK size). Region/point geometry is baked into the page at
// generation time (via JSON.stringify below) rather than injected after
// load, so there's no load-order race to coordinate for the initial data.
const buildLeafletHtml = (regions: CoverageRegion[]): string => {
  const provisional = regions.filter((r) => r.geometrySource !== 'survey_hull');
  const survey = regions.filter((r) => r.geometrySource === 'survey_hull');

  // Leaflet coordinates are [lat, lon] — the opposite order from the
  // GeoJSON [lon, lat] pairs the old MapLibre implementation used.
  const provisionalPolygons = provisional.map((r) => r.boundary.map((p) => [p.lat, p.lon]));
  const surveyPolygons = survey.map((r) => r.boundary.map((p) => [p.lat, p.lon]));
  const points = regions.flatMap((r) => r.calibratedPoints.map((p) => [p.lat, p.lon, p.radiusKm]));

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    html, body, #map { height: 100%; margin: 0; padding: 0; }
    .leaflet-control-attribution { font-size: 10px; }
  </style>
</head>
<body>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    var map = L.map('map').setView([${INDIA_CENTER[0]}, ${INDIA_CENTER[1]}], ${INDIA_ZOOM});

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(map);

    var provisionalPolygons = ${JSON.stringify(provisionalPolygons)};
    var surveyPolygons = ${JSON.stringify(surveyPolygons)};
    var points = ${JSON.stringify(points)};

    // Dashed = a declared rectangle, not yet derived from survey data (see
    // geometrySource in backend/data/site_calibration.py).
    provisionalPolygons.forEach(function (coords) {
      L.polygon(coords, {
        color: '${INTERPOLATED_DOT}', weight: 2, opacity: 0.6,
        fillOpacity: 0.08, dashArray: '8, 8',
      }).addTo(map);
    });
    // Solid = a real survey-derived boundary.
    surveyPolygons.forEach(function (coords) {
      L.polygon(coords, {
        color: '${INTERPOLATED_DOT}', weight: 2, opacity: 0.6, fillOpacity: 0.08,
      }).addTo(map);
    });

    // L.circle()'s radius is real metres on the ground, unlike MapLibre's
    // circleRadius (screen pixels) — this is a genuine improvement, not a
    // workaround: these circles now show each point's true ~2km calibration
    // catchment instead of an arbitrary decorative dot size.
    points.forEach(function (p) {
      L.circle([p[0], p[1]], {
        radius: p[2] * 1000,
        color: '${MEASURED_DOT}', weight: 1.5, opacity: 1,
        fillColor: '${MEASURED_DOT}', fillOpacity: 0.35,
      }).addTo(map);
    });

    var marker = null;

    function markerIcon(color) {
      return L.divIcon({
        className: '',
        html: '<div style="width:22px;height:22px;border-radius:11px;background:' + color +
          ';border:3px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,0.3);"></div>',
        iconSize: [22, 22],
        iconAnchor: [11, 11],
      });
    }

    function post(payload) {
      window.ReactNativeWebView.postMessage(JSON.stringify(payload));
    }

    map.on('click', function (e) {
      var lat = e.latlng.lat, lon = e.latlng.lng;
      if (marker) { map.removeLayer(marker); }
      marker = L.marker([lat, lon], { draggable: true, icon: markerIcon('${Colors.primary}') }).addTo(map);
      marker.on('dragend', function () {
        var pos = marker.getLatLng();
        post({ type: 'markerMoved', lat: pos.lat, lon: pos.lng });
      });
      post({ type: 'mapTapped', lat: lat, lon: lon });
    });
  </script>
</body>
</html>`;
};

export default function MapScreen() {
  const { setCurrentResult, addRecentSearch } = useLocationStore();
  const params = useLocalSearchParams<{ regionId?: string }>();
  const webViewRef = useRef<WebView>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [regions, setRegions] = useState<CoverageRegion[]>([]);
  const [regionsError, setRegionsError] = useState<string | null>(null);
  const [mapReady, setMapReady] = useState(false);

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

  // Regenerated only when the fetched region list changes (once, after the
  // initial GET /api/coverage resolves) — the WebView reloads when its
  // source.html changes, so mapReady is reset until the new page's onLoad
  // fires again.
  const leafletHtml = useMemo(() => buildLeafletHtml(regions), [regions]);
  useEffect(() => setMapReady(false), [leafletHtml]);

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

  const handleWebViewMessage = useCallback((event: WebViewMessageEvent) => {
    let data: { type: string; lat: number; lon: number };
    try {
      data = JSON.parse(event.nativeEvent.data);
    } catch {
      return;
    }
    if (data.type === 'mapTapped') {
      setMarker({ lat: data.lat, lon: data.lon });
      runCoverageCheck(data.lat, data.lon);
    } else if (data.type === 'markerMoved') {
      setMarker({ lat: data.lat, lon: data.lon });
      debouncedCheck(data.lat, data.lon);
    }
  }, [runCoverageCheck, debouncedCheck]);

  // `map` is a global in the WebView's page script (declared at the top
  // level in buildLeafletHtml above), so injected script can call it
  // directly — no round-trip wrapper function needed.
  const flyTo = useCallback((lat: number, lon: number, zoom = 12) => {
    webViewRef.current?.injectJavaScript(`map.flyTo([${lat}, ${lon}], ${zoom}); true;`);
  }, []);

  const panToRegion = useCallback((region: CoverageRegion) => {
    flyTo(region.center.lat, region.center.lon);
  }, [flyTo]);

  // Focuses the region passed via router params (e.g. "View on map" on the
  // home screen's region cards). Re-runs whenever the param, the fetched
  // region list, or map readiness changes, so it works whether this tab was
  // already mounted, just mounted, or the WebView was still loading Leaflet
  // when the param first arrived.
  useEffect(() => {
    if (mapReady && params.regionId && regions.length > 0) {
      const found = regions.find((r) => r.id === params.regionId);
      if (found) panToRegion(found);
    }
  }, [mapReady, params.regionId, regions, panToRegion]);

  const handlePanToNearest = () => {
    const nearest = checkResult?.nearestRegion;
    if (!nearest) return;
    flyTo(nearest.center.lat, nearest.center.lon);
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

  const markerDotColor = checkResult ? SOURCE_COLORS[checkResult.expectedVs30Source].dot : Colors.primary;

  // Keeps the in-page marker's color in sync with the async coverage-check
  // result (starts as Colors.primary at drop time, then updates once
  // checkResult resolves) — mirrors what the old PointAnnotation's
  // `backgroundColor` did reactively for free; here it's an explicit inject
  // since the marker lives inside the WebView's own JS context.
  useEffect(() => {
    if (marker && mapReady) {
      webViewRef.current?.injectJavaScript(
        `if (typeof marker !== 'undefined' && marker) { marker.setIcon(markerIcon('${markerDotColor}')); } true;`
      );
    }
  }, [markerDotColor, marker, mapReady]);

  const showHint = !marker;

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
        <WebView
          ref={webViewRef}
          style={styles.map}
          originWhitelist={['*']}
          source={{ html: leafletHtml }}
          onLoad={() => setMapReady(true)}
          onMessage={handleWebViewMessage}
        />

        {/* Swatch colours below reuse INTERPOLATED_DOT/MEASURED_DOT —
            semantic map overlay colours, deliberately left unchanged (see
            constants/riskConfig.ts). */}
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
            <Text style={styles.legendText}>Calibrated survey point</Text>
          </View>
          <Text style={styles.attribution}>© OpenStreetMap contributors</Text>
        </View>

        {showHint && (
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
                    <ActivityIndicator size="small" color={Palette.white} />
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
  container: { flex: 1, backgroundColor: Colors.background },
  chipRow: { maxHeight: 44, borderBottomWidth: 1, borderBottomColor: Colors.border },
  chipRowContent: { paddingHorizontal: Space.sm + 4, paddingVertical: Space.sm, gap: Space.sm },
  chip: {
    borderWidth: 1, borderColor: Colors.primaryBorder, backgroundColor: Colors.primaryLight,
    borderRadius: Radius.md, paddingHorizontal: Space.sm + 4, paddingVertical: Space.xs + 2,
  },
  chipText: { ...Type.bodySmall, fontWeight: '500', color: Colors.primary },
  errorBanner: { backgroundColor: RISK_COLORS['Very High'].bg, padding: Space.sm, paddingHorizontal: Space.sm + 4 },
  errorBannerText: { ...Type.label, color: RISK_COLORS['Very High'].text },
  mapWrapper: { flex: 1 },
  map: { flex: 1 },
  legend: {
    position: 'absolute', top: Space.sm + 4, right: Space.sm + 4,
    backgroundColor: 'rgba(255,255,255,0.95)', borderRadius: Radius.md, padding: Space.sm,
    borderWidth: 1, borderColor: Colors.border, gap: Space.xs,
  },
  legendRow: { flexDirection: 'row', alignItems: 'center', gap: Space.xs + 2 },
  legendSwatch: { width: 14, height: 14, borderRadius: Radius.sm, borderWidth: 1.5 },
  legendSwatchDashed: { borderStyle: 'dashed' },
  legendText: { ...Type.label, color: Colors.textSecondary },
  attribution: { ...Type.label, color: Colors.textMuted, marginTop: Space.xs },
  hint: {
    position: 'absolute', bottom: 30, left: Space.lg - 4, right: Space.lg - 4,
    backgroundColor: Palette.white, borderRadius: Radius.lg, padding: Space.md - 2,
    borderWidth: 1, borderColor: Colors.border,
    alignItems: 'center',
  },
  hintText: { ...Type.bodySmall, color: Colors.textSecondary },
  sheet: {
    position: 'absolute', bottom: 0, left: 0, right: 0,
    // Capped so the map above it stays fully visible and pannable — this
    // sheet must never grow to cover most of the screen.
    maxHeight: '40%',
    backgroundColor: Palette.white, borderTopLeftRadius: Radius.lg, borderTopRightRadius: Radius.lg,
    borderWidth: 1, borderColor: Colors.border,
    padding: Space.md, gap: Space.sm,
    shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 8, shadowOffset: { width: 0, height: -2 },
    elevation: 8,
  },
  sheetCoordsRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  sheetCoords: { ...Type.mono, fontWeight: '500', color: Colors.textPrimary },
  sheetLoading: { paddingVertical: Space.xs },
  sheetLoadingText: { ...Type.bodySmall, color: Colors.textSecondary },
  sheetError: { ...Type.bodySmall, color: RISK_COLORS['Very High'].text },
  sheetRegion: { ...Type.bodySmall, color: Colors.textSecondary },
  outsideNotice: {
    backgroundColor: Colors.surface, borderRadius: Radius.sm, padding: Space.sm + 2, gap: Space.xs + 2,
  },
  outsideNoticeText: { ...Type.label, color: Colors.textSecondary },
  nearestRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: Space.sm },
  nearestText: { ...Type.label, color: Colors.textSecondary, flex: 1 },
  panBtn: { borderWidth: 1, borderColor: Colors.primaryBorder, borderRadius: Radius.md, paddingHorizontal: Space.sm + 2, paddingVertical: Space.xs + 1 },
  panBtnText: { ...Type.label, fontWeight: '500', color: Colors.primary },
  analyzeBtn: {
    backgroundColor: Colors.primary, borderRadius: Radius.md, paddingVertical: Space.md - 3,
    alignItems: 'center', marginTop: Space.xs,
  },
  analyzeBtnDisabled: { opacity: 0.6 },
  analyzeBtnText: { ...Type.body, fontWeight: '500', color: Palette.white },
  slowNotice: { ...Type.label, color: Colors.textSecondary, textAlign: 'center', marginTop: Space.xs + 2 },
});
