#!/usr/bin/env python3
"""
Research validation tool for the /api/analyze pipeline — NOT a unit test.
Prints everything, asserts nothing. The point is to look at the numbers and
judge whether they're plausible, not to pass/fail a CI gate.

Exercises every resolution tier across the study cities:
  - Calibrated Vs30/SPT points (measured)
  - City-scale interpolation (interpolated)
  - The interpolation boundary (just outside it, and a physically nonsensical
    point over the Brahmaputra channel, to see what the model does there)
  - The other calibrated cities (Bhuj, Dehradun north/south)
  - Control cities with no calibration data at all (should bottom out at
    the regional "assumed" default)

Usage:
    python scripts/test_sites.py [--url http://localhost:8000/api/analyze]

Coordinates for the Guwahati calibrated points come straight from
backend/data/site_calibration.py. The interpolated/boundary points were
distance-checked by hand against that file's CALIBRATION_RADIUS_KM (2km)
and CITY_REGIONS radii before being hardcoded here — see the comments next
to each one.

Note: the task that requested this script said "group all 15 points" in
the recommendation-spread summary, but the point list as specified totals
16 (5 calibrated + 3 interpolated + 2 boundary + 3 other cities + 3
controls). Rather than dropping one to force 15, every summary below counts
len(POINTS) dynamically, whatever that is.
"""

import argparse
import sys
from collections import defaultdict

import httpx

DEFAULT_URL = "http://localhost:8000/api/analyze"

# (name, lat, lon, expected_bucket) — expected_bucket is a label for grouping
# the printed output and the summaries, not an assertion.
POINTS = [
    # --- GUWAHATI: calibrated (expect vs30Source "measured") ---
    # Coordinates from backend/data/site_calibration.py CALIBRATED_VS30_POINTS.
    ("Assam Zoo", 26.1517, 91.7897, "GUWAHATI calibrated"),
    ("Pan Bazaar", 26.1868, 91.7466, "GUWAHATI calibrated"),
    ("IIT Guwahati Campus", 26.1920, 91.6960, "GUWAHATI calibrated"),
    ("Maligaon", 26.1580, 91.6540, "GUWAHATI calibrated"),
    ("Dhol Gobinda", 26.0950, 91.7550, "GUWAHATI calibrated"),

    # --- GUWAHATI: interpolated (expect vs30Source "interpolated") ---
    # Real airport coordinates (LGBI Airport, Borjhar) — worth noting this is
    # ~15.6km from the Guwahati CITY_REGIONS center, i.e. right at the edge
    # of the 15km interpolation radius. Left as the real coordinate rather
    # than nudged inward to force a bucket match; if it resolves "assumed"
    # instead of "interpolated" that's a genuine, useful finding about where
    # the region radius stops reaching.
    ("Guwahati Airport (LGBI)", 26.1061, 91.5859, "GUWAHATI interpolated"),
    # City center (GS Road/Fancy Bazaar area) — 4.82km from the nearest
    # calibrated point (Assam Zoo), 0km from the Guwahati region center.
    ("Guwahati City Center", 26.1445, 91.7362, "GUWAHATI interpolated"),
    # Six Mile / Khanapara — 3.89km from the nearest calibrated point
    # (Dhol Gobinda), 7.0km from the Guwahati region center.
    ("Guwahati - Six Mile / Khanapara", 26.1180, 91.8000, "GUWAHATI interpolated"),

    # --- GUWAHATI: boundary ---
    # ~19.8km from the Guwahati region center (radius 15km) and ~27.6km from
    # Guwahati South (radius 6km) — outside both, by roughly 5km past the
    # binding constraint.
    ("Guwahati - 5km outside CITY_REGIONS", 26.2900, 91.8500, "GUWAHATI boundary"),
    # Mid-channel in the Brahmaputra, north of the city center — 2.88km from
    # the nearest calibrated point (clear of the 2km calibration radius) but
    # 7.1km from the Guwahati region center (inside the 15km interpolation
    # radius). A physically nonsensical site (open water) that the model
    # has no concept of — included to see what it does anyway.
    ("Brahmaputra River Channel", 26.2080, 91.7300, "GUWAHATI boundary"),

    # --- OTHER STUDY CITIES ---
    ("Bhuj", 23.25, 69.67, "OTHER STUDY CITIES"),
    ("Dehradun North", 30.3800, 78.0700, "OTHER STUDY CITIES"),  # CITY_REGIONS center
    ("Dehradun South", 30.2600, 77.9300, "OTHER STUDY CITIES"),  # CITY_REGIONS center

    # --- CONTROLS (expect "assumed" — no calibration data anywhere nearby) ---
    ("Kolkata", 22.57, 88.36, "CONTROLS"),
    ("Chennai", 13.08, 80.27, "CONTROLS"),
    ("Delhi", 28.61, 77.21, "CONTROLS"),
]


