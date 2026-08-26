import { Colors } from './colors';
import { SiteDataSource } from '../types';

export const RISK_COLORS = {
  'Low': Colors.risk.low,
  'Moderate': Colors.risk.moderate,
  'High': Colors.risk.high,
  'Very High': Colors.risk.veryHigh,
};

// Provenance tiers, in decreasing order of confidence. Reuses the same
// colour objects as RISK_COLORS (green -> red) so "assumed" reads the same
// way "Very High risk" does elsewhere in the app, instead of introducing an
// unrelated palette just for data-source confidence.
export const SOURCE_COLORS: Record<SiteDataSource, typeof Colors.risk.low> = {
  measured: Colors.risk.low,
  interpolated: Colors.risk.moderate,
  modeled: Colors.risk.high,
  assumed: Colors.risk.veryHigh,
};

export const SOURCE_LABELS: Record<SiteDataSource, string> = {
  measured: 'Measured — calibrated survey point',
  interpolated: 'Interpolated — city-scale estimate',
  modeled: 'Modeled — global raster',
  assumed: 'Assumed — regional default',
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
