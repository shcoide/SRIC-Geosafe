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
    """
    "OVERALL DATA QUALITY" — originally just the *Source field breakdown
    (still the bulk of this function); extended to also report how many
    points resolved a real resonance_zone (strong/moderate/none — i.e. the
    matched CITY_REGIONS entry has a measured amplificationFrequencyHz) vs.
    "indeterminate" (no measured resonant frequency there) — a second,
    independent data-quality signal alongside the *Source tiers.
    """
    print("\n" + "=" * 70)
    print("1. OVERALL DATA QUALITY")
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

    resonance_counts = defaultdict(int)
    for _, _, data in results:
        resonance_counts["real value (strong/moderate/none)" if data.get("resonanceZone") in
                          ("strong", "moderate", "none") else "indeterminate"] += 1
    resonance_total = sum(resonance_counts.values())
    print(f"\n  resonance_zone coverage (at floors=3, this run's default):")
    for label, count in sorted(resonance_counts.items(), key=lambda kv: -kv[1]):
        pct = 100 * count / resonance_total if resonance_total else 0
        print(f"    {label:<32} {count:>4}  ({pct:5.1f}%)")


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

    if len(groups) == 1:
        print("\n  NOTE: a single group here is expected, not a sign surface_sa stopped "
              "varying — get_materials() ranks suitable=True/False by RELATIVE position (top\n"
              "  two of four by collapseProbability), not an absolute cutoff, and the four "
              "typologies' fragility curves (data/fragility_curves.py) never cross rank order\n"
              "  across the Sa range these study points produce, so the same two NAMES rank "
              "suitable everywhere even though their actual collapseProbability values differ\n"
              "  substantially by site (see section 6, MATERIALS RANKING BY ZONE, below, which "
              "compares the probabilities directly rather than just the top-2 name set).")

    # Specific check: do Guwahati Class E points and Class D points collapse
    # onto the same recommendation set?
    class_e_names = {"Assam Zoo", "Pan Bazaar", "Maligaon", "Dhol Gobinda"}
    class_d_names = {"Guwahati City Center", "Guwahati - Six Mile / Khanapara"}
    e_sets = {top3_materials(data["materials"]) for name, _, data in results if name in class_e_names}
    d_sets = {top3_materials(data["materials"]) for name, _, data in results if name in class_d_names}
    if e_sets and d_sets and e_sets == d_sets:
        print("\n  NOTE: Guwahati Class E points and Class D points return identical top-3 "
              "materials. This is expected under the fragility-based ranking (get_materials(),\n"
              "  backend/services/inference.py), not a bug: surface_sa is derived from the "
              "IS 1893 design spectrum, which maps site class onto only IS 1893's own 3 soil\n"
              "  types (IS1893_SOIL_TYPE_MAP: A/B->I, C->II, D/E->III) — Class D and Class E "
              "both map to Type III and so get an identical spectral shape (and, at the same\n"
              "  zone/period, identical surface_sa and identical fragility ranking), even though "
              "they're distinct Vs30-based classes elsewhere in the app. A real limitation of\n"
              "  spectrum-driven surface_sa's resolution, distinct from the old zone-only "
              "materials function this replaced.")


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


def print_summary_materials_by_zone(results):
    """
    Confirms surface_sa (backend/routers/analyze.py) actually reaches
    get_materials()'s fragility ranking (backend/services/inference.py):
    groups every point's full materials list (rank, name, collapseProbability)
    by seismic zone, then explicitly diffs a Zone V point against a Zone II
    point. Per the task that added this: "if they're identical, surface_sa
    is not reaching the function."
    """
    print("\n" + "=" * 70)
    print("6. MATERIALS RANKING BY ZONE (fragility_sa_convolution)")
    print("=" * 70)
    by_zone = defaultdict(list)
    for name, _, data in results:
        by_zone[data["seismicZone"]].append((name, data))

    for zone in sorted(by_zone):
        name, data = by_zone[zone][0]
        print(f"\n  Zone {zone} (e.g. {name}):")
        for m in data["materials"]:
            print(
                f"    rank={m['rank']} {m['name']:<32} "
                f"collapseP={m['collapseProbability']:.2f}  suitable={m['suitable']}"
            )

    zone_v = next((data for _, data in by_zone.get("V", [])), None)
    zone_ii = next((data for _, data in by_zone.get("II", [])), None)
    if zone_v is None or zone_ii is None:
        print("\n  (need at least one Zone V and one Zone II point in POINTS to run this check)")
        return

    v_probs = tuple(m["collapseProbability"] for m in zone_v["materials"])
    ii_probs = tuple(m["collapseProbability"] for m in zone_ii["materials"])
    if v_probs == ii_probs:
        print("\n  FAIL: Zone V and Zone II collapseProbability values are identical — "
              "surface_sa is not reaching get_materials().")
    else:
        print(f"\n  PASS: Zone V collapseProbability {v_probs} != Zone II {ii_probs} — "
              "surface_sa is reaching get_materials() and driving a different ranking.")


