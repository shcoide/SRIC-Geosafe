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

export interface CoverageBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

export interface CalibratedPointSummary {
  name: string;
  lat: number;
  lon: number;
  radiusKm: number;
  hasSptData: boolean;
}

export interface CoverageCounts {
  calibratedPoints: number;
  withSptData: number;
}

export interface CoverageRegion {
  id: string;
  name: string;
  state: string;
  seismicZone: 'II' | 'III' | 'IV' | 'V';
  center: Coordinates;
  bounds: CoverageBounds;
  boundary: Coordinates[];
  geometrySource: 'provisional_bbox' | 'survey_hull';
  calibratedPoints: CalibratedPointSummary[];
  counts: CoverageCounts;
  dataQuality: 'calibrated' | 'regional';
  notes: string;
}

export interface NearestRegion {
  id: string;
  name: string;
  distanceKm: number;
  center: Coordinates;
}

export interface CoverageCheckResult {
  inCoverage: boolean;
  regionId: string | null;
  regionName: string | null;
  expectedVs30Source: SiteDataSource;
  nearestRegion: NearestRegion | null;
}
