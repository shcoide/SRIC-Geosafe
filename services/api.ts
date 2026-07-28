import axios from 'axios';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import { LocationResult } from '../types';

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
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

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

export const analyzeLocation = async (params: AnalyzeParams): Promise<LocationResult> => {
  const response = await apiClient.post('/analyze', {
    lat: params.lat,
    lon: params.lon,
    location_name: params.locationName,
    floors: params.floors || 3,
    building_type: params.buildingType || 'residential',
  });
  return response.data;
};