# Only Dehradun North/South currently carry a measured amplification
# frequency (data/site_calibration.py) — they're the only two CITY_REGIONS
# points where resonance_zone can actually change with floor count. Every
# other point's amplificationFrequencyHz is null, so its resonance_zone is
# "indeterminate" at ANY floor count (get_resonance_amplification()'s first
# branch fires unconditionally when site_period is None) — no request
# needed to know that.
DEHRADUN_LOCATIONS = {
    "Dehradun North": (30.3800, 78.0700),  # amplification_frequency_hz = 3.5 (site period ~0.286s)
    "Dehradun South": (30.2600, 77.9300),  # amplification_frequency_hz = 1.25 (site period ~0.8s)
}
# floors=3 is already available from the main POINTS loop's results; these
# are just the two additional storey counts this section adds.
NEW_RESONANCE_FLOORS = (7, 12)


def _fetch_dehradun_resonance_fresh(client, url):
    """
    Fetches Dehradun North/South at NEW_RESONANCE_FLOORS (7, 12) — the two
    locations, and the only two, where resonance_zone can actually change
    with floor count (see the module-level comment above
    DEHRADUN_LOCATIONS). Shared by print_summary_resonance_by_location() and
    print_summary_resonance_by_location_and_height() so the two sections
    combined still cost only 4 new requests, not 8.
    """
    fresh = {}
    for dname, (lat, lon) in DEHRADUN_LOCATIONS.items():
        for floors in NEW_RESONANCE_FLOORS:
            payload = {"lat": lat, "lon": lon, "location_name": dname, "floors": floors, "building_type": "residential"}
            try:
                response = client.post(url, json=payload)
                response.raise_for_status()
                fresh[(dname, floors)] = response.json()
            except httpx.HTTPStatusError as e:
                print(f"  ERROR fetching {dname} at {floors} floors: {e.response.status_code} {e.response.text}")
    return fresh


def print_summary_resonance_by_location(results, fresh):
    """
    RESONANCE BY LOCATION: for every point that actually resolved inside a
    CITY_REGIONS boundary (vs30Source "measured" or "interpolated" — see
    data/site_calibration.py), shows buildingPeriodS/resonanceZone at 3, 7,
    and 12 storeys side by side.

    Takes the already-fetched Dehradun North/South floors=7/12 data
    (`fresh`, from _fetch_dehradun_resonance_fresh()) rather than fetching
    it itself — see that function's docstring for why only those two
    locations ever need a fresh request. A naive "every qualifying point x
    every new floor count" implementation would need dozens of requests and
    badly exceed POST /api/analyze's 20/minute rate limit on top of the main
    loop's 16.
    """
    print("\n" + "=" * 70)
    print("7. RESONANCE BY LOCATION (building_period_s / resonance_zone by storey count)")
    print("=" * 70)

    qualifying = [(name, data) for name, _, data in results if data.get("vs30Source") in ("measured", "interpolated")]
    if not qualifying:
        print("  (no point in POINTS resolved to a city region — nothing to show)")
        return

    period_at_floors = {
        floors: next((d["buildingPeriodS"] for (_n, f), d in fresh.items() if f == floors), None)
        for floors in NEW_RESONANCE_FLOORS
    }

    print(f"\n  {'Location':<34}{'3 storeys':<26}{'7 storeys':<26}{'12 storeys':<26}")
    for name, data in qualifying:
        cells = [f"{data['buildingPeriodS']:.3f}s / {data['resonanceZone']}"]
        for floors in NEW_RESONANCE_FLOORS:
            if (name, floors) in fresh:
                d = fresh[(name, floors)]
                cells.append(f"{d['buildingPeriodS']:.3f}s / {d['resonanceZone']}")
            elif data.get("amplificationFrequencyHz") is None:
                bp = period_at_floors.get(floors)
                bp_str = f"{bp:.3f}s" if bp is not None else "?"
                cells.append(f"{bp_str} / indeterminate")  # derived, not queried — see docstring
            else:
                cells.append("(not queried)")
        print(f"  {name:<34}" + "".join(f"{c:<26}" for c in cells))

    north_zones = {fresh[k]["resonanceZone"] for k in fresh if k[0] == "Dehradun North"}
    south_zones = {fresh[k]["resonanceZone"] for k in fresh if k[0] == "Dehradun South"}
    if north_zones and south_zones and north_zones != south_zones:
        print(f"\n  PASS: at the same storey counts (7, 12), Dehradun North {sorted(north_zones)} "
              f"and South {sorted(south_zones)} return different resonance_zone values — the "
              "north/south-west height-dependence holds beyond the floors=4/10 pair checked in "
              "earlier sessions.")
    else:
        print(f"\n  WARNING: Dehradun North ({north_zones}) and South ({south_zones}) did not "
              "diverge at 7/12 storeys as expected.")


