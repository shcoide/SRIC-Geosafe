"""
Loads the GEM Global Active Faults dataset (clipped to India,
backend/data/faults_india.geojson) once, at FastAPI startup, and exposes
nearest_fault() as a precise geodesic nearest-neighbour query — never a
per-request file read.

distance_to_fault previously fed into get_bedrock_pga() as
max(5, abs(lat - 26) * 15) in routers/analyze.py — a formula with no basis
in real fault geometry, so a fabricated value was propagating into
surface_pga and the overall risk rating. nearest_fault() replaces it with
an actual distance to the nearest mapped active fault trace, computed by
projecting the query point and candidate faults to an azimuthal
equidistant CRS centred on the query point (+proj=aeqd), so degrees become
metres without the distortion a single fixed global projection would
introduce at this range.

If the dataset is missing, or no fault falls within CANDIDATE_RADIUS_DEG of
the query point, nearest_fault() returns None — never a distance computed
from anything other than real geometry.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

FAULTS_PATH = Path(__file__).parent.parent / "data" / "faults_india.geojson"
CANDIDATE_RADIUS_DEG = 3.0

_faults_gdf = None
_load_attempted = False


@dataclass
class FaultResult:
    distance_km: float
    fault_name: Optional[str]
    slip_type: Optional[str]
    net_slip_rate: Optional[str]
    source: str  # "measured" — follows the same SiteDataSource convention as get_vs30()


def load_faults():
    """Reads FAULTS_PATH into a GeoDataFrame and caches it. Safe to call more than once."""
    global _faults_gdf, _load_attempted
    if _load_attempted:
        return _faults_gdf
    _load_attempted = True

    if not FAULTS_PATH.exists():
        logger.warning(
            "Active faults dataset not found at %s — nearest_fault() will always return None.",
            FAULTS_PATH,
        )
        return None

    try:
        import geopandas as gpd
        gdf = gpd.read_file(FAULTS_PATH)
        if gdf.crs is not None and str(gdf.crs).upper() not in ("EPSG:4326", "WGS84"):
            gdf = gdf.to_crs(epsg=4326)
        _faults_gdf = gdf
        logger.info("Loaded %d active fault trace(s) from %s", len(gdf), FAULTS_PATH)
    except Exception:
        logger.exception("Failed to load active faults dataset at %s", FAULTS_PATH)
        _faults_gdf = None

    return _faults_gdf


def get_faults():
    """Returns the cached GeoDataFrame, or None if unavailable/not yet loaded."""
    return _faults_gdf


def _clean_str(value) -> Optional[str]:
    return value if isinstance(value, str) else None


def nearest_fault(lat: float, lon: float) -> Optional[FaultResult]:
    """
    Finds the nearest mapped active fault trace to (lat, lon).

    Pre-filters to a CANDIDATE_RADIUS_DEG bounding box (cheap, and sufficient
    at this scale) before projecting the point and candidates to an
    azimuthal equidistant CRS centred on the query point
    (+proj=aeqd +lat_0=<lat> +lon_0=<lon>) and measuring true geodesic
    distance in metres — plain coordinate distance is in degrees, not
    metres, and distorts badly away from the equator.

    Returns None if the dataset isn't loaded or nothing falls within range,
    rather than ever inventing a distance.
    """
    gdf = _faults_gdf if _load_attempted else load_faults()
    if gdf is None or gdf.empty:
        return None

    candidates = gdf.cx[
        lon - CANDIDATE_RADIUS_DEG: lon + CANDIDATE_RADIUS_DEG,
        lat - CANDIDATE_RADIUS_DEG: lat + CANDIDATE_RADIUS_DEG,
    ]
    if candidates.empty:
        return None

    from shapely.geometry import Point
    from shapely.ops import transform as shapely_transform
    from pyproj import Transformer

    aeqd = f"+proj=aeqd +lat_0={lat} +lon_0={lon} +units=m +ellps=WGS84"
    transformer = Transformer.from_crs("EPSG:4326", aeqd, always_xy=True)

    point_m = shapely_transform(transformer.transform, Point(lon, lat))
    distances_m = candidates.geometry.apply(
        lambda g: shapely_transform(transformer.transform, g).distance(point_m)
    )

    nearest_idx = distances_m.idxmin()
    nearest_row = candidates.loc[nearest_idx]
    distance_km = float(distances_m.loc[nearest_idx]) / 1000.0

    fault_name = _clean_str(nearest_row.get("name")) or _clean_str(nearest_row.get("fs_name"))

    return FaultResult(
        distance_km=round(distance_km, 2),
        fault_name=fault_name,
        slip_type=_clean_str(nearest_row.get("slip_type")),
        net_slip_rate=_clean_str(nearest_row.get("net_slip_rate")),
        source="measured",
    )
