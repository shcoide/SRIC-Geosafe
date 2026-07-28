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
"""

import math
from typing import Optional, Tuple, TypedDict

CALIBRATION_RADIUS_KM = 2.0


class CalibratedPoint(TypedDict):
    name: str
    vs30: float
    site_class: str


class CalibratedSptPoint(TypedDict):
    name: str
    site_class_spt: str


class CityRegion(TypedDict, total=False):
    name: str
    lat: float
    lon: float
    radius_km: float
    vs30_min: float
    vs30_max: float
    site_class: Optional[str]
    notes: str
    resonance_hz: Tuple[float, float]
    amplification: Tuple[float, float]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


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

# City-scale interpolation areas. When a point falls within radius_km of more
# than one region, the nearest region center wins (see services.inference).
CITY_REGIONS: list[CityRegion] = [
    {
        "name": "Guwahati",
        "lat": 26.1445, "lon": 91.7362,
        "radius_km": 15.0,
        "vs30_min": 220.0, "vs30_max": 280.0,
        "site_class": "D",
        "notes": "Brahmaputra valley alluvium. Most of the city is Class D; "
                 "see CALIBRATED_VS30_POINTS for softer Class E pockets and the "
                 "'Guwahati South' region for the rockier southern hills.",
    },
    {
        "name": "Guwahati South",
        "lat": 26.0500, "lon": 91.7800,
        "radius_km": 6.0,
        "vs30_min": 280.0, "vs30_max": 340.0,
        "site_class": "C",
        "notes": "Basistha/Garbhanga hill outcrops south of the city — "
                 "shallower, stiffer ground than the valley floor.",
    },
    {
        "name": "Dehradun North",
        "lat": 30.3800, "lon": 78.0700,
        "radius_km": 10.0,
        "vs30_min": 200.0, "vs30_max": 700.0,
        "site_class": None,  # derive from interpolated Vs30 - spans multiple classes
        "notes": "Siwalik foothills / Doon gravel fans. Stiffer and far more "
                 "variable than the valley floor, occasional rock outcrop.",
    },
    {
        "name": "Dehradun South",
        "lat": 30.2600, "lon": 77.9300,
        "radius_km": 10.0,
        "vs30_min": 180.0, "vs30_max": 400.0,
        "site_class": None,
        "notes": "Doon valley floor toward the Song/Suswa rivers - softer "
                 "alluvial fill than the northern foothills.",
    },
    {
        "name": "Bhuj",
        "lat": 23.2420, "lon": 69.6669,
        "radius_km": 20.0,
        "vs30_min": 220.0, "vs30_max": 300.0,
        "site_class": None,
        "notes": "Kutch basin fill shows no strong shallow impedance contrast, "
                 "so site response here is basin-resonance driven rather than a "
                 "sharp Vs30 boundary: HVSR studies report resonance around "
                 "0.6-1.4 Hz with amplification factors of 1.5-4.4x.",
        "resonance_hz": (0.6, 1.4),
        "amplification": (1.5, 4.4),
    },
]