def print_summary_fragility_ranking_by_location(results):
    """
    FRAGILITY RANKING: for every point, the top-3 ranked materials (by
    ascending collapseProbability — materials[] is already rank-ordered) and
    their collapse probability, then an explicit Zone II vs. Zone V diff —
    same spirit as print_summary_materials_by_zone() (section 6), but listing
    every location rather than one representative per zone.
    """
    print("\n" + "=" * 70)
    print("8. FRAGILITY RANKING (top-3 materials per location)")
    print("=" * 70)
    for name, _, data in results:
        top3 = data["materials"][:3]
        cells = ", ".join(f"{m['name']} ({m['collapseProbability'] * 100:.0f}%)" for m in top3)
        print(f"  {name:<32} zone {data['seismicZone']:<4} {cells}")

    zone_ii = next((data for _, _, data in results if data["seismicZone"] == "II"), None)
    zone_v = next((data for _, _, data in results if data["seismicZone"] == "V"), None)
    if zone_ii is None or zone_v is None:
        print("\n  (need at least one Zone II and one Zone V point in POINTS to run this check)")
        return
    ii_top3 = tuple(m["collapseProbability"] for m in zone_ii["materials"][:3])
    v_top3 = tuple(m["collapseProbability"] for m in zone_v["materials"][:3])
    if ii_top3 == v_top3:
        print(f"\n  FAIL: Zone II and Zone V top-3 collapseProbability values are identical {ii_top3}.")
    else:
        print(f"\n  PASS: Zone II top-3 collapseProbability {ii_top3} != Zone V {v_top3} — "
              "rankings genuinely differ between low- and high-hazard zones.")


def _surface_sa_by_zone(results):
    """One representative point's surfaceSa per IS 1893 zone present in this run (first one encountered per zone)."""
    by_zone = {}
    for name, _, data in results:
        by_zone.setdefault(data["seismicZone"], (name, data["surfaceSa"]))
    ordered_zones = [z for z in ("II", "III", "IV", "V") if z in by_zone]
    sa_values = [by_zone[z][1] for z in ordered_zones]
    is_monotonic = all(sa_values[i] <= sa_values[i + 1] for i in range(len(sa_values) - 1))
    return by_zone, ordered_zones, sa_values, is_monotonic


def print_summary_surface_sa_by_zone(results, section="9"):
    """
    SURFACE SA BY ZONE: one representative point's surfaceSa per IS 1893
    zone present in this run, checked for monotonic increase from Zone II
    to Zone V — surfaceSa = ZONE_PGA[zone] * (design spectrum's Sa/g), so
    the zone factor alone should dominate the ordering even though the
    Sa/g term also varies (slightly) by site class/period.
    """
    print("\n" + "=" * 70)
    print(f"{section}. SURFACE SA BY ZONE")
    print("=" * 70)
    by_zone, ordered_zones, sa_values, is_monotonic = _surface_sa_by_zone(results)

    for zone in sorted(by_zone):
        name, sa = by_zone[zone]
        print(f"  Zone {zone:<4} surfaceSa={sa:.3f}g   (e.g. {name})")

    pairs = list(zip(ordered_zones, sa_values))
    if is_monotonic:
        print(f"\n  PASS: surfaceSa increases monotonically from Zone II to Zone V: {pairs}")
    else:
        print(f"\n  WARNING: surfaceSa is NOT monotonic across zones: {pairs}")


