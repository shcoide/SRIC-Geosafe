export interface Coordinates {
  lat: number;
  lon: number;
}

export type SiteDataSource = 'measured' | 'interpolated' | 'modeled' | 'assumed';

export interface LocationResult {
  locationId: string;
  name: string;
  coordinates: Coordinates;
  seismicZone: 'II' | 'III' | 'IV' | 'V';
  seismicZoneSource: 'shapefile' | 'approximate';
  bedrockPga: number;
  bedrockPgaSource: SiteDataSource;
  amplificationFactor: number;
  amplificationFactorSource: SiteDataSource;
  surfacePga: number;
  designBaseShearCoefficient: number;
  designBaseShearCoefficientSource: SiteDataSource;
  vs30: number;
  vs30Source: SiteDataSource;
  siteClassVs30: 'A' | 'B' | 'C' | 'D' | 'E';
  siteClassVs30Source: SiteDataSource;
  siteClassSpt: 'A' | 'B' | 'C' | 'D' | 'E' | null;
  siteClassSptSource: SiteDataSource | null;
  distanceToFault: number | null;
  faultName: string | null;
  faultSlipType: string | null;
  faultNetSlipRate: string | null;
  faultSource: SiteDataSource | null;
  liquefactionRisk: 'Low' | 'Moderate' | 'High' | 'Very High';
  liquefactionRiskSource: SiteDataSource;
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
