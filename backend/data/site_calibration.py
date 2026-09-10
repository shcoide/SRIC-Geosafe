"""
Calibrated Vs30 reference data for a handful of well-studied cities.

Values are illustrative estimates consistent with published microtremor/HVSR
surveys for these areas (not raw sensor exports). They exist so Vs30 can be
resolved from real site conditions instead of being derived from the IS 1893
seismic zone, which describes tectonic hazard, not local soil stiffness.

Resolution tiers (see services.inference.get_vs30):
  1. CALIBRATED_VS30_POINTS - a specific surveyed point within CALIBRATION_RADIUS_KM
  2. CITY_REGIONS           - interpolated across a known urban survey area
  3. regional geological default (services.inference._regional_default_vs30)

Region geometry: each CITY_REGION used to be modelled as a circle
(centre + radius_km). That's a poor fit for elongated cities — Guwahati runs
along the Brahmaputra, so a circle wide enough to reach the city's east-west
extent over-covers well north and south of the river. Regions now carry an
explicit `geometry` field instead (see CityRegion), checked with shapely
rather than a haversine radius test (services.inference / services.coverage).
`lat`/`lon` remain as the region's centre, but only for map camera
positioning — never for containment.
"""

import math
from typing import List, Literal, Optional, Tuple, TypedDict, Union

CALIBRATION_RADIUS_KM = 2.0


class CalibratedPoint(TypedDict):
    name: str
    vs30: float
    site_class: str


class CalibratedSptPoint(TypedDict):
    name: str
    site_class_spt: str


class LatLon(TypedDict):
    lat: float
    lon: float


class BboxGeometry(TypedDict):
    type: Literal["bbox"]
    north: float
    south: float
    east: float
    west: float


class PolygonGeometry(TypedDict):
    type: Literal["polygon"]
    vertices: List[LatLon]


RegionGeometry = Union[BboxGeometry, PolygonGeometry]

# "provisional_bbox"  - a declared rectangle, not derived from survey data
# "survey_hull"       - a polygon traced from real calibrated survey points
GeometrySource = Literal["provisional_bbox", "survey_hull"]


class CityRegion(TypedDict, total=False):
    name: str
    state: str
    lat: float  # centre — map camera positioning only, NOT used for containment
    lon: float
    geometry: RegionGeometry
    geometrySource: GeometrySource
    interpolation_radius_km: float  # original circle radius this region's bbox was derived from; see region_effective_radius_km
    vs30_min: float
    vs30_max: float
    site_class: Optional[str]
    notes: str
    resonance_hz: Tuple[float, float]
    amplification: Tuple[float, float]
    amplification_frequency_hz: float  # single representative resonant frequency — see get_resonance_amplification()


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def region_polygon(region: CityRegion):
    """Builds the shapely geometry for a region's declared bbox/polygon (lon, lat order)."""
    from shapely.geometry import Polygon, box

    geometry = region["geometry"]
    if geometry["type"] == "bbox":
        return box(geometry["west"], geometry["south"], geometry["east"], geometry["north"])
    if geometry["type"] == "polygon":
        return Polygon([(v["lon"], v["lat"]) for v in geometry["vertices"]])
    raise ValueError(f"Unknown geometry type: {geometry['type']!r}")


def region_contains(region: CityRegion, lat: float, lon: float) -> bool:
    """True if (lat, lon) falls inside the region's declared geometry (bbox or polygon)."""
    from shapely.geometry import Point

    return region_polygon(region).contains(Point(lon, lat))


def find_containing_region(lat: float, lon: float) -> Optional[CityRegion]:
    """
    The CITY_REGION whose declared geometry contains (lat, lon). CITY_REGIONS
    are independently declared, provisional bboxes (see module docstring) —
    nothing prevents two of them from covering the same ground (see
    check_region_overlaps()), so when more than one region contains the
    point, the most specific one wins: the region with the smallest
    geometry area, e.g. Guwahati South's hill-outcrop bbox sitting inside
    Guwahati's much larger valley bbox. This is an explicit precedence
    rule, not incidental CITY_REGIONS declaration order or nearest-centre
    distance — both services.inference's Vs30 resolution and
    services.coverage.find_region_for_point() call this so the two can
    never disagree about which region a point belongs to.
    """
    matches = [region for region in CITY_REGIONS if region_contains(region, lat, lon)]
    if not matches:
        return None
    return min(matches, key=lambda region: region_polygon(region).area)