# Chennai (Zone II) and the calibrated "Assam Zoo" point (Zone V, already in
# POINTS) are the two locations the band-tolerance-plus-cost rework was
# specifically verified against — see backend/tests/test_fragility.py.
BUDGET_VERIFICATION_LOCATIONS = {
    "Chennai": (13.08, 80.27),
    "Guwahati (Assam Zoo)": (26.1517, 91.7897),
}


def _fetch_budget_preference_fresh(client, url, budget_preference):
    """Fetches BUDGET_VERIFICATION_LOCATIONS (Chennai, Guwahati/Assam Zoo) at floors=3 for one budget_preference value. Returns {label: response_json}."""
    fresh = {}
    for label, (lat, lon) in BUDGET_VERIFICATION_LOCATIONS.items():
        payload = {
            "lat": lat, "lon": lon, "location_name": label,
            "floors": 3, "building_type": "residential", "budget_preference": budget_preference,
        }
        try:
            response = client.post(url, json=payload)
            response.raise_for_status()
            fresh[label] = response.json()
        except httpx.HTTPStatusError as e:
            print(f"  ERROR fetching {label} (budget={budget_preference}): {e.response.status_code} {e.response.text}")
    return fresh


def print_summary_budget_preference(results, low_fresh):
    """
    BUDGET PREFERENCE: confirms the three claims the band-tolerance-plus-cost
    rewrite of get_materials() was verified against (see
    backend/data/fragility_curves.py's and backend/services/inference.py's
    comments on why relative_cost and BAND_TOLERANCE_BY_BUDGET ended up with
    the values they have):
      - Guwahati (Zone V), budget=any -> RC moment frame and light gauge
        steel both suitable.
      - Chennai (Zone II), budget=low -> confined masonry suitable (it was
        always marked "avoid" under the old fixed-top-two rule, despite a
        ~9% collapse probability, purely because it ranked 3rd).
      - Guwahati (Zone V), budget=low -> light gauge steel still suitable.

    Guwahati+any is read straight off the main POINTS loop's "Assam Zoo"
    result (default budget_preference) rather than re-queried. `low_fresh`
    (from _fetch_budget_preference_fresh(client, url, "low")) supplies the
    two budget=low points — fetched once in main() and shared with section
    12 (MATERIAL RANKING BY BUDGET AND ZONE) rather than re-fetched here.
    """
    print("\n" + "=" * 70)
    print("10. BUDGET PREFERENCE (band-tolerance cost sensitivity)")
    print("=" * 70)

    guwahati_any = next((data for name, _, data in results if name == "Assam Zoo"), None)
    fresh = low_fresh

    def suitable_names(data):
        return sorted(m["name"] for m in data["materials"] if m["suitable"])

    checks = []
    if guwahati_any:
        names = suitable_names(guwahati_any)
        print(f"  Guwahati (Assam Zoo), Zone V, budget=any -> suitable: {names}")
        checks.append((
            "Guwahati Zone V + any: RC moment frame and light gauge steel suitable",
            {"RC moment frame with shear walls", "Light gauge steel frame"} <= set(names),
        ))

    chennai_low = fresh.get("Chennai")
    if chennai_low:
        names = suitable_names(chennai_low)
        print(f"  Chennai, Zone II, budget=low             -> suitable: {names}")
        checks.append(("Chennai Zone II + low: confined masonry suitable", "Confined masonry" in names))

    guwahati_low = fresh.get("Guwahati (Assam Zoo)")
    if guwahati_low:
        names = suitable_names(guwahati_low)
        print(f"  Guwahati (Assam Zoo), Zone V, budget=low -> suitable: {names}")
        checks.append(("Guwahati Zone V + low: light gauge steel suitable", "Light gauge steel frame" in names))

    print()
    for label, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}: {label}")


# --- Sections 11-14: added to re-verify the same claims sections 6-10 above
# already cover, at the exact locations/values a later review round asked
# for by name. Kept as separate, explicitly-numbered sections (rather than
# folded into 6-10) since that's what was asked for, even though the
# underlying data mostly overlaps — each reuses already-fetched results or
# an already-fetched `fresh` dict rather than re-querying wherever possible.

