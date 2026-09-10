"""
Regression tests for the fragility-based material ranking added this
session: data/fragility_curves.py's compute_damage_probability() and
TYPOLOGIES, and services/inference.py's get_materials().

A note on compute_damage_probability(0.0, 0.10, 0.60): this suite was
requested with the expectation that this call returns ~0.50, "by
definition of median". That's true of Sa *equal to* the median capacity
(P(DS>=ds | Sa=median) = 0.50 is exactly what the lognormal fragility
function gives at Sa=median) — but 0.0 is not the median here, 0.10 is.
compute_damage_probability(0.0, 0.10, 0.60) hits the function's explicit
sa_g <= 0 guard (documented in fragility_curves.py: "no physical scenario
where zero or negative shaking causes nonzero damage probability") and
returns 0.0, not 0.50. Verified directly against the running code. Both
cases are tested explicitly below: the actual "at the median" case
(compute_damage_probability(0.10, 0.10, 0.60) == 0.50) and the zero-Sa edge
case (== 0.0), rather than asserting a value the function doesn't produce
for the literal call given.

get_materials() itself has gone through three suitability rules across this
session: an absolute P(DS>=DS4) > 0.30 cutoff (returned zero suitable
typologies at every Zone V site), a fixed top-half/bottom-half split (always
promoted the same two typology *names* regardless of zone, since their
fragility curves never cross rank order — a cheap, adequate typology like
confined masonry was marked "avoid" purely by rank position, not because it
was actually unsafe), and now a band-tolerance-plus-cost rule (this file's
current version). Two numeric choices behind that final version were
verified computationally before shipping, not assumed:
  - `relative_cost` for rc_moment_frame/light_gauge_steel had to be swapped
    from an initial 4/3 to the current 3/4 — at 4/3, light gauge steel was
    both cheaper AND always had a lower collapse probability than RC moment
    frame (same beta, higher ds4_median_sa), so RC moment frame could never
    win the "cheaper or equal" cost check at any Sa or tolerance — it would
    never be suitable regardless of anything else. See
    data/fragility_curves.py's own comment on this.
  - BAND_TOLERANCE_BY_BUDGET's "low"/"any" mapping is the WIDEST tolerance
    for "low" budget and the NARROWEST for "any" (no budget preference) —
    the opposite of a literal reading of "low -> tighten the tolerance,"
    because tightening it actually *reduces* how much room a cheaper
    alternative has to qualify, which is backwards from what a
    budget-conscious user would want. See
    services/inference.py's BAND_TOLERANCE_BY_BUDGET comment.
"""

from data.fragility_curves import TYPOLOGIES, compute_damage_probability
from services.inference import get_materials

URM_NAME = TYPOLOGIES["unreinforced_masonry"]["name"]
CONFINED_NAME = TYPOLOGIES["confined_masonry"]["name"]
RC_FRAME_NAME = TYPOLOGIES["rc_moment_frame"]["name"]
LIGHT_GAUGE_NAME = TYPOLOGIES["light_gauge_steel"]["name"]

# Illustrative surface_sa values standing in for a low-hazard (~Zone II) and
# high-hazard (~Zone V) site — these are direct arguments to get_materials()
# / compute_damage_probability(), not run through the full zone -> surface_sa
# pipeline in routers/analyze.py (see that file for the real derivation).
ZONE_II_SA = 0.05
ZONE_V_SA = 0.36
# The actual live surface_sa values routers/analyze.py produces for Chennai
# (Zone II) and Guwahati (Zone V) at floors=3/residential — see
# scripts/test_sites.py's SURFACE SA BY ZONE section. Used for the
# band-tolerance-plus-cost tests below since (unlike the two constants
# above) those need the real cross-typology probability gaps, not just "a
# low value" / "a high value".
CHENNAI_ZONE_II_SA = 0.25
GUWAHATI_ZONE_V_SA = 0.90


def _suitable_names(materials):
    return {m["name"] for m in materials if m["suitable"]}


def test_damage_probability_at_zero_sa_is_zero_not_median():
    """The sa_g <= 0 guard, not the median-crossing case — see module docstring."""
    assert compute_damage_probability(0.0, 0.10, 0.60) == 0.0


