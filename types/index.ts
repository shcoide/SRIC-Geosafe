export interface Coordinates {
  lat: number;
  lon: number;
}

export interface LocationResult {
  locationId: string;
  name: string;
  coordinates: Coordinates;
  seismicZone: 'II' | 'III' | 'IV' | 'V';
  pga: number;
  vs30: number;
  siteClass: 'A' | 'B' | 'C' | 'D' | 'E';
  distanceToFault: number;
  liquefactionRisk: 'Low' | 'Moderate' | 'High' | 'Very High';
  overallRisk: 'Low' | 'Moderate' | 'High' | 'Very High';
  hazards: HazardSummary[];
  earthquakes: EarthquakeRecord[];
  materials: MaterialRecommendation[];
  guidelines: ArchitecturalGuideline[];
}

export interface HazardSummary {
  type: 'earthquake' | 'flood' | 'landslide' | 'cyclone';
  level: 'Low' | 'Moderate' | 'High' | 'Very High';
  description: string;
}

export interface EarthquakeRecord {
  magnitude: number;
  place: string;
  year: number;
  depth: number;
  distanceKm: number;
}

export interface MaterialRecommendation {
  rank: number;
  name: string;
  reason: string;
  isCode: string;
  suitable: boolean;
}

export interface ArchitecturalGuideline {
  category: string;
  recommendation: string;
  detail: string;
  isCodeRef: string;
}

export interface SearchResult {
  name: string;
  displayName: string;
  lat: number;
  lon: number;
}