def print_summary_resonance_by_location_and_height(results, dehradun_fresh):
    """
    RESONANCE BY LOCATION AND HEIGHT: building_period_s / resonance_zone at
    floors=3/7/12 for exactly four named locations — Dehradun North,
    Dehradun South, Guwahati, and Bhuj — plus explicit checks that (a)
    Dehradun North and South differ at the same storey count, and (b)
    Guwahati and Bhuj (both "indeterminate" — neither has a measured
    amplification frequency) differ from both Dehradun sectors' real
    classifications. A narrower, differently-organized view of the same
    data section 7 (RESONANCE BY LOCATION) already presents for every
    city-region point, not just these four.
    """
    print("\n" + "=" * 70)
    print("11. RESONANCE BY LOCATION AND HEIGHT")
    print("=" * 70)

    period_at_floors = {
        floors: next((d["buildingPeriodS"] for (_n, f), d in dehradun_fresh.items() if f == floors), None)
        for floors in NEW_RESONANCE_FLOORS
    }
    guwahati = next((data for name, _, data in results if name == "Assam Zoo"), None)
    bhuj = next((data for name, _, data in results if name == "Bhuj"), None)

    rows = {}
    for dname in DEHRADUN_LOCATIONS:
        source = next((data for name, _, data in results if name == dname), None)
        cells = {3: (source["buildingPeriodS"], source["resonanceZone"]) if source else (None, None)}
        for floors in NEW_RESONANCE_FLOORS:
            d = dehradun_fresh.get((dname, floors))
            cells[floors] = (d["buildingPeriodS"], d["resonanceZone"]) if d else (None, None)
        rows[dname] = cells

    for label, data in (("Guwahati (Assam Zoo)", guwahati), ("Bhuj", bhuj)):
        cells = {3: (data["buildingPeriodS"], data["resonanceZone"]) if data else (None, None)}
        for floors in NEW_RESONANCE_FLOORS:
            bp = period_at_floors.get(floors)
            # Derived, not queried: amplificationFrequencyHz is null for both
            # locations, so resonance_zone is deterministically "indeterminate"
            # at any floor count (get_resonance_amplification()'s first branch).
            cells[floors] = (bp, "indeterminate")
        rows[label] = cells

    print(f"\n  {'Location':<26}{'3 storeys':<24}{'7 storeys':<24}{'12 storeys':<24}")
    for label in ("Dehradun North", "Dehradun South", "Guwahati (Assam Zoo)", "Bhuj"):
        cells = rows[label]
        formatted = []
        for floors in (3, *NEW_RESONANCE_FLOORS):
            bp, zone = cells[floors]
            formatted.append(f"{bp:.3f}s / {zone}" if bp is not None else "?")
        print(f"  {label:<26}" + "".join(f"{c:<24}" for c in formatted))

    print()
    for floors in (3, *NEW_RESONANCE_FLOORS):
        north_zone = rows["Dehradun North"][floors][1]
        south_zone = rows["Dehradun South"][floors][1]
        ok = north_zone is not None and south_zone is not None and north_zone != south_zone
        print(f"  {'PASS' if ok else 'FAIL'}: floors={floors}: Dehradun North ({north_zone}) != Dehradun South ({south_zone})")

    for floors in (3, *NEW_RESONANCE_FLOORS):
        north_zone = rows["Dehradun North"][floors][1]
        south_zone = rows["Dehradun South"][floors][1]
        for label in ("Guwahati (Assam Zoo)", "Bhuj"):
            other_zone = rows[label][floors][1]
            ok = other_zone not in (north_zone, south_zone)
            print(f"  {'PASS' if ok else 'FAIL'}: floors={floors}: {label} ({other_zone}) differs from both Dehradun sectors ({north_zone}, {south_zone})")


BUDGET_MATERIAL_ZONE_LOCATIONS = {
    "Guwahati (Assam Zoo)": (26.1517, 91.7897),
    "Chennai": (13.08, 80.27),
}
# The main POINTS loop's location_name for each display label above differs
# for Guwahati ("Assam Zoo", not "Guwahati (Assam Zoo)") — needed to look
# its "any"-budget result up in `results` without re-querying.
POINTS_NAME_FOR_BUDGET_LOCATION = {
    "Guwahati (Assam Zoo)": "Assam Zoo",
    "Chennai": "Chennai",
}