def check_region_overlaps() -> List[Tuple[str, str, float]]:
    """
    Every pair of CITY_REGIONS whose declared geometries overlap, as
    (name_a, name_b, overlap_area_km2). Meant to be called once at process
    startup (see main.py) and logged as a warning, not raised — an overlap
    is expected to be possible given these are independently hand-declared
    provisional bboxes (see module docstring), and find_containing_region()
    already has a deterministic rule for resolving it. This just makes an
    existing overlap visible in the logs instead of leaving it to be
    inferred from behaviour.

    Area is converted from the polygons' native degree^2 (lon/lat) into an
    approximate km^2 using each pair's mean latitude for the longitude
    scale factor — coarse, but only used for a log line, not a decision.
    """
    overlaps: List[Tuple[str, str, float]] = []
    polygons = [(region, region_polygon(region)) for region in CITY_REGIONS]
    for i, (region_a, poly_a) in enumerate(polygons):
        for region_b, poly_b in polygons[i + 1:]:
            intersection = poly_a.intersection(poly_b)
            if intersection.is_empty:
                continue
            km_per_deg_lat = 111.32
            mean_lat = (region_a["lat"] + region_b["lat"]) / 2
            km_per_deg_lon = km_per_deg_lat * math.cos(math.radians(mean_lat))
            area_km2 = intersection.area * km_per_deg_lat * km_per_deg_lon
            overlaps.append((region_a["name"], region_b["name"], area_km2))
    return overlaps


def region_boundary_vertices(region: CityRegion) -> List[LatLon]:
    """Ordered {lat, lon} vertices describing the region's outline, for map rendering."""
    geometry = region["geometry"]
    if geometry["type"] == "bbox":
        n, s, e, w = geometry["north"], geometry["south"], geometry["east"], geometry["west"]
        return [
            {"lat": n, "lon": w}, {"lat": n, "lon": e},
            {"lat": s, "lon": e}, {"lat": s, "lon": w},
        ]
    return list(geometry["vertices"])


def region_bounds(region: CityRegion) -> dict:
    """Axis-aligned bounding box of the region's geometry (bbox: itself; polygon: its envelope)."""
    geometry = region["geometry"]
    if geometry["type"] == "bbox":
        return {"north": geometry["north"], "south": geometry["south"], "east": geometry["east"], "west": geometry["west"]}
    west, south, east, north = region_polygon(region).bounds
    return {"north": north, "south": south, "east": east, "west": west}


def region_effective_radius_km(region: CityRegion) -> float:
    """
    Radius used only to normalise interpolation distance into [0, 1] for the
    Vs30 min/max blend in get_vs30(). Read directly from the region's
    declared `interpolation_radius_km` (the original circle radius the
    region's bbox/polygon was derived from) rather than computed from the
    geometry's vertices — the geometry is generally not a circle (a square
    bbox's corner is r√2 from centre, not r), so deriving the normalisation
    radius from vertex distance would silently rescale every interpolated
    Vs30 whenever a region's geometry shape changed. This is NOT a
    containment boundary; region_contains() is authoritative for that.
    """
    return region["interpolation_radius_km"]