def test_damage_probability_at_the_median_is_approximately_half():
    """P(DS>=ds | Sa=median) = 0.50 by construction of the lognormal fragility function."""
    p = compute_damage_probability(0.10, 0.10, 0.60)
    assert abs(p - 0.50) < 1e-9


def test_unreinforced_masonry_ranks_last_at_high_sa():
    materials = get_materials(ZONE_V_SA)
    assert materials[-1]["name"] == URM_NAME
    assert materials[-1]["rank"] == len(materials)
    # Every other typology's collapse probability should be lower than URM's.
    urm_probability = materials[-1]["collapseProbability"]
    for m in materials[:-1]:
        assert m["collapseProbability"] <= urm_probability


def test_rankings_differ_between_zone_ii_and_zone_v_sa():
    low_sa_materials = get_materials(ZONE_II_SA)
    high_sa_materials = get_materials(ZONE_V_SA)

    low_sa_probabilities = tuple(m["collapseProbability"] for m in low_sa_materials)
    high_sa_probabilities = tuple(m["collapseProbability"] for m in high_sa_materials)
    assert low_sa_probabilities != high_sa_probabilities, (
        "collapseProbability is identical between a Zone II-like and Zone V-like "
        "surface_sa — get_materials() is not actually using surface_sa"
    )

    # Every typology's collapse probability should increase (or stay equal, at the
    # rounding floor) as surface_sa rises from the Zone II-like to Zone V-like value.
    low_by_name = {m["name"]: m["collapseProbability"] for m in low_sa_materials}
    high_by_name = {m["name"]: m["collapseProbability"] for m in high_sa_materials}
    for name in low_by_name:
        assert high_by_name[name] >= low_by_name[name], (
            f"{name}: collapseProbability decreased ({low_by_name[name]} -> "
            f"{high_by_name[name]}) as surface_sa increased — expected non-decreasing"
        )


def test_lowest_probability_typology_is_always_suitable():
    """
    The one invariant the band-tolerance-plus-cost rule guarantees regardless
    of surface_sa or budget_preference: rank 1 (lowest collapseProbability)
    is always suitable — see get_materials()'s docstring, point (d) of the
    original band-tolerance spec ("always ensure at least one typology is
    suitable").
    """
    for sa in (ZONE_II_SA, ZONE_V_SA, 0.0, 2.0):
        for budget in ("any", "low", "moderate"):
            materials = get_materials(sa, budget)
            assert materials[0]["suitable"] is True, (
                f"surface_sa={sa} budget={budget}: rank-1 typology "
                f"({materials[0]['name']}) was not suitable"
            )


def test_chennai_zone_ii_low_budget_makes_confined_masonry_suitable():
    """
    The motivating example: at low surface_sa, confined masonry's collapse
    probability (~9.4%) is a negligible absolute risk but was always ranked
    3rd (behind light gauge steel and RC moment frame) under the old
    fixed-top-two rule, so it was marked "avoid" purely by rank position.
    At "low" budget preference (the widest band), it's within tolerance of
    — and cheaper than — the chain of typologies ahead of it, so it becomes
    suitable.
    """
    materials = get_materials(CHENNAI_ZONE_II_SA, "low")
    assert CONFINED_NAME in _suitable_names(materials)


def test_guwahati_zone_v_any_budget_suitable_set():
    """
    At the default "any" (no budget preference) and Zone V's typical
    surface_sa, RC moment frame is within the (narrow) "any" band of light
    gauge steel and no more expensive, so both are suitable — confined
    masonry and unreinforced masonry are not.
    """
    materials = get_materials(GUWAHATI_ZONE_V_SA, "any")
    assert _suitable_names(materials) == {LIGHT_GAUGE_NAME, RC_FRAME_NAME}


def test_guwahati_zone_v_low_budget_light_gauge_steel_suitable():
    """
    Light gauge steel remains suitable at "low" budget too — it's rank 1
    (lowest collapseProbability), which is always suitable regardless of
    budget_preference (see test_lowest_probability_typology_is_always_suitable).
    """
    materials = get_materials(GUWAHATI_ZONE_V_SA, "low")
    assert LIGHT_GAUGE_NAME in _suitable_names(materials)


def test_relative_cost_and_cost_label_are_consistent():
    for sa in (CHENNAI_ZONE_II_SA, GUWAHATI_ZONE_V_SA):
        for m in get_materials(sa):
            if m["relativeCost"] <= 2:
                assert m["costLabel"] == "Low cost"
            elif m["relativeCost"] == 3:
                assert m["costLabel"] == "Moderate cost"
            else:
                assert m["costLabel"] == "Higher cost"


