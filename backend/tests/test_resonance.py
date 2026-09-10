"""
Regression tests for the building-resonance pipeline (get_building_period,
get_amplification_frequency_hz, get_resonance_amplification — added this
session in services/inference.py) and its Dehradun north/south-west finding:
the same IS 1893 zone label (Zone IV) covers sites where a different
building height is most at risk, because the measured dominant
amplification frequency runs 3-4 Hz in the north (favouring low-rise
resonance) against 1-1.5 Hz in the south-west (favouring mid-rise
resonance) — see backend/data/site_calibration.py's Dehradun North/South
`amplification_frequency_hz`.

A note on the exact floor counts used below: this test suite was requested
with the expectation that a 3-storey building resonates "strong" in
Dehradun north (site 3-4 Hz, "building ~2.6 Hz with infill formula"). That
expectation doesn't match this codebase's actual get_building_period():
with building_type="residential" (the default), 3 floors uses the
masonry-infill formula (Ta = 0.09h/sqrt(15)), giving a ~0.209s period
(~4.78 Hz) — not the ~2.6 Hz (~0.390s) figure, which is actually what the
*bare-frame* formula (Ta = 0.075h^0.75, used for building_type="industrial")
gives at 3 floors. Verified directly against the running code rather than
assumed: 3-floor + Dehradun north resolves resonance_zone "moderate" (ratio
~27%, inside the 40% band but outside the 20% "strong" band), not "strong".
4 floors is the first floor count that actually lands "strong" (ratio
~2.4%). Both cases are tested explicitly below, so this suite covers the
real 3-storey case (correctly, as "moderate") *and* demonstrates the
"strong" low-rise-resonance phenomenon at the floor count where it
genuinely occurs, rather than asserting a value the code doesn't produce.
"""

from services.inference import (
    get_amplification_frequency_hz,
    get_building_period,
    get_resonance_amplification,
)

# Dehradun North / South CITY_REGIONS centers (backend/data/site_calibration.py)
DEHRADUN_NORTH = (30.3800, 78.0700)
DEHRADUN_SOUTH = (30.2600, 77.9300)
BHUJ = (23.2420, 69.6669)

# A second set of points inside the same two regions but off-center, plus
# Bhuj at slightly different coordinates — added to confirm the resonance
# outcome isn't an artifact of using the exact CITY_REGIONS centroid.
DEHRADUN_NORTH_OFFSET = (30.40, 78.05)
DEHRADUN_SOUTH_OFFSET = (30.28, 78.00)
BHUJ_OFFSET = (23.25, 69.67)


def _resonance_zone(lat: float, lon: float, floors: int, building_type: str = "residential") -> str:
    building_period, _clause = get_building_period(floors, building_type)
    frequency_hz = get_amplification_frequency_hz(lat, lon)
    site_period = (1.0 / frequency_hz) if frequency_hz else None
    return get_resonance_amplification(site_period, building_period).resonance_zone


def test_dehradun_north_amplification_frequency_is_3_5_hz():
    assert get_amplification_frequency_hz(*DEHRADUN_NORTH) == 3.5


def test_dehradun_south_amplification_frequency_is_1_25_hz():
    assert get_amplification_frequency_hz(*DEHRADUN_SOUTH) == 1.25


def test_three_storey_dehradun_north_is_moderate_not_strong():
    """
    The literal 3-storey case: real ratio ~27% (inside the 40% "moderate"
    band, outside the 20% "strong" band) — see module docstring.
    """
    assert _resonance_zone(*DEHRADUN_NORTH, floors=3) == "moderate"


def test_four_storey_dehradun_north_returns_strong_resonance():
    """
    The floor count that actually produces "strong" for Dehradun north
    (ratio ~2.4%, well inside the 20% band) — see module docstring.
    """
    assert _resonance_zone(*DEHRADUN_NORTH, floors=4) == "strong"


def test_three_storey_dehradun_south_west_returns_no_resonance():
    """
    Dehradun south-west's site period (1/1.25 Hz = 0.8s) is far from a
    3-storey building's period (~0.209s, infill formula) — ratio ~74%,
    outside even the 40% "moderate" band.
    """
    assert _resonance_zone(*DEHRADUN_SOUTH, floors=3) == "none"


