"""
Loads the IS 1893 seismic zone shapefile once, at FastAPI startup, so
get_is1893_zone() resolves zones with a point-in-polygon query instead of
touching disk (or re-parsing a shapefile) on every request.

If the shapefile is missing or fails to load, the cache stays empty and
services.inference.get_is1893_zone() falls back to the bounding-box rules
in get_is1893_zone_bbox(), tagging the result source as "approximate".
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ZONE_SHAPEFILE_PATH = Path(__file__).parent / "is1893_zones" / "is1893_zones.shp"
ZONE_FIELD = "zone"

_zones_gdf = None
_load_attempted = False


def load_zones():
    """
    Reads ZONE_SHAPEFILE_PATH into a GeoDataFrame (reprojected to WGS84) and
    caches it in-process. Safe to call more than once — later calls are a
    no-op and return the cached result.
    """
    global _zones_gdf, _load_attempted
    if _load_attempted:
        return _zones_gdf
    _load_attempted = True

    if not ZONE_SHAPEFILE_PATH.exists():
        logger.warning(
            "IS 1893 zone shapefile not found at %s — get_is1893_zone() will "
            "use the bounding-box fallback.",
            ZONE_SHAPEFILE_PATH,
        )
        return None

    try:
        import geopandas as gpd
        gdf = gpd.read_file(ZONE_SHAPEFILE_PATH)
        if gdf.crs is not None and str(gdf.crs).upper() not in ("EPSG:4326", "WGS84"):
            gdf = gdf.to_crs(epsg=4326)
        _zones_gdf = gdf
        logger.info("Loaded %d IS 1893 zone polygon(s) from %s", len(gdf), ZONE_SHAPEFILE_PATH)
    except Exception:
        logger.exception("Failed to load IS 1893 zone shapefile at %s", ZONE_SHAPEFILE_PATH)
        _zones_gdf = None

    return _zones_gdf


def get_zones() -> Optional[object]:
    """
    Returns the cached GeoDataFrame. If load_zones() hasn't run yet (e.g. a
    test or script calling get_is1893_zone() directly without going through
    the FastAPI app's startup event), loads it lazily on first call instead
    of returning None just because startup never fired — the same pattern
    services.vs30_raster.read_vs30() and services.faults.nearest_fault() use
    for their own caches, so "loader never ran" and "loader found nothing"
    both resolve to the same fallback path, not two different ones.
    """
    return _zones_gdf if _load_attempted else load_zones()
