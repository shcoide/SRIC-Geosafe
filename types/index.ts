export interface Coordinates {
  lat: number;
  lon: number;
}

export type SiteDataSource = 'measured' | 'interpolated' | 'modeled' | 'assumed';

// Provenance for HazardSummary entries: earthquake reuses the real seismic
// zone's source ('shapefile' | 'approximate' — see seismicZoneSource);
// flood/landslide/cyclone are lat/lon bounding-box rules only, no river,
// elevation, slope, geology, or coastline data — 'regional_bbox' says so
// honestly instead of implying a method that was never used.
export type HazardSource = 'shapefile' | 'approximate' | 'regional_bbox';

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
  // Estimated real spectral acceleration (g) at the building's period —
  // Z x Sa/g from the IS 1893 design spectrum, the input to the
  // fragility-based material ranking below (see MaterialRecommendation).
  // Not the same quantity as surfacePga (bedrock x amplification, no
  // spectral shape) — see backend/routers/analyze.py for the derivation.
  surfaceSa: number;
  // Building-resonance approximation (services/inference.py
  // get_resonance_amplification) — already folded into amplificationFactor
  // and surfacePga above; these fields exist to explain that number, not to
  // be applied again. resonanceZone "indeterminate" means the site has no
  // measured amplification frequency (e.g. Bhuj), not "no resonance risk".
  resonanceFactor: number;
  resonanceZone: 'strong' | 'moderate' | 'none' | 'indeterminate';
  buildingPeriodS: number;
  amplificationFrequencyHz: number | null;
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
  source: HazardSource;
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
  // suitable is a RELATIVE ranking (top half of the 4 typologies by lowest
  // collapseProbability), not an absolute safety threshold — see `note` for
  // the human-readable reason, and backend/services/inference.py's
  // get_materials() docstring for why a fixed P(DS>=DS4) cutoff was dropped
  // (it produced zero suitable typologies at every Zone V site).
  // suitable is a band-tolerance, cost-sensitive ranking — the lowest-
  // collapseProbability typology is always suitable; each subsequent one
  // (ascending order) joins only if it's within BAND_TOLERANCE_BY_BUDGET's
  // band of the last typology marked suitable AND no more expensive — see
  // backend/services/inference.py's get_materials() docstring. `note`
  // explains which case applied (lowest risk / comparable risk at lower
  // cost / higher risk).
  suitable: boolean;
  note: string;
  // Fragility-based ranking (backend/data/fragility_curves.py) — collapseProbability
  // is P(DS>=DS4) (0-1) at the site's estimated surface Sa, the value the
  // ranking is sorted by (ascending); moderateDamageProbability is P(DS>=DS2).
  // rankingBasis is always 'fragility_sa_convolution' for now (the one ranking
  // method this app has), kept as a string field so a future alternative
  // ranking method doesn't need a schema change.
  collapseProbability: number;
  moderateDamageProbability: number;
  rankingBasis: string;
  // relativeCost: 1-5 (1=lowest), from data/fragility_curves.py — indicative
  // Indian market rates, not a quantity survey. costLabel is the same value
  // bucketed for display: 1-2 "Low cost", 3 "Moderate cost", 4-5 "Higher cost".
  relativeCost: number;
  costLabel: string;
}

export type BudgetPreference = 'any' | 'low' | 'moderate';

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