def fmt(value, unit=""):
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}{unit}"
    return f"{value}{unit}"


def top3_materials(materials):
    suitable = [m for m in materials if m.get("suitable")]
    suitable.sort(key=lambda m: m["rank"])
    return tuple(m["name"] for m in suitable[:3])


def print_point_result(name, bucket, data):
    print(f"\n--- {name} [{bucket}] ---")
    print(f"  seismic zone        : {data['seismicZone']} (source={data['seismicZoneSource']})")
    print(f"  vs30                : {fmt(data['vs30'], ' m/s')} (source={data['vs30Source']})")
    print(f"  site class (Vs30)   : {data['siteClassVs30']}")
    print(f"  site class (SPT-N)  : {data['siteClassSpt'] or 'not surveyed'}")
    print(f"  amplification factor: {fmt(data['amplificationFactor'], 'x')} (source={data['amplificationFactorSource']})")
    print(f"  bedrock PGA         : {fmt(data['bedrockPga'], 'g')} (source={data['bedrockPgaSource']})")
    print(f"  surface PGA         : {fmt(data['surfacePga'], 'g')}")
    if data["distanceToFault"] is None:
        print(f"  nearest fault       : none within range")
    else:
        print(
            f"  nearest fault       : {data['faultName'] or '(unnamed)'} at "
            f"{fmt(data['distanceToFault'], ' km')} (source={data['faultSource']})"
        )
    print(f"  liquefaction risk   : {data['liquefactionRisk']} (source={data['liquefactionRiskSource']})")
    print(f"  overall risk        : {data['overallRisk']}")
    print(f"  top 3 materials     : {', '.join(top3_materials(data['materials'])) or '(none)'}")


def print_summary_source_coverage(results):
    print("\n" + "=" * 70)
    print("1. SOURCE COVERAGE")
    print("=" * 70)
    source_fields = [
        "seismicZoneSource", "vs30Source", "siteClassVs30Source", "siteClassSptSource",
        "amplificationFactorSource", "bedrockPgaSource", "faultSource", "liquefactionRiskSource",
    ]
    counts = defaultdict(int)
    total = 0
    for _, _, data in results:
        for field in source_fields:
            value = data.get(field)
            counts[value if value is not None else "(null)"] += 1
            total += 1

    for value, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        pct = 100 * count / total if total else 0
        print(f"  {value:<14} {count:>4}  ({pct:5.1f}%)")
    print(f"  {'TOTAL':<14} {total:>4}")


def print_summary_vs30_spread(results):
    print("\n" + "=" * 70)
    print("2. VS30 SPREAD IN GUWAHATI (the 5 calibrated points)")
    print("=" * 70)
    calibrated_names = {"Assam Zoo", "Pan Bazaar", "IIT Guwahati Campus", "Maligaon", "Dhol Gobinda"}
    values = []
    for name, _, data in results:
        if name in calibrated_names:
            print(f"  {name:<24} vs30 = {data['vs30']} m/s")
            values.append(data["vs30"])

    distinct = sorted(set(values))
    if len(distinct) == 1:
        print(f"  WARNING: all 5 points collapsed to a single Vs30 value ({distinct[0]}) — "
              "the zone/Vs30 decoupling is not working.")
    else:
        print(f"  {len(distinct)} distinct value(s) across {len(values)} points — decoupling confirmed: {distinct}")


