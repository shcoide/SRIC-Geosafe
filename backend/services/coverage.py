"""
Coverage geometry derived from data/site_calibration.py — the single
source of truth for calibration data. Nothing here re-guesses or
duplicates that data; it only projects it into shapes an API/UI can use
(bounds, boundary outlines, point-in-region membership) and reports which
resolution tier get_vs30() would actually use at a given point.

This exists because the app currently gives no indication of where its
answers come from real calibration versus a regional guess — every result
looks equally confident. /api/coverage and /api/coverage/check expose that
distinction so the UI can show it.

Containment now goes through data.site_calibration.find_containing_region()
(a real shapely geometry test against each region's declared bbox/polygon,
with an explicit most-specific-region-wins precedence for the rare case
where two regions' declared geometries overlap — see
check_region_overlaps()), not a haversine-radius test — regions are no
longer modelled as circles.
"""

import re
from typing import Optional, Tuple

from data.site_calibration import (
    CALIBRATED_SPT_POINTS,
    CALIBRATED_VS30_POINTS,
    CALIBRATION_RADIUS_KM,
    CITY_REGIONS,
    find_containing_region,
    haversine_km,
    region_bounds,
    region_boundary_vertices,
)
from services.inference import get_is1893_zone, get_vs30


def region_id(name: str) -> str:
    """Stable slug derived from a CITY_REGIONS name, e.g. 'Guwahati South' -> 'guwahati-south'."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def find_region_for_point(lat: float, lon: float) -> Tuple[Optional[dict], Optional[float]]:
    """CITY_REGION whose declared geometry actually contains (lat, lon) — same containment
    test and most-specific-region-wins precedence as get_vs30()'s internal city-region
    matching (both go through data.site_calibration.find_containing_region()), so /coverage
    and /coverage/check never disagree with each other or with the actual resolution logic."""
    region = find_containing_region(lat, lon)
    if region is None:
        return None, None
    return region, haversine_km(lat, lon, region["lat"], region["lon"])


def _calibrated_points_in_region(region: dict) -> list:
    """Calibrated Vs30 points whose nearest matching region (by the same tie-break) is this one."""
    points = []
    for (plat, plon), point in CALIBRATED_VS30_POINTS.items():
        matched_region, _ = find_region_for_point(plat, plon)
        if matched_region is region:
            points.append((plat, plon, point))
    return points


def _region_summary(region: dict) -> dict:
    points = _calibrated_points_in_region(region)
    calibrated_points = [
        {
            "name": point["name"],
            "lat": plat,
            "lon": plon,
            "radiusKm": CALIBRATION_RADIUS_KM,
            "hasSptData": (plat, plon) in CALIBRATED_SPT_POINTS,
        }
        for plat, plon, point in points
    ]
    spt_count = sum(1 for p in calibrated_points if p["hasSptData"])
    zone_result = get_is1893_zone(region["lat"], region["lon"])

    return {
        "id": region_id(region["name"]),
        "name": region["name"],
        "state": region.get("state", ""),
        "seismicZone": zone_result.zone,
        "center": {"lat": region["lat"], "lon": region["lon"]},
        "bounds": region_bounds(region),
        "boundary": region_boundary_vertices(region),
        "geometrySource": region.get("geometrySource", "provisional_bbox"),
        "calibratedPoints": calibrated_points,
        "counts": {"calibratedPoints": len(calibrated_points), "withSptData": spt_count},
        "dataQuality": "calibrated" if calibrated_points else "regional",
        "notes": region.get("notes", ""),
    }


def build_coverage_list() -> list:
    return [_region_summary(region) for region in CITY_REGIONS]


def check_coverage(lat: float, lon: float) -> dict:
    """
    inCoverage/expectedVs30Source come straight from get_vs30() — the same
    function the real /api/analyze pipeline uses — so this can never drift
    from what a full analysis would actually resolve to, and it stays cheap
    enough for live use (calibrated-point/city-region lookups are dict/list
    scans, no network calls, no USGS, no full analysis).
    """
    matched_region, _ = find_region_for_point(lat, lon)
    vs30_result = get_vs30(lat, lon)
    in_coverage = vs30_result.source in ("measured", "interpolated")

    result = {
        "inCoverage": in_coverage,
        "regionId": region_id(matched_region["name"]) if matched_region else None,
        "regionName": matched_region["name"] if matched_region else None,
        "expectedVs30Source": vs30_result.source,
        "nearestRegion": None,
    }

    if not in_coverage:
        nearest, nearest_dist = None, None
        for region in CITY_REGIONS:
            dist = haversine_km(lat, lon, region["lat"], region["lon"])
            if nearest_dist is None or dist < nearest_dist:
                nearest, nearest_dist = region, dist
        if nearest is not None:
            result["nearestRegion"] = {
                "id": region_id(nearest["name"]),
                "name": nearest["name"],
                "distanceKm": round(nearest_dist, 2),
                "center": {"lat": nearest["lat"], "lon": nearest["lon"]},
            }

    return result
