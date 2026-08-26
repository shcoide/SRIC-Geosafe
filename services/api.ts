import axios from 'axios';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import { LocationResult, CoverageRegion, CoverageCheckResult } from '../types';

const DEFAULT_PORT = 8000;

/**
 * Resolution order:
 *   a) EXPO_PUBLIC_API_URL, if set — explicit override always wins
 *   b) In __DEV__, a real LAN host from Constants.expoConfig.hostUri — covers
 *      physical devices on the same Wi-Fi, and survives the Mac's LAN IP changing
 *   c) In __DEV__ otherwise, the platform-specific loopback: Android's emulated
 *      network stack maps the host machine to 10.0.2.2, not localhost
 *   d) Final fallback: http://localhost:8000/api
 */
const resolveBaseUrl = (): string => {
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL;
  }

  if (__DEV__) {
    const hostUri = Constants.expoConfig?.hostUri ?? Constants.expoGoConfig?.debuggerHost;
    const lanHost = hostUri?.split(':')[0];
    if (lanHost && lanHost !== 'localhost' && lanHost !== '127.0.0.1') {
      return `http://${lanHost}:${DEFAULT_PORT}/api`;
    }

    return Platform.OS === 'android'
      ? `http://10.0.2.2:${DEFAULT_PORT}/api`
      : `http://localhost:${DEFAULT_PORT}/api`;
  }

  return `http://localhost:${DEFAULT_PORT}/api`;
};

export const BASE_URL = resolveBaseUrl();

if (__DEV__) {
  console.log(`[api] Using backend base URL: ${BASE_URL}`);
}

export const apiClient = axios.create({
  baseURL: BASE_URL,
  // Render's free tier spins the backend down after inactivity, so the
  // first request after a lull pays for a cold start (can take 30-50s)
  // before /analyze even starts working. 60s gives that a real chance to
  // finish instead of timing out mid-boot. This is independent of the
  // USGS lookup's own short timeout inside /analyze (see
  // backend/services/usgs.py) — a slow USGS response can never be why
  // this outer timeout is hit.
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
});

// After this long with no response, the UI should stop showing a generic
// spinner and tell the user the backend may be waking up from a Render
// cold start, rather than leaving them guessing why nothing is happening.
export const SLOW_REQUEST_THRESHOLD_MS = 5000;

// Whether the backend has answered at least once this app session — set
// permanently by the response interceptor below the first time any
// request gets a real response, success or error status (a 4xx/5xx still
// means the server is awake; only a response-less failure doesn't count).
// Never reset short of an app restart.
//
// The "waking up the server" messaging (components/LoadingOverlay.tsx,
// app/(tabs)/map.tsx) reads this to decide whether a slow request is
// plausibly a cold start. It should only ever say so once: after the
// backend has proven it's awake, a later slow request is real latency
// (a big query, a bad network), not a boot, and repeating the cold-start
// message would just be wrong.
let backendWarmed = false;

export const isBackendWarmed = (): boolean => backendWarmed;

apiClient.interceptors.response.use(
  (response) => {
    backendWarmed = true;
    return response;
  },
  (error) => {
    if (axios.isAxiosError(error) && error.response) {
      backendWarmed = true;
    }
    return Promise.reject(error);
  }
);

/**
 * Axios' "Network Error" on its own isn't actionable — it means the request
 * never reached the backend at all (wrong host, backend not running, or
 * backend bound to 127.0.0.1 instead of 0.0.0.0). Turn that into a message
 * that names the address actually in use and how to fix it.
 */
export const describeApiError = (error: unknown): string => {
  if (axios.isAxiosError(error) && !error.response) {
    return `Could not reach the backend at ${BASE_URL}. Make sure it's running with:\nuvicorn main:app --reload --port 8000 --host 0.0.0.0`;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return 'Could not analyse this location.';
};

export interface AnalyzeParams {
  lat: number;
  lon: number;
  locationName: string;
  floors?: number;
  buildingType?: string;
}

// The most recent analyzeLocation() call's params, kept purely for crash
// diagnostics. If the app crashes shortly after a search, ErrorBoundary
// includes this in its log line so a remote "it crashed" report is
// debuggable without asking the user what they were doing or reproducing
// it locally. Never used for anything functional — see
// components/ErrorBoundary.tsx.
let lastAnalyzeRequest: AnalyzeParams | null = null;

export const getLastAnalyzeRequest = (): AnalyzeParams | null => lastAnalyzeRequest;

export const analyzeLocation = async (params: AnalyzeParams): Promise<LocationResult> => {
  lastAnalyzeRequest = params;
  const response = await apiClient.post('/analyze', {
    lat: params.lat,
    lon: params.lon,
    location_name: params.locationName,
    floors: params.floors || 3,
    building_type: params.buildingType || 'residential',
  });
  return response.data;
};

export const getCoverage = async (): Promise<CoverageRegion[]> => {
  const response = await apiClient.get('/coverage');
  return response.data;
};

export const checkCoverage = async (lat: number, lon: number): Promise<CoverageCheckResult> => {
  const response = await apiClient.get('/coverage/check', { params: { lat, lon } });
  return response.data;
};