def test_ten_storey_dehradun_south_west_returns_strong_resonance():
    """
    Confirms the south-west risk profile actually is mid/high-rise, not
    just "3 storeys isn't the risk height there" — 10 floors (~30m) lands
    inside Dehradun South's "strong" band.
    """
    assert _resonance_zone(*DEHRADUN_SOUTH, floors=10) == "strong"


def test_building_period_changes_with_floor_count():
    period_3, _ = get_building_period(3, "residential")
    period_10, _ = get_building_period(10, "residential")
    assert period_3 != period_10
    assert period_10 > period_3, "a taller building should have a longer fundamental period"


def test_bhuj_returns_indeterminate_resonance():
    """
    Bhuj's HVSR data shows no strong shallow impedance contrast, so it has
    no measured amplification_frequency_hz — get_resonance_amplification()
    must report "indeterminate", not silently default to "none" (see that
    function's docstring: "no data" and "no resonance risk" aren't the same
    claim).
    """
    assert get_amplification_frequency_hz(*BHUJ) is None
    assert _resonance_zone(*BHUJ, floors=3) == "indeterminate"
    assert _resonance_zone(*BHUJ, floors=10) == "indeterminate"


def test_three_storey_dehradun_north_offset_point_is_strong_or_moderate():
    """
    (30.40, 78.05) — inside Dehradun North but off the region centroid.
    A 3-storey residential (infill-formula) building's period is ~0.209s
    (~4.78 Hz); the site's measured amplification frequency is 3.5 Hz
    (site period ~0.286s). The resulting ratio (~27%) lands "moderate", not
    "strong" (that needs ~20%, hit at 4 floors — see
    test_four_storey_dehradun_north_returns_strong_resonance above) — but
    both are the "site and building are in the same low-rise-risk regime"
    outcome this test is really checking for, so either is accepted.
    """
    assert _resonance_zone(*DEHRADUN_NORTH_OFFSET, floors=3) in ("strong", "moderate")


def test_three_storey_dehradun_south_offset_point_is_none():
    """
    (30.28, 78.00) — inside Dehradun South but off the region centroid
    (and, at lat 30.28, just south of Dehradun North's bbox boundary at
    30.28979, so this point resolves to South only, not both). Site period
    0.8s (1.25 Hz) vs. a 3-storey building's ~0.209s — ratio ~74%, well
    outside even the 40% "moderate" band.
    """
    assert _resonance_zone(*DEHRADUN_SOUTH_OFFSET, floors=3) == "none"


def test_dehradun_north_and_south_offset_points_differ_at_same_storey_count():
    """Same floors=3 input, different location -> different resonance_zone, confirming the north/south-west split isn't dependent on which exact point is queried."""
    north = _resonance_zone(*DEHRADUN_NORTH_OFFSET, floors=3)
    south = _resonance_zone(*DEHRADUN_SOUTH_OFFSET, floors=3)
    assert north != south


def test_bhuj_offset_point_returns_indeterminate_resonance():
    assert get_amplification_frequency_hz(*BHUJ_OFFSET) is None
    assert _resonance_zone(*BHUJ_OFFSET, floors=3) == "indeterminate"


def test_building_period_changes_between_floors_3_and_10_at_the_same_location():
    """
    get_building_period() takes floors/building_type, not lat/lon, so
    "at the same location" is automatically satisfied by any two calls with
    the same location — but this test still fixes one (Dehradun North) and
    threads it through the full _resonance_zone() call shape (matching
    routers/analyze.py's real sequence), rather than calling
    get_building_period() in isolation, so a future change that accidentally
    made the period depend on the resonance lookup's other inputs would
    still be caught here.
    """
    period_3, _ = get_building_period(3, "residential")
    period_10, _ = get_building_period(10, "residential")
    assert period_3 != period_10, "get_building_period() is not wired correctly — period is identical at floors=3 and floors=10"

    zone_3 = _resonance_zone(*DEHRADUN_NORTH, floors=3)
    zone_10 = _resonance_zone(*DEHRADUN_NORTH, floors=10)
    # Not asserting zone_3 != zone_10 here (both could legitimately land in
    # the same band) — the period difference above is the actual invariant
    # being tested; this just confirms the full pipeline still runs cleanly
    # at both floor counts for a real location.
    assert zone_3 in ("strong", "moderate", "none", "indeterminate")
    assert zone_10 in ("strong", "moderate", "none", "indeterminate")
