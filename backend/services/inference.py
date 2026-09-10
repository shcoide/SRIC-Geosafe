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
    find_containing_region,
    haversine_km,
    region_effective_radius_km,
)
from data.zone_loader import get_zones, ZONE_FIELD
from data.fragility_curves import TYPOLOGIES, compute_damage_probability
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
    City region whose declared geometry (bbox or polygon — see
    data.site_calibration) actually contains the point, with a 0..1 distance
    fraction for interpolation. Containment is a real shapely geometry test,
    not a haversine-radius test — regions are no longer modelled as circles.
    When more than one region's geometry contains the point (see
    data.site_calibration.check_region_overlaps()), find_containing_region()
    picks the most specific (smallest-area) one, not whichever has the
    nearest centre — the same rule services.coverage.find_region_for_point()
    uses, so the two never disagree.
    """
    best_region = find_containing_region(lat, lon)
    if best_region is None:
        return None
    best_dist = haversine_km(lat, lon, best_region["lat"], best_region["lon"])
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

def get_building_period(
    floors: int,
    building_type: str,
    storey_height_m: float = 3.0,
    infill_dimension_m: float = 15.0,
) -> Tuple[float, str]:
    """
    IS 1893 (Part 1):2016 Cl 7.6.2 empirical fundamental period, used for the
    building-resonance check (get_resonance_amplification) — separate from
    estimate_fundamental_period_sec() above, which the design base shear
    calculation always treats as a bare frame regardless of building_type.

    Two formulae, selected by building_type:
      - Bare RC moment frame (no masonry infill): Ta = 0.075 * h^0.75
      - RC frame with masonry infill: Ta = 0.09h / sqrt(d)
        AnalyzeRequest doesn't collect a building plan dimension, so d uses
        IS 1893's own worked-example default of 15m rather than inventing
        an estimate from floors alone.

    "industrial" buildings are modelled as bare frames (large-span sheds
    typically aren't infilled); "residential" and "commercial" — and
    anything else the caller passes — are modelled as infilled frames,
    the far more common case in Indian construction for both.
    """
    height_m = max(floors, 1) * storey_height_m
    if building_type == "industrial":
        ta = 0.075 * height_m ** 0.75
        clause = "IS 1893 (Part 1):2016 Cl 7.6.2 (bare RC frame)"
    else:
        ta = (0.09 * height_m) / (infill_dimension_m ** 0.5)
        clause = "IS 1893 (Part 1):2016 Cl 7.6.2 (RC frame with masonry infill, d=15m assumed)"
    return round(ta, 4), clause

def get_amplification_frequency_hz(lat: float, lon: float) -> Optional[float]:
    """
    Single representative resonant frequency for the city region containing
    (lat, lon) — the Dehradun finding that motivated this feature: a 50-site
    MASW/SHAKE2000 survey found the dominant amplification frequency runs
    3-4 Hz in the north of the city (favouring low-rise resonance) against
    1-1.5 Hz in the south-west (favouring mid-rise resonance), even though
    both fall under the same IS 1893 Zone IV label.

    Returns None wherever the matched region carries no measured
    amplification_frequency_hz, or no region matches at all. Bhuj is a
    deliberate case of the former: its HVSR data shows no strong shallow
    impedance contrast, so there is no reliable single resonant peak to
    report — get_resonance_amplification() treats that honestly as
    "indeterminate" rather than inventing a frequency.
    """
    match = _match_city_region(lat, lon)
    if match is None:
        return None
    region, _frac = match
    return region.get("amplification_frequency_hz")

@dataclass
class ResonanceResult:
    resonance_factor: float
    resonance_zone: str  # "strong" | "moderate" | "none" | "indeterminate"

def get_resonance_amplification(site_period: Optional[float], building_period: float) -> ResonanceResult:
    """
    Approximates the risk that a proposed building's fundamental period
    couples with the site's dominant resonance period. This is a simplified
    period-proximity approximation, not a real dynamic analysis — an actual
    resonance assessment requires full soil-structure interaction modelling,
    not a ratio of two single numbers. Treat resonance_factor as a coarse
    risk flag, not a design value.

    site_period is None wherever get_amplification_frequency_hz() found no
    measured frequency for this location (Bhuj, and any control point with
    no city region match at all) — returned as resonance_zone
    "indeterminate" rather than assuming "none", since "no data" and "no
    resonance risk" are not the same claim.
    """
    if site_period is None:
        return ResonanceResult(resonance_factor=1.0, resonance_zone="indeterminate")

    ratio = abs(building_period - site_period) / site_period
    if ratio <= 0.2:
        return ResonanceResult(resonance_factor=2.0, resonance_zone="strong")
    if ratio <= 0.4:
        return ResonanceResult(resonance_factor=1.5, resonance_zone="moderate")
    return ResonanceResult(resonance_factor=1.0, resonance_zone="none")

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

# Band-tolerance width (as a fraction, e.g. 0.10 = 10 percentage points of
# collapse probability), keyed by AnalyzeRequest.budget_preference. Widths
# were derived, not guessed: get_materials()'s band-tolerance-plus-cost
# comparison only lets a typology join "suitable" by being within this band
# of AND cheaper than the current best — so the width has to be at least as
# large as the real probability gap between two typologies for cost to ever
# get a chance to prefer the cheaper one. At Zone V (surface_sa ~0.9g), the
# gap between light gauge steel and RC moment frame is ~7.6 points; at Zone
# II (~0.25g), the gap between RC moment frame and confined masonry is
# ~8.4 points. "low" (a budget-conscious user) gets the widest band, so a
# cheaper option gets the most room to be accepted as "close enough";
# "any" (no budget preference) gets the narrowest, so only a near-identical
# alternative ever displaces the safest option on cost grounds alone.
BAND_TOLERANCE_BY_BUDGET = {
    "low": 0.15,
    "moderate": 0.10,
    "any": 0.08,
}
DEFAULT_BUDGET_PREFERENCE = "any"

def _cost_label(relative_cost: int) -> str:
    if relative_cost <= 2:
        return "Low cost"
    if relative_cost == 3:
        return "Moderate cost"
    return "Higher cost"

def get_materials(surface_sa: float, budget_preference: str = DEFAULT_BUDGET_PREFERENCE) -> List[dict]:
    """
    Fragility-based structural material ranking, replacing the previous
    zone-only hardcoded lists (which branched on `zone` alone and never
    varied by site class — see git history / explanation/CHANGELOG.md for
    that version). For each typology in data/fragility_curves.py, computes
    P(DS>=DS2) (moderate damage) and P(DS>=DS4) (collapse) at the site's
    surface_sa via the standard lognormal fragility function
    (compute_damage_probability), then ranks ascending by P(DS>=DS4) —
    lowest collapse probability first.

    surface_sa is derived from both seismic zone and site class (see
    routers/analyze.py: Z x Sa/g, the IS 1893 zone factor times the design
    spectrum's spectral shape at the building's estimated period), so the
    ranking genuinely depends on both without this function branching on
    either directly.

    Per data/fragility_curves.py's own docstring: these fragility
    parameters, and its relative_cost indices, are indicative values — not
    a substitute for site-specific fragility analysis, structural design,
    or a real quantity survey.

    suitable is a BAND-TOLERANCE, COST-SENSITIVE ranking — not a fixed
    top-half cutoff (an earlier version's rule) and not an absolute
    P(DS>=DS4) threshold (the version before that, which returned zero
    suitable typologies at every Zone V site). The lowest-collapse-
    probability typology is always suitable. Each subsequent typology (in
    ascending collapse-probability order) joins "suitable" only if BOTH:
    its collapse probability is within `band_tolerance` (see
    BAND_TOLERANCE_BY_BUDGET) of the *last typology that was itself marked
    suitable*, AND its relative_cost is no higher than that typology's. A
    typology outside the band, or inside the band but pricier, is
    suitable=False — but the comparison anchor for the *next* typology
    doesn't move past it, so a single expensive typology in the middle of
    the ranking can't block a cheaper, still-close-enough option further
    down from qualifying.

    This fixes a real problem the earlier fixed top-two rule had: at low
    surface_sa (Zone II/III), the top two typologies by raw collapse
    probability are always the same two regardless of zone (their fragility
    curves never cross rank order across this app's surface_sa range), so a
    much cheaper typology with a negligibly higher — sometimes ~1% —
    collapse probability was marked "avoid" purely because it ranked 3rd,
    not because it was actually unsafe. Band-tolerance ranking lets a
    cheaper, comparably-safe option in regardless of its raw rank position.
    """
    band_tolerance = BAND_TOLERANCE_BY_BUDGET.get(budget_preference, BAND_TOLERANCE_BY_BUDGET[DEFAULT_BUDGET_PREFERENCE])

    ranked = sorted(
        (
            (
                compute_damage_probability(surface_sa, typology["ds4_median_sa"], typology["ds4_beta"]),
                compute_damage_probability(surface_sa, typology["ds2_median_sa"], typology["ds2_beta"]),
                typology,
            )
            for typology in TYPOLOGIES.values()
        ),
        key=lambda row: row[0],
    )

    materials = []
    anchor_prob = None
    anchor_cost = None
    for i, (p_ds4, p_ds2, typology) in enumerate(ranked):
        cost = typology["relative_cost"]
        if i == 0:
            suitable = True
            promoted_on_cost = False
        else:
            gap = p_ds4 - anchor_prob  # ascending sort => always >= 0
            suitable = gap <= band_tolerance and cost <= anchor_cost
            promoted_on_cost = suitable

        if suitable:
            anchor_prob, anchor_cost = p_ds4, cost

        pct = round(p_ds4 * 100)
        if i == 0:
            note = f"Lowest collapse risk among assessed typologies. Absolute probability: {pct}%."
        elif promoted_on_cost:
            note = f"Comparable collapse risk to the safest option, at lower cost. Absolute probability: {pct}%."
        else:
            note = f"Higher collapse risk than the recommended options at this site. Absolute probability: {pct}%."

        materials.append({
            "rank": i + 1,
            "name": typology["name"],
            "reason": (
                f"{pct}% probability of collapse-level damage (DS4) at this "
                f"site's estimated Sa = {surface_sa:.2f}g. {typology['description']}."
            ),
            "isCode": typology["is_code"],
            "suitable": suitable,
            "note": note,
            "collapseProbability": round(p_ds4, 2),
            "moderateDamageProbability": round(p_ds2, 2),
            "rankingBasis": "fragility_sa_convolution",
            "relativeCost": cost,
            "costLabel": _cost_label(cost),
        })
    return materials

def get_guidelines(zone: str, site_class: str) -> List[dict]:
    # IS CODE CITATIONS — VERIFICATION STATUS
    # Confirmed against BIS documents: IS 1893 Cl. 7.6.2 (period formula)
    # Unverified (plausible but not checked): all others
    # Before publication: open IS 1893:2016, IS 13920:2016,
    # IS 4326:2013 and verify each clause number and edition year.
    # IS codes are revised periodically; a clause number in one
    # edition may refer to different content in another.
    base = [
        {"category": "Foundation", "recommendation": "Raft / mat foundation", "detail": "Required on Class C/D/E soil. Prevents differential settlement during ground shaking.", "isCodeRef": "IS 1893 Cl. 6.3"},  # VERIFY: IS 1893 Cl. 6.3 — needs confirmation against BIS document
        {"category": "Column reinforcement", "recommendation": f"Min. {'1.5%' if zone in ('IV','V') else '1.0%'} steel ratio", "detail": "Confining hoops at 100 mm c/c in plastic hinge zones (500 mm from joint).", "isCodeRef": "IS 13920 Cl. 7.3"},  # VERIFY: IS 13920 Cl. 7.3 — needs confirmation against BIS document
        {"category": "Beam-column joint", "recommendation": "Strong column – weak beam design", "detail": "Sum of column moment capacities must exceed sum of beam moment capacities at each joint.", "isCodeRef": "IS 13920 Cl. 7.2.1"},  # VERIFY: IS 13920 Cl. 7.2.1 — needs confirmation against BIS document
        {"category": "Roof", "recommendation": "Lightweight RCC slab", "detail": "Avoid heavy roof mass. Each additional tonne of roof mass increases seismic force by PGA × 1000 kg.", "isCodeRef": "IS 1893 Cl. 7.6"},  # VERIFY: IS 1893 Cl. 7.6 — needs confirmation against BIS document
        {"category": "Infill walls", "recommendation": "Leave gap between infill and RC frame", "detail": "Min. 20mm gap prevents short-column effect which causes brittle shear failure.", "isCodeRef": "IS 13920 Cl. 9.1"},  # VERIFY: IS 13920 Cl. 9.1 — needs confirmation against BIS document
    ]
    if zone in ("IV", "V") and site_class in ("D", "E"):
        base.append({
            "category": "Liquefaction mitigation",
            "recommendation": "Deep foundation or ground improvement",
            "detail": "Pile foundation to competent layer below liquefiable zone, or dynamic compaction / stone columns.",
            "isCodeRef": "IS 1893 Part 1 Annex F"  # VERIFY: IS 1893 Part 1 Annex F — needs confirmation against BIS document
        })
    return base

def get_hazards(zone: str, zone_source: str, lat: float, lon: float) -> List[dict]:
    """
    flood/landslide/cyclone levels come only from lat/lon bounding-box rules
    below — no river, elevation, slope, geology, or coastline data is
    actually consulted, so their description/source must say so honestly
    rather than name inputs that were never read. "regional_bbox" is that
    same honest source for all three. earthquake's level is a direct
    reclassification of the real seismic zone (see get_is1893_zone), so it
    carries zone_source ("shapefile" or "approximate") instead.
    """
    zone_eq = {"II": "Low", "III": "Moderate", "IV": "High", "V": "Very High"}
    flood_risk = "High" if (lat >= 24 and lat <= 30 and lon >= 84 and lon <= 92) else "Moderate" if lat < 20 else "Low"
    landslide_risk = "Moderate" if (lat >= 28 or (lat >= 24 and lon >= 90)) else "Low"
    cyclone_risk = "High" if (lat <= 14 and lon >= 80) or (lat >= 20 and lat <= 24 and lon >= 85 and lon <= 92) else "Low"

    return [
        {"type": "earthquake", "level": zone_eq[zone], "description": f"IS 1893 Zone {zone} seismic activity", "source": zone_source},
        {"type": "flood", "level": flood_risk, "description": "Based on regional location classification", "source": "regional_bbox"},
        {"type": "landslide", "level": landslide_risk, "description": "Based on regional location classification", "source": "regional_bbox"},
        {"type": "cyclone", "level": cyclone_risk, "description": "Based on regional location classification", "source": "regional_bbox"},
    ]