def test_damage_probability_at_the_median_is_half_for_any_median_beta_pair():
    """
    P(DS>=ds | Sa=median) = 0.50 by construction of the lognormal fragility
    function, regardless of which median/beta pair is used — not just the
    one pair test_damage_probability_at_the_median_is_approximately_half()
    checks. Covers every (median, beta) this app's own TYPOLOGIES actually
    use, plus a couple of values no typology happens to have, to confirm
    this is a property of the function, not a coincidence of one dataset.
    """
    pairs = [(t["ds4_median_sa"], t["ds4_beta"]) for t in TYPOLOGIES.values()]
    pairs += [(t["ds2_median_sa"], t["ds2_beta"]) for t in TYPOLOGIES.values()]
    pairs += [(0.5, 0.3), (1.5, 0.8)]
    for median, beta in pairs:
        p = compute_damage_probability(median, median, beta)
        assert abs(p - 0.50) < 1e-9, f"median={median} beta={beta}: expected 0.50, got {p}"


def test_rc_moment_frame_has_lower_collapse_probability_than_confined_masonry_at_zone_v_sa():
    """
    At Zone V-scale surface_sa, RC moment frame (ds4_median_sa=0.90) must
    have a lower collapse probability than confined masonry
    (ds4_median_sa=0.55) — if this were ever inverted, the fragility
    parameters themselves (not the ranking logic) would be wrong, since RC
    moment frame per IS 13920 is the more ductile, higher-capacity system.
    """
    sa = 0.36
    rc = compute_damage_probability(sa, TYPOLOGIES["rc_moment_frame"]["ds4_median_sa"], TYPOLOGIES["rc_moment_frame"]["ds4_beta"])
    cm = compute_damage_probability(sa, TYPOLOGIES["confined_masonry"]["ds4_median_sa"], TYPOLOGIES["confined_masonry"]["ds4_beta"])
    assert rc < cm, f"at sa={sa}: rc_moment_frame P={rc} is not lower than confined_masonry P={cm} — fragility parameters may be inverted"


def test_chennai_zone_ii_low_budget_confined_masonry_suitable_across_illustrative_range():
    """
    Same claim as test_chennai_zone_ii_low_budget_makes_confined_masonry_suitable()
    (which uses the real live surface_sa routers/analyze.py computes for
    Chennai, 0.25g) but swept across the illustrative 0.05-0.08g range too,
    confirming the result isn't sensitive to exactly which Zone II-scale
    value is used.
    """
    for sa in (0.05, 0.06, 0.08):
        materials = get_materials(sa, "low")
        assert CONFINED_NAME in _suitable_names(materials), f"sa={sa}: confined masonry not suitable at budget=low"


def test_guwahati_zone_v_any_budget_rc_moment_frame_suitable_at_illustrative_sa():
    """Same claim as test_guwahati_zone_v_any_budget_suitable_set() (real live 0.90g) at the illustrative 0.36g value too."""
    materials = get_materials(0.36, "any")
    assert RC_FRAME_NAME in _suitable_names(materials)


def test_unreinforced_masonry_never_suitable_at_zone_v_scale_sa():
    """
    Unreinforced masonry has the lowest ds4_median_sa (0.25) of all four
    typologies, so it has the highest collapse probability at any
    surface_sa above ~0.20g (below that, URM and the others cluster too
    close together for this to hold generically — see
    test_lowest_probability_typology_is_always_suitable for the sa=0.0 case,
    where a tie means URM's *rank order*, not its risk, decides suitability).
    At Zone V-scale sa, it should never be suitable, regardless of budget_preference.
    """
    for sa in (0.20, 0.25, 0.36, GUWAHATI_ZONE_V_SA):
        for budget in ("low", "moderate", "any"):
            materials = get_materials(sa, budget)
            urm = next(m for m in materials if m["name"] == URM_NAME)
            assert urm["suitable"] is False, f"sa={sa} budget={budget}: unreinforced masonry was suitable"
            assert urm["collapseProbability"] == max(m["collapseProbability"] for m in materials), (
                f"sa={sa} budget={budget}: unreinforced masonry does not have the highest collapse probability"
            )
