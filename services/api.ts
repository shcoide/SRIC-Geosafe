import axios from 'axios';
import Constants from 'expo-constants';
import { LocationResult } from '../types';

// In Expo Go / dev builds, derive the backend host from the same LAN address
// Metro is already reachable on, instead of a hardcoded IP that goes stale
// whenever the machine's Wi-Fi IP changes.
const getDevBaseUrl = () => {
  const hostUri = Constants.expoConfig?.hostUri ?? Constants.expoGoConfig?.debuggerHost;
  const host = hostUri?.split(':')[0];
  return `http://${host || 'localhost'}:8000/api`;
};

const BASE_URL = __DEV__
  ? getDevBaseUrl()
  : process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000/api';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

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
