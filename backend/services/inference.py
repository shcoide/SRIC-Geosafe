"""
Rule-based seismic inference engine.
This simulates what the trained ML model will do.
Replace infer() with model.predict() when real models are trained.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from data.site_calibration import (
    CALIBRATED_SPT_POINTS,
    CALIBRATED_VS30_POINTS,
    CALIBRATION_RADIUS_KM,
    CITY_REGIONS,
    haversine_km,
    region_contains,
    region_effective_radius_km,
)
from data.zone_loader import get_zones, ZONE_FIELD
from services.vs30_raster import read_vs30 as read_vs30_raster

ZONE_PGA = {"II": 0.10, "III": 0.16, "IV": 0.24, "V": 0.36}
ZONE_RISK = {"II": "Low", "III": "Moderate", "IV": "High", "V": "Very High"}

@dataclass
class ZoneResult:
    zone: str
    source: str  # "shapefile" | "approximate"

def get_is1893_zone_bbox(lat: float, lon: float) -> str:
    """
    Coarse bounding-box IS 1893 zone rules. Named fallback for get_is1893_zone()
    when the real zone shapefile (data/is1893_zones/) is missing or fails to load.
    """
    # NE India (Assam, Meghalaya, Manipur, etc.) — Zone V
    if lat >= 24 and lat <= 29 and lon >= 89 and lon <= 97:
        return "V"
    # Uttarakhand, Himachal, parts of Kashmir — Zone IV/V
    if lat >= 30 and lat <= 36 and lon >= 74 and lon <= 82:
        return "V" if lat >= 33 else "IV"
    # J&K, Punjab hills
    if lat >= 32 and lat <= 37 and lon >= 72 and lon <= 77:
        return "IV"
    # Gujarat (Bhuj area) — Zone V
    if lat >= 22 and lat <= 25 and lon >= 68 and lon <= 72:
        return "V" if (lat >= 23 and lon <= 70) else "III"
    # Bihar, UP plains
    if lat >= 24 and lat <= 30 and lon >= 78 and lon <= 88:
        return "IV" if lat >= 28 else "III"
    # Andaman — Zone V
    if lat >= 10 and lat <= 14 and lon >= 92 and lon <= 94:
        return "V"
    # Most of peninsular India
    if lat >= 8 and lat <= 25 and lon >= 72 and lon <= 88:
        return "II" if lat < 16 else "III"
    return "III"

def _query_zone_shapefile(lat: float, lon: float) -> Optional[str]:
    """Point-in-polygon lookup against the shapefile cached by data.zone_loader."""
    gdf = get_zones()
    if gdf is None:
        return None

    from shapely.geometry import Point
    point = Point(lon, lat)
    matches = gdf[gdf.geometry.contains(point)]
    if matches.empty:
        return None
    return str(matches.iloc[0][ZONE_FIELD])

def get_is1893_zone(lat: float, lon: float) -> ZoneResult:
    """
    Resolves the IS 1893 seismic zone via a point-in-polygon query against
    the real zone shapefile loaded at startup (data.zone_loader). Falls back
    to the bounding-box approximation in get_is1893_zone_bbox() when the
    shapefile is missing, fails to load, or doesn't cover this point.
    """
    zone = _query_zone_shapefile(lat, lon)
    if zone is not None:
        return ZoneResult(zone=zone, source="shapefile")
    return ZoneResult(zone=get_is1893_zone_bbox(lat, lon), source="approximate")

@dataclass
class Vs30Result:
    vs30: float
    site_class: str
    source: str  # "measured" | "interpolated" | "modeled" | "assumed"

def _find_calibrated_point(lat: float, lon: float) -> Optional[dict]:
    best_point, best_dist = None, None
    for (plat, plon), point in CALIBRATED_VS30_POINTS.items():
        dist = haversine_km(lat, lon, plat, plon)
        if dist <= CALIBRATION_RADIUS_KM and (best_dist is None or dist < best_dist):
            best_point, best_dist = point, dist
    return best_point

def _match_city_region(lat: float, lon: float) -> Optional[Tuple[dict, float]]:
    """
    Nearest city region whose declared geometry (bbox or polygon — see
    data.site_calibration) actually contains the point, with a 0..1 distance
    fraction for interpolation. Containment is a real shapely geometry test,
    not a haversine-radius test — regions are no longer modelled as circles.
    """
    best_region, best_dist = None, None
    for region in CITY_REGIONS:
        if not region_contains(region, lat, lon):
            continue
        dist = haversine_km(lat, lon, region["lat"], region["lon"])
        if best_dist is None or dist < best_dist:
            best_region, best_dist = region, dist
    if best_region is None:
        return None
    effective_radius = region_effective_radius_km(best_region)
    frac = min(best_dist / effective_radius, 1.0) if effective_radius else 0.0
    return best_region, frac

def _find_city_region(lat: float, lon: float) -> Optional[Tuple[float, str]]:
    """Interpolates Vs30 within the nearest city region whose radius contains the point."""
    match = _match_city_region(lat, lon)
    if match is None:
        return None
    region, frac = match
    vs30 = region["vs30_max"] - (region["vs30_max"] - region["vs30_min"]) * frac
    site_class = region.get("site_class") or get_site_class(vs30)
    return vs30, site_class

def _regional_default_vs30(lat: float, lon: float) -> Tuple[float, str]:
    """
    Coarse geological fallback, keyed to broad geomorphological province
    (alluvial basin vs. foothill vs. hard-rock shield) rather than IS 1893
    seismic zone — Vs30 reflects local soil stiffness, not tectonic hazard.
    """
    # Brahmaputra valley — thick unconsolidated alluvium
    if 24 <= lat <= 29 and 89 <= lon <= 97:
        return 240.0, "D"
    # Himalayan / sub-Himalayan foothills — stiffer, mixed rock-soil
    if 28 <= lat <= 36 and 74 <= lon <= 82:
        return 420.0, "C"
    # Indo-Gangetic alluvial plain
    if 24 <= lat <= 30 and 78 <= lon <= 88:
        return 260.0, "D"
    # Kutch / Gujarat rift basin sediments
    if 22 <= lat <= 25 and 68 <= lon <= 72:
        return 280.0, "D"
    # Peninsular shield — hard crystalline rock (granite/gneiss/Deccan trap)
    if 8 <= lat <= 25 and 72 <= lon <= 88:
        return 480.0, "C"
    # Andaman volcanic/sedimentary arc
    if 10 <= lat <= 14 and 92 <= lon <= 94:
        return 300.0, "D"
    return 320.0, "C"

def get_vs30(lat: float, lon: float) -> Vs30Result:
    """
    Resolves Vs30 (and site class) as an input independent of the IS 1893
    seismic zone, in order of decreasing confidence:
      1. A calibrated field measurement within CALIBRATION_RADIUS_KM
      2. Interpolation across a known city survey area
      3. The USGS Global Vs30 raster (services.vs30_raster) — a real
         measurement-derived product, but coarse (~1km, topographic-slope
         proxy) and not yet validated at city scale; see scripts/validate_vs30.py.
         Ranked below the curated city tiers above until that's done.
      4. A coarse regional geological default
    """
    point = _find_calibrated_point(lat, lon)
    if point is not None:
        return Vs30Result(vs30=point["vs30"], site_class=point["site_class"], source="measured")

    city_match = _find_city_region(lat, lon)
    if city_match is not None:
        vs30, site_class = city_match
        return Vs30Result(vs30=vs30, site_class=site_class, source="interpolated")

    raster_vs30 = read_vs30_raster(lat, lon)
    if raster_vs30 is not None:
        return Vs30Result(vs30=raster_vs30, site_class=get_site_class(raster_vs30), source="modeled")

    vs30, site_class = _regional_default_vs30(lat, lon)
    return Vs30Result(vs30=vs30, site_class=site_class, source="assumed")

def get_site_class_spt(lat: float, lon: float) -> Optional[Tuple[str, str]]:
    """
    SPT-N (IS 1893) based site classification, resolved independently of the
    Vs30-based classification — the two are documented to disagree at some
    Indian sites, so this must never be derived from get_vs30().

    Only returns a result where a calibrated SPT-N survey point exists within
    CALIBRATION_RADIUS_KM. There is no interpolated or assumed tier: without
    an actual borehole/SPT record, guessing a value from Vs30 would silently
    collapse the two classifications back into one.
    """
    best_point, best_dist = None, None
    for (plat, plon), point in CALIBRATED_SPT_POINTS.items():
        dist = haversine_km(lat, lon, plat, plon)
        if dist <= CALIBRATION_RADIUS_KM and (best_dist is None or dist < best_dist):
            best_point, best_dist = point, dist
    if best_point is None:
        return None
    return best_point["site_class_spt"], "measured"

@dataclass
class AmplificationResult:
    factor: float
    source: str  # "measured" | "interpolated" | "modeled" | "assumed"

@dataclass
class BedrockPgaResult:
    pga: float
    source: str  # "measured" (real fault distance) | "assumed" (un-attenuated zone PGA)

def get_bedrock_pga(zone: str, distance_to_fault_km: Optional[float]) -> BedrockPgaResult:
    """
    Ground motion at rock level (Vs30 ~ 760 m/s), from IS 1893 zone PGA
    attenuated by distance to the nearest mapped active fault (services.faults).
    Independent of Vs30/soil — this is bedrock shaking, before any site
    response is applied.

    distance_to_fault_km is None when services.faults.nearest_fault() found
    no real fault geometry (dataset missing, or nothing within range) — in
    that case this returns the un-attenuated zone PGA rather than fabricating
    a distance-based adjustment.
    """
    if distance_to_fault_km is None:
        return BedrockPgaResult(pga=ZONE_PGA[zone], source="assumed")

    reference_km = 25.0
    raw_factor = (reference_km / max(distance_to_fault_km, 5.0)) ** 0.5
    factor = min(max(raw_factor, 0.5), 1.8)
    return BedrockPgaResult(pga=round(ZONE_PGA[zone] * factor, 4), source="measured")

def _amplification_from_vs30(vs30: float) -> float:
    """
    Generic site-response multiplier relative to rock (Vs30 = 760 m/s),
    independent of seismic zone: softer soil amplifies bedrock motion more.
    """
    factor = (760.0 / max(vs30, 1.0)) ** 0.35
    return round(min(max(factor, 1.0), 3.0), 3)

def get_amplification_factor(lat: float, lon: float, vs30_result: Vs30Result) -> AmplificationResult:
    """
    Site response multiplier from Vs30/soil profile, independent of zone.

    Cities with directly observed HVSR amplification data override the
    generic Vs30 formula — e.g. Bhuj, where no strong impedance contrast
    was found beneath the city, so the usual "soft soil -> high amplification"
    formula would misattribute the 2001 damage to site response when it was
    actually driven by bedrock motion.
    """
    match = _match_city_region(lat, lon)
    if match is not None:
        region, frac = match
        amp_range = region.get("amplification")
        if amp_range is not None:
            amp_min, amp_max = amp_range
            factor = amp_max - (amp_max - amp_min) * frac
            return AmplificationResult(factor=round(factor, 3), source=vs30_result.source)

    return AmplificationResult(factor=_amplification_from_vs30(vs30_result.vs30), source=vs30_result.source)

def get_site_class(vs30: float) -> str:
    if vs30 >= 760: return "A"
    if vs30 >= 360: return "B"
    if vs30 >= 180: return "C"
    if vs30 >= 90:  return "D"
    return "E"

def get_liquefaction_risk(vs30: float, zone: str) -> str:
    if vs30 < 180 and zone in ("IV", "V"): return "Very High"
    if vs30 < 250 and zone in ("IV", "V"): return "High"
    if vs30 < 360 and zone == "III":        return "Moderate"
    return "Low"

# This app's Vs30-based site_class (A-E, a NEHRP-style scheme) predates IS
# 1893's own soil classification, which only has three types. This mapping
# is this codebase's interpretation, not an IS 1893 table:
#   Type I   (Rock or Hard Soil) <- A, B  (Vs30 >= 360 m/s)
#   Type II  (Medium Soil)       <- C     (180-360 m/s)
#   Type III (Soft Soil)         <- D, E  (< 180 m/s)
IS1893_SOIL_TYPE_MAP = {"A": "I", "B": "I", "C": "II", "D": "III", "E": "III"}

@dataclass
class DesignSpectrumResult:
    sa_g: float
    is_code_ref: str

def get_design_spectrum(site_class: str, period: float) -> DesignSpectrumResult:
    """
    IS 1893 (Part 1):2016, Table 3 — average response acceleration
    coefficient (Sa/g) for 5% damping, as a function of the undamped
    natural period T (seconds). This is the real code-specified spectral
    shape; nothing here is invented.
    """
    soil_type = IS1893_SOIL_TYPE_MAP.get(site_class, "II")
    t = max(period, 0.0)

    if soil_type == "I":
        if t <= 0.10: sa_g = 1 + 15 * t
        elif t <= 0.40: sa_g = 2.5
        else: sa_g = 1.0 / t
    elif soil_type == "III":
        if t <= 0.10: sa_g = 1 + 15 * t
        elif t <= 0.67: sa_g = 2.5
        else: sa_g = 1.67 / t
    else:  # Type II, medium soil
        if t <= 0.10: sa_g = 1 + 15 * t
        elif t <= 0.55: sa_g = 2.5
        else: sa_g = 1.36 / t

    return DesignSpectrumResult(sa_g=round(sa_g, 4), is_code_ref="IS 1893 Part 1 Table 3")

@dataclass
class DesignBaseShearResult:
    ah: float
    source: str  # mirrors the Vs30 resolution tier this depends on, via site_class

def estimate_fundamental_period_sec(floors: int, storey_height_m: float = 3.0) -> float:
    """
    IS 1893 (Part 1):2016 Cl 7.6.2 empirical fundamental period for an RC
    moment-frame building without brick infill: Ta = 0.075 * h^0.75, h in
    metres. Storey height is assumed at 3m/floor (not returned by the API,
    so this is a simplifying assumption, not a measurement).
    """
    height_m = max(floors, 1) * storey_height_m
    return round(0.075 * height_m ** 0.75, 4)

def get_design_base_shear_coefficient(
    zone: str,
    site_class: str,
    period: float,
    vs30_source: str,
    importance_factor: float = 1.0,
    response_reduction_factor: float = 5.0,
) -> DesignBaseShearResult:
    """
    Design horizontal seismic base shear coefficient, IS 1893 (Part 1):2016
    Cl 7.5.3: Ah = (Z/2)(I/R)(Sa/g).

    Z is the zone factor (ZONE_PGA — the same table IS 1893 calls Z: 0.10 /
    0.16 / 0.24 / 0.36 for Zone II-V). I and R default to 1.0 and 5.0 (an
    ordinary RC moment frame, OMRF-ish) and are both overridable by callers
    who know the actual importance class / structural system.
    """
    z = ZONE_PGA[zone]
    spectrum = get_design_spectrum(site_class, period)
    ah = (z / 2) * (importance_factor / response_reduction_factor) * spectrum.sa_g
    return DesignBaseShearResult(ah=round(ah, 4), source=vs30_source)

def get_materials(zone: str, site_class: str, floors: int, building_type: str) -> List[dict]:
    """
    site_class is accepted but deliberately not branched on: no IS code
    provision links site/soil class to structural material selection (site
    class governs design forces via the response spectrum — see
    get_design_spectrum() — not which material system is appropriate).
    Branching this on site_class without a citable IS clause would produce
    authoritative-looking output with no real basis. This is the intended
    insertion point for the trained damage/inference model, which can learn
    real site-dependent material performance from data instead.
    """
    if zone in ("IV", "V"):
        recommended = [
            {"rank": 1, "name": "RC moment frame with shear walls", "reason": "Best ductility and lateral resistance for Zone IV/V. Proven in NE India earthquakes.", "isCode": "IS 456 + IS 13920", "suitable": True},
            {"rank": 2, "name": "Confined masonry", "reason": "Cost-effective for 1–2 storey. RC columns and tie beams confine masonry panels effectively.", "isCode": "IS 4326", "suitable": True},
            {"rank": 3, "name": "Light gauge steel frame", "reason": "Lightweight — reduces seismic inertial forces. Ideal for soft soil (Class D/E) sites.", "isCode": "IS 801", "suitable": True},
        ]
        avoid = [
            {"rank": 4, "name": "Unreinforced brick masonry", "reason": "No ductility. Collapses catastrophically in Zone IV/V without confinement.", "isCode": "IS 1905", "suitable": False},
            {"rank": 5, "name": "Flat slab without walls", "reason": "Punching shear failure at column connections during lateral loading.", "isCode": "IS 456", "suitable": False},
        ]
    elif zone == "III":
        recommended = [
            {"rank": 1, "name": "RC frame with infill walls", "reason": "Adequate for Zone III with proper gap detailing around infill panels.", "isCode": "IS 456 + IS 13920", "suitable": True},
            {"rank": 2, "name": "Reinforced masonry", "reason": "Suitable for low-rise (≤3 floors) residential in Zone III with steel reinforcement.", "isCode": "IS 1905", "suitable": True},
        ]
        avoid = [
            {"rank": 3, "name": "Unreinforced masonry above 2 storeys", "reason": "Insufficient seismic resistance for multi-storey in Zone III.", "isCode": "IS 1905", "suitable": False},
        ]
    else:
        recommended = [
            {"rank": 1, "name": "RC frame or reinforced masonry", "reason": "Standard construction adequate for Zone II with basic seismic detailing.", "isCode": "IS 456", "suitable": True},
        ]
        avoid = []
    return recommended + avoid

def get_guidelines(zone: str, site_class: str) -> List[dict]:
    base = [
        {"category": "Foundation", "recommendation": "Raft / mat foundation", "detail": "Required on Class C/D/E soil. Prevents differential settlement during ground shaking.", "isCodeRef": "IS 1893 Cl. 6.3"},
        {"category": "Column reinforcement", "recommendation": f"Min. {'1.5%' if zone in ('IV','V') else '1.0%'} steel ratio", "detail": "Confining hoops at 100 mm c/c in plastic hinge zones (500 mm from joint).", "isCodeRef": "IS 13920 Cl. 7.3"},
        {"category": "Beam-column joint", "recommendation": "Strong column – weak beam design", "detail": "Sum of column moment capacities must exceed sum of beam moment capacities at each joint.", "isCodeRef": "IS 13920 Cl. 7.2.1"},
        {"category": "Roof", "recommendation": "Lightweight RCC slab", "detail": "Avoid heavy roof mass. Each additional tonne of roof mass increases seismic force by PGA × 1000 kg.", "isCodeRef": "IS 1893 Cl. 7.6"},
        {"category": "Infill walls", "recommendation": "Leave gap between infill and RC frame", "detail": "Min. 20mm gap prevents short-column effect which causes brittle shear failure.", "isCodeRef": "IS 13920 Cl. 9.1"},
    ]
    if zone in ("IV", "V") and site_class in ("D", "E"):
        base.append({
            "category": "Liquefaction mitigation",
            "recommendation": "Deep foundation or ground improvement",
            "detail": "Pile foundation to competent layer below liquefiable zone, or dynamic compaction / stone columns.",
            "isCodeRef": "IS 1893 Part 1 Annex F"
        })
    return base

def get_hazards(zone: str, lat: float, lon: float) -> List[dict]:
    zone_eq = {"II": "Low", "III": "Moderate", "IV": "High", "V": "Very High"}
    flood_risk = "High" if (lat >= 24 and lat <= 30 and lon >= 84 and lon <= 92) else "Moderate" if lat < 20 else "Low"
    landslide_risk = "Moderate" if (lat >= 28 or (lat >= 24 and lon >= 90)) else "Low"
    cyclone_risk = "High" if (lat <= 14 and lon >= 80) or (lat >= 20 and lat <= 24 and lon >= 85 and lon <= 92) else "Low"

    return [
        {"type": "earthquake", "level": zone_eq[zone], "description": f"IS 1893 Zone {zone} seismic activity"},
        {"type": "flood", "level": flood_risk, "description": "Based on river proximity and elevation"},
        {"type": "landslide", "level": landslide_risk, "description": "Based on slope and geology"},
        {"type": "cyclone", "level": cyclone_risk, "description": "Based on coastal proximity"},
    ]