def print_summary_recommendation_spread(results):
    print("\n" + "=" * 70)
    print(f"3. RECOMMENDATION SPREAD (grouped across all {len(results)} points)")
    print("=" * 70)
    groups = defaultdict(list)
    for name, _, data in results:
        groups[top3_materials(data["materials"])].append(name)

    print(f"  {len(groups)} distinct top-3 recommendation set(s) across {len(results)} points:\n")
    for materials, names in groups.items():
        print(f"  {', '.join(materials) or '(none)'}")
        print(f"    -> {', '.join(names)}")

    # Specific check: do Guwahati Class E points and Class D points collapse
    # onto the same recommendation set?
    class_e_names = {"Assam Zoo", "Pan Bazaar", "Maligaon", "Dhol Gobinda"}
    class_d_names = {"Guwahati City Center", "Guwahati - Six Mile / Khanapara"}
    e_sets = {top3_materials(data["materials"]) for name, _, data in results if name in class_e_names}
    d_sets = {top3_materials(data["materials"]) for name, _, data in results if name in class_d_names}
    if e_sets and d_sets and e_sets == d_sets:
        print("\n  WARNING: Guwahati Class E points and Class D points return identical "
              "top-3 materials — site class is resolving correctly but not propagating "
              "to the recommendation.")


def print_summary_site_class_disagreement(results):
    print("\n" + "=" * 70)
    print("4. SITE CLASS DISAGREEMENT (siteClassVs30 != siteClassSpt)")
    print("=" * 70)
    found = False
    for name, bucket, data in results:
        spt = data["siteClassSpt"]
        if spt is not None and spt != data["siteClassVs30"]:
            found = True
            print(f"  {name:<24} Vs30={data['siteClassVs30']}  SPT-N={spt}")
    if not found:
        print("  none — every point with an SPT-N survey agrees with its Vs30-based class.")


def print_summary_zone_source(results):
    print("\n" + "=" * 70)
    print("5. ZONE SOURCE (shapefile vs approximate)")
    print("=" * 70)
    sources = {data["seismicZoneSource"] for _, _, data in results}
    for name, _, data in results:
        print(f"  {name:<32} {data['seismicZoneSource']}")
    if sources == {"approximate"}:
        print("\n  All points resolved via the bounding-box fallback (\"approximate\") — "
              "no IS 1893 zone shapefile is installed at backend/data/is1893_zones/.")
    elif "shapefile" in sources:
        print("\n  At least one point resolved via the real shapefile (\"shapefile\") — "
              "a zone shapefile IS installed and being used.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help=f"analyze endpoint (default: {DEFAULT_URL})")
    args = parser.parse_args()

    try:
        client = httpx.Client(timeout=30.0)
        client.get(args.url.rsplit("/api/", 1)[0] + "/health")
    except httpx.ConnectError:
        print(f"ERROR: could not reach the backend at {args.url}.")
        print("Make sure it's running: uvicorn main:app --reload --port 8000 --host 0.0.0.0")
        sys.exit(1)

    results = []
    for name, lat, lon, bucket in POINTS:
        payload = {"lat": lat, "lon": lon, "location_name": name, "floors": 3, "building_type": "residential"}
        try:
            response = client.post(args.url, json=payload)
            response.raise_for_status()
        except httpx.ConnectError:
            print(f"ERROR: lost connection to the backend while requesting {name}.")
            sys.exit(1)
        except httpx.HTTPStatusError as e:
            print(f"\n--- {name} [{bucket}] ---")
            print(f"  ERROR: {e.response.status_code} {e.response.text}")
            continue

        data = response.json()
        results.append((name, bucket, data))
        print_point_result(name, bucket, data)

    print("\n" + "=" * 70)
    print(f"Fetched {len(results)}/{len(POINTS)} points successfully.")
    print("=" * 70)

    print_summary_source_coverage(results)
    print_summary_vs30_spread(results)
    print_summary_recommendation_spread(results)
    print_summary_site_class_disagreement(results)
    print_summary_zone_source(results)


if __name__ == "__main__":
    main()
