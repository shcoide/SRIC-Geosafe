from pydantic import BaseModel
from typing import List, Optional

class AnalyzeRequest(BaseModel):
    lat: float
    lon: float
    location_name: str
    floors: int = 3
    building_type: str = "residential"

class HazardSummary(BaseModel):
    type: str
    level: str
    description: str

class EarthquakeRecord(BaseModel):
    magnitude: float
    place: str
    year: int
    depth: float
    distanceKm: float

class MaterialRecommendation(BaseModel):
    rank: int
    name: str
    reason: str
    isCode: str
    suitable: bool

class ArchitecturalGuideline(BaseModel):
    category: str
    recommendation: str
    detail: str
    isCodeRef: str

class AnalyzeResponse(BaseModel):
    locationId: str
    name: str
    coordinates: dict
    seismicZone: str
    seismicZoneSource: str
    bedrockPga: float
    bedrockPgaSource: str
    amplificationFactor: float
    amplificationFactorSource: str
    surfacePga: float
    designBaseShearCoefficient: float
    designBaseShearCoefficientSource: str
    vs30: float
    vs30Source: str
    siteClassVs30: str
    siteClassVs30Source: str
    siteClassSpt: Optional[str] = None
    siteClassSptSource: Optional[str] = None
    distanceToFault: Optional[float] = None
    faultName: Optional[str] = None
    faultSlipType: Optional[str] = None
    faultNetSlipRate: Optional[str] = None
    faultSource: Optional[str] = None
    liquefactionRisk: str
    liquefactionRiskSource: str
    overallRisk: str
    hazards: List[HazardSummary]
    earthquakes: List[EarthquakeRecord]
    materials: List[MaterialRecommendation]
    guidelines: List[ArchitecturalGuideline]

class LatLon(BaseModel):
    lat: float
    lon: float

class CoverageBounds(BaseModel):
    north: float
    south: float
    east: float
    west: float

class CalibratedPointSummary(BaseModel):
    name: str
    lat: float
    lon: float
    radiusKm: float
    hasSptData: bool

class CoverageCounts(BaseModel):
    calibratedPoints: int
    withSptData: int

class CoverageRegion(BaseModel):
    id: str
    name: str
    state: str
    seismicZone: str
    center: LatLon
    bounds: CoverageBounds
    boundary: List[LatLon]
    geometrySource: str
    calibratedPoints: List[CalibratedPointSummary]
    counts: CoverageCounts
    dataQuality: str
    notes: str

class NearestRegion(BaseModel):
    id: str
    name: str
    distanceKm: float
    center: LatLon

class CoverageCheckResult(BaseModel):
    inCoverage: bool
    regionId: Optional[str] = None
    regionName: Optional[str] = None
    expectedVs30Source: str
    nearestRegion: Optional[NearestRegion] = None