def region_from_points(points: List[Tuple[float, float]], method: str = "concave", buffer_km: float = 1.0):
    """
    Builds a polygon geometry from real calibrated survey coordinates —
    the intended replacement for a region's provisional bbox once enough
    real survey points exist to trace an actual coverage extent.

    NOT applied to any region yet. CALIBRATED_VS30_POINTS currently holds a
    handful of placeholder points per city (illustrative estimates, per this
    file's own docstring) — nowhere near enough to describe a real survey
    boundary. Wire this in once real microzonation survey coordinates are
    loaded for a city (see README, "What needs more thorough research"),
    then set that region's geometrySource to "survey_hull".

    Uses a concave hull (shapely.concave_hull), not a convex hull, because
    real calibration coverage is rarely convex: surveyed points typically
    trace settlement patterns, river corridors, or road networks rather than
    filling a blob-shaped area. A convex hull would paper over the gaps
    between points and silently claim coverage in unsurveyed areas between
    them — the same "over-covers" failure mode this task replaces the
    circle model for (Guwahati's Brahmaputra-following footprint is exactly
    this shape: elongated and concave, not a disc).

    Args:
        points: (lat, lon) pairs — real calibrated survey coordinates, not
            interpolation guesses.
        method: only "concave" is implemented. Kept as an explicit parameter
            rather than hardcoding the choice, so a future caller has to
            deliberately opt into something else (e.g. "convex") instead of
            silently getting a different shape than they asked for.
        buffer_km: small outward buffer (in km, roughly converted to degrees)
            so the boundary doesn't pass exactly through the outermost
            survey points, which would place those points ON the edge
            rather than inside it.

    Returns:
        A shapely Polygon (lon, lat coordinates) — pass its exterior
        coordinates into a PolygonGeometry's `vertices` (as {lat, lon} dicts)
        when wiring this into a CityRegion.
    """
    if method != "concave":
        raise ValueError(f"Unsupported method: {method!r} — only 'concave' is implemented")
    if len(points) < 4:
        raise ValueError("Need at least 4 points to build a concave hull")

    from shapely import concave_hull
    from shapely.geometry import MultiPoint

    multipoint = MultiPoint([(lon, lat) for lat, lon in points])
    hull = concave_hull(multipoint, ratio=0.3)
    buffer_deg = buffer_km / 111.0  # coarse km->degree conversion; fine at city scale
    return hull.buffer(buffer_deg)


# Individually surveyed points, keyed by (lat, lon).
# Guwahati class E pockets: soft alluvium / backwater-fill sites with low Vs30.
CALIBRATED_VS30_POINTS: dict[Tuple[float, float], CalibratedPoint] = {
    (26.1517, 91.7897): {"name": "Assam Zoo", "vs30": 150.0, "site_class": "E"},
    (26.1868, 91.7466): {"name": "Pan Bazaar", "vs30": 145.0, "site_class": "E"},
    (26.1920, 91.6960): {"name": "IIT Guwahati Campus", "vs30": 155.0, "site_class": "E"},
    (26.1580, 91.6540): {"name": "Maligaon", "vs30": 140.0, "site_class": "E"},
    (26.0950, 91.7550): {"name": "Dhol Gobinda", "vs30": 150.0, "site_class": "E"},
}

# SPT-N (IS 1893) based site classification, resolved independently of Vs30.
# Vs30-based (shear-wave, NEHRP-style) and SPT-N-based (IS 1893) classification
# are documented to disagree at some Indian sites: a shallow weathered/lateritic
# crust can register stiff SPT-N refusal near the surface even where the
# deeper Vs30-averaged profile is soft. This is a real discrepancy, not a data
# error, so it is tracked as a second independent dataset rather than derived
# from CALIBRATED_VS30_POINTS. Points absent here have no SPT-N survey on
# record and must resolve to null, not a copy of the Vs30-based class.
CALIBRATED_SPT_POINTS: dict[Tuple[float, float], CalibratedSptPoint] = {
    (26.1517, 91.7897): {"name": "Assam Zoo", "site_class_spt": "D"},          # disagrees with Vs30 Class E
    (26.1868, 91.7466): {"name": "Pan Bazaar", "site_class_spt": "D"},         # disagrees with Vs30 Class E
    (26.1920, 91.6960): {"name": "IIT Guwahati Campus", "site_class_spt": "E"},  # agrees with Vs30 Class E
    # Maligaon and Dhol Gobinda have no SPT-N survey on record.
}

