import { Colors } from './colors';

export const RISK_COLORS = {
  'Low': Colors.risk.low,
  'Moderate': Colors.risk.moderate,
  'High': Colors.risk.high,
  'Very High': Colors.risk.veryHigh,
};

export const ZONE_LABELS: Record<string, string> = {
  II: 'Low seismic activity',
  III: 'Moderate seismic activity',
  IV: 'High seismic activity',
  V: 'Very high seismic activity',
};

export const ZONE_RISK: Record<string, string> = {
  II: 'Low',
  III: 'Moderate',
  IV: 'High',
  V: 'Very High',
};

export const HAZARD_ICONS: Record<string, string> = {
  earthquake: 'alert-circle',
  flood: 'water',
  landslide: 'terrain',
  cyclone: 'weather-windy',
};
