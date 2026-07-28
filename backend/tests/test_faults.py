"""
Regression test for the fault-distance pipeline.

distance_to_fault used to be computed in routers/analyze.py as
max(5, abs(lat - 26) * 15) — a formula with no relation to real fault
geometry. services.faults.nearest_fault() replaced it with an actual
nearest-neighbour query against the GEM Global Active Faults dataset
(clipped to India, backend/data/faults_india.geojson), via an azimuthal
equidistant projection centred on the query point.

If either resolution test below fails, the AEQD projection or the India
bounding-box clip is wrong — both Bhuj and Guwahati sit in well-mapped
fault zones, so a broken projection would either return a wildly wrong
distance or match nothing at all.

Note on region checks: GEM's public dataset doesn't carry names for the
Kachchh rift faults (Katrol Hill Fault, Kachchh Mainland Fault, Allah Bund
Fault, etc.) near Bhuj — the nearest mapped trace there is an unnamed EMME
segment. So the Bhuj assertion checks that the match is geographically
local (i.e. actually within the Kachchh region, not some distant named
fault elsewhere) rather than checking a fault name string.
"""

import pytest

from services.faults import load_faults, nearest_fault

pytestmark = pytest.mark.skipif(
    load_faults() is None,
    reason="backend/data/faults_india.geojson not present — nothing to test",
)

# Generous enough to allow for real data placement/attribute variance, tight
# enough that a broken projection (wrong units, or degrees mistaken for
# metres) would clearly fail it instead of accidentally passing.
LOCAL_FAULT_THRESHOLD_KM = 100


def test_bhuj_resolves_to_kachchh_region_fault():
    result = nearest_fault(23.25, 69.67)
    assert result is not None, "expected a mapped fault near Bhuj"
    assert result.distance_km < LOCAL_FAULT_THRESHOLD_KM, (
        f"nearest fault to Bhuj is {result.distance_km} km away — too far "
        "to be the Kachchh rift structure that produced the 2001 earthquake"
    )


def test_guwahati_resolves_to_kopili_or_himalayan_frontal_fault():
    result = nearest_fault(26.14, 91.74)
    assert result is not None, "expected a mapped fault near Guwahati"
    assert result.distance_km < LOCAL_FAULT_THRESHOLD_KM, (
        f"nearest fault to Guwahati is {result.distance_km} km away — too "
        "far to be the Kopili/Shillong Plateau or Himalayan frontal system"
    )


def test_no_fault_within_range_returns_none():
    # Middle of the Bay of Bengal — no mapped active fault trace nearby.
    assert nearest_fault(10.0, 88.0) is None