# City-scale interpolation areas. When a point falls within more than one
# region's geometry, the nearest region centre wins (see services.inference).
#
# Every geometry below is a provisional bbox, derived from this region's
# previous circle (centre + radius_km) via due-N/S/E/W projection, purely so
# switching to the new schema didn't silently change what area counts as
# covered. None of these rectangles come from an actual survey extent — they
# are a placeholder pending real boundary data (see region_from_points()).
CITY_REGIONS: list[CityRegion] = [
    {
        "name": "Guwahati",
        "state": "Assam",
        "lat": 26.1445, "lon": 91.7362,
        # Provisional bbox derived from the old circle (centre 26.1445,91.7362, radius 15km).
        "geometry": {"type": "bbox", "north": 26.27989, "south": 26.00911, "east": 91.88621, "west": 91.58619},
        "geometrySource": "provisional_bbox",
        "interpolation_radius_km": 15.0,
        "vs30_min": 220.0, "vs30_max": 280.0,
        "site_class": "D",
        "notes": "Brahmaputra valley alluvium. Most of the city is Class D; "
                 "see CALIBRATED_VS30_POINTS for softer Class E pockets and the "
                 "'Guwahati South' region for the rockier southern hills. "
                 "Boundary is a provisional bbox, not a survey extent — "
                 "Guwahati runs along the Brahmaputra, so a box this wide "
                 "north-south likely over-covers away from the river.",
    },
    {
        "name": "Guwahati South",
        "state": "Assam",
        "lat": 26.0500, "lon": 91.7800,
        # Provisional bbox derived from the old circle (centre 26.0500,91.7800, radius 6km).
        "geometry": {"type": "bbox", "north": 26.10416, "south": 25.99584, "east": 91.83995, "west": 91.72005},
        "geometrySource": "provisional_bbox",
        "interpolation_radius_km": 6.0,
        "vs30_min": 280.0, "vs30_max": 340.0,
        "site_class": "C",
        "notes": "Basistha/Garbhanga hill outcrops south of the city — "
                 "shallower, stiffer ground than the valley floor. Boundary "
                 "is a provisional bbox, not a survey extent.",
    },
    {
        "name": "Dehradun North",
        "state": "Uttarakhand",
        "lat": 30.3800, "lon": 78.0700,
        # Provisional bbox derived from the old circle (centre 30.3800,78.0700, radius 10km).
        "geometry": {"type": "bbox", "north": 30.47020, "south": 30.28979, "east": 78.17404, "west": 77.96596},
        "geometrySource": "provisional_bbox",
        "interpolation_radius_km": 10.0,
        "vs30_min": 200.0, "vs30_max": 700.0,
        "site_class": None,  # derive from interpolated Vs30 - spans multiple classes
        "notes": "Siwalik foothills / Doon gravel fans. Stiffer and far more "
                 "variable than the valley floor, occasional rock outcrop. "
                 "Boundary is a provisional bbox, not a survey extent. "
                 "50-site MASW/SHAKE2000 amplification analysis reports a "
                 "dominant amplification frequency of 3-4 Hz here — resonant "
                 "with low-rise buildings, not the 1-1.5 Hz measured in "
                 "Dehradun South.",
        "amplification_frequency_hz": 3.5,
    },
    {
        "name": "Dehradun South",
        "state": "Uttarakhand",
        "lat": 30.2600, "lon": 77.9300,
        # Provisional bbox derived from the old circle (centre 30.2600,77.9300, radius 10km).
        "geometry": {"type": "bbox", "north": 30.35021, "south": 30.16979, "east": 78.03391, "west": 77.82609},
        "geometrySource": "provisional_bbox",
        "interpolation_radius_km": 10.0,
        "vs30_min": 180.0, "vs30_max": 400.0,
        "site_class": None,
        "notes": "Doon valley floor toward the Song/Suswa rivers - softer "
                 "alluvial fill than the northern foothills. Boundary is a "
                 "provisional bbox, not a survey extent. 50-site MASW/"
                 "SHAKE2000 amplification analysis reports a dominant "
                 "amplification frequency of 1-1.5 Hz here — resonant with "
                 "mid-rise buildings, the opposite risk profile from "
                 "Dehradun North's 3-4 Hz.",
        "amplification_frequency_hz": 1.25,
    },
    {
        "name": "Bhuj",
        "state": "Gujarat",
        "lat": 23.2420, "lon": 69.6669,
        # Provisional bbox derived from the old circle (centre 23.2420,69.6669, radius 20km).
        "geometry": {"type": "bbox", "north": 23.42259, "south": 23.06141, "east": 69.86233, "west": 69.47147},
        "geometrySource": "provisional_bbox",
        "interpolation_radius_km": 20.0,
        "vs30_min": 220.0, "vs30_max": 300.0,
        "site_class": None,
        "notes": "Kutch basin fill shows no strong shallow impedance contrast, "
                 "so site response here is basin-resonance driven rather than a "
                 "sharp Vs30 boundary: HVSR studies report resonance around "
                 "0.6-1.4 Hz with amplification factors of 1.5-4.4x. Boundary "
                 "is a provisional bbox, not a survey extent.",
        "resonance_hz": (0.6, 1.4),
        "amplification": (1.5, 4.4),
    },
]
