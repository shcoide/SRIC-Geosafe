import * as Location from 'expo-location';
import { Coordinates } from '../types';

export const requestLocationPermission = async (): Promise<boolean> => {
  const { status } = await Location.requestForegroundPermissionsAsync();
  return status === 'granted';
};

export const getCurrentCoordinates = async (): Promise<Coordinates> => {
  const hasPermission = await requestLocationPermission();
  if (!hasPermission) throw new Error('Location permission denied');

  const location = await Location.getCurrentPositionAsync({
    accuracy: Location.Accuracy.Balanced,
  });

  return {
    lat: location.coords.latitude,
    lon: location.coords.longitude,
  };
};

export const reverseGeocode = async (lat: number, lon: number): Promise<string> => {
  try {
    const results = await Location.reverseGeocodeAsync({ latitude: lat, longitude: lon });
    if (results.length > 0) {
      const r = results[0];
      return [r.city, r.region, r.country].filter(Boolean).join(', ');
    }
    return `${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E`;
  } catch {
    return `${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E`;
  }
};