def print_summary_material_ranking_by_budget_and_zone(results, low_fresh, moderate_fresh):
    """
    MATERIAL RANKING BY BUDGET AND ZONE: Guwahati (Zone V) and Chennai
    (Zone II) at all three budget_preference values, with the suitable/avoid
    split and every typology's collapseProbability. "any" is read from the
    main POINTS loop's results (the default); "low" from `low_fresh`
    (section 10's fetch); only "moderate" needed a genuinely new request per
    location — 2 total, made by main() and passed in here.
    """
    print("\n" + "=" * 70)
    print("12. MATERIAL RANKING BY BUDGET AND ZONE")
    print("=" * 70)

    any_by_label = {}
    for label, points_name in POINTS_NAME_FOR_BUDGET_LOCATION.items():
        data = next((data for name, _, data in results if name == points_name), None)
        if data is not None:
            any_by_label[label] = data

    checks = []
    for label in BUDGET_MATERIAL_ZONE_LOCATIONS:
        print(f"\n  {label}:")
        for budget, source in (("any", any_by_label), ("low", low_fresh), ("moderate", moderate_fresh)):
            data = source.get(label)
            if data is None:
                print(f"    budget={budget:<9} (no data)")
                continue
            suitable = sorted(m["name"] for m in data["materials"] if m["suitable"])
            avoid = sorted(m["name"] for m in data["materials"] if not m["suitable"])
            probs = ", ".join(f"{m['name']}={m['collapseProbability']:.2f}" for m in data["materials"])
            print(f"    budget={budget:<9} suitable={suitable}")
            print(f"    {'':<18} avoid={avoid}")
            print(f"    {'':<18} collapseProbability: {probs}")

            if label == "Chennai" and budget == "low":
                checks.append(("Chennai + low: confined masonry suitable", "Confined masonry" in suitable))
            if label == "Guwahati (Assam Zoo)" and budget == "any":
                checks.append(("Guwahati + any: RC moment frame suitable", "RC moment frame with shear walls" in suitable))

    print()
    for label, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}: {label}")


def print_summary_data_source_coverage(results):
    """
    DATA SOURCE COVERAGE: the provenance audit — how many of the (up to 16)
    fetched points resolved Vs30 from each source tier, and seismic zone
    from each source tier. A narrower, two-field view of what section 1
    (OVERALL DATA QUALITY) already reports across every *Source field.
    """
    print("\n" + "=" * 70)
    print("14. DATA SOURCE COVERAGE (provenance audit)")
    print("=" * 70)
    total = len(results)

    vs30_counts = defaultdict(int)
    zone_counts = defaultdict(int)
    for _, _, data in results:
        vs30_counts[data["vs30Source"]] += 1
        zone_counts[data["seismicZoneSource"]] += 1

    print(f"\n  Vs30 source across {total} points:")
    for source in ("measured", "interpolated", "modeled", "assumed"):
        count = vs30_counts.get(source, 0)
        pct = 100 * count / total if total else 0
        print(f"    {source:<14} {count:>2}/{total}  ({pct:5.1f}%)")

    print(f"\n  Seismic zone source across {total} points:")
    for source in ("shapefile", "approximate"):
        count = zone_counts.get(source, 0)
        pct = 100 * count / total if total else 0
        print(f"    {source:<14} {count:>2}/{total}  ({pct:5.1f}%)")

    real_vs30 = vs30_counts.get("measured", 0) + vs30_counts.get("interpolated", 0)
    real_pct = 100 * real_vs30 / total if total else 0
    print(f"\n  {real_pct:.1f}% of points resolved Vs30 from real calibrated/interpolated survey "
          f"data ({real_vs30}/{total}); the rest fell back to the modeled raster or a regional default.")


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

    dehradun_fresh = _fetch_dehradun_resonance_fresh(client, args.url)
    budget_low_fresh = _fetch_budget_preference_fresh(client, args.url, "low")
    budget_moderate_fresh = _fetch_budget_preference_fresh(client, args.url, "moderate")

    print_summary_source_coverage(results)
    print_summary_vs30_spread(results)
    print_summary_recommendation_spread(results)
    print_summary_site_class_disagreement(results)
    print_summary_zone_source(results)
    print_summary_materials_by_zone(results)
    print_summary_resonance_by_location(results, dehradun_fresh)
    print_summary_fragility_ranking_by_location(results)
    print_summary_surface_sa_by_zone(results)
    print_summary_budget_preference(results, budget_low_fresh)
    print_summary_resonance_by_location_and_height(results, dehradun_fresh)
    print_summary_material_ranking_by_budget_and_zone(results, budget_low_fresh, budget_moderate_fresh)
    print_summary_surface_sa_by_zone(results, section="13")
    print_summary_data_source_coverage(results)


if __name__ == "__main__":
    main()
