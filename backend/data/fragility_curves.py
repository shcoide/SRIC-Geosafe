"""
Fragility parameters for structural material ranking (services/inference.py's
get_materials()), and the lognormal damage-probability function that
consumes them.

Fragility parameters are adapted from published Indian seismic fragility
literature. These are indicative values for comparative ranking purposes
only and should not be used for structural design without site-specific
fragility analysis.
"""

from typing import TypedDict

import math
from scipy.stats import norm


class TypologyFragility(TypedDict):
    name: str
    description: str
    is_code: str
    ds2_median_sa: float
    ds2_beta: float
    ds4_median_sa: float
    ds4_beta: float
    relative_cost: int


# Four typologies common in Indian construction. Each carries lognormal
# fragility parameters for two damage states:
#   DS2 (moderate damage) — median_sa in g at which P(DS>=DS2) = 0.50
#   DS4 (complete damage / collapse) — same, for the collapse-level state
# beta is the lognormal standard deviation (dispersion) for that state.
#
# relative_cost: Relative cost index 1-5 (1=lowest). Based on approximate
# Indian market rates for residential construction. Not a substitute for a
# quantity survey.
#
# NOTE on rc_moment_frame vs light_gauge_steel costs: an initial pass at
# these indices (rc_moment_frame=4, light_gauge_steel=3) made RC moment
# frame strictly dominated — light gauge steel was both cheaper AND had a
# higher ds4_median_sa (1.00 vs 0.90), so RC moment frame could never win
# get_materials()'s band-tolerance-plus-cost comparison (see that function's
# docstring) at ANY surface_sa or budget_preference. Confirmed by direct
# computation before shipping this, not assumed. Swapped to
# rc_moment_frame=3, light_gauge_steel=4 — conventional RC moment-frame
# construction is also, in practice, generally cheaper than engineered
# light-gauge cold-formed steel framing in the Indian residential market, so
# this is not just a fix for the ranking but arguably the more realistic
# ordering of the two.
TYPOLOGIES: dict[str, TypologyFragility] = {
    "unreinforced_masonry": {
        "name": "Unreinforced masonry",
        "description": "Random rubble or brick, no RC elements",
        "is_code": "IS 1905",
        # Lognormal parameters for moderate damage (DS2)
        # from HAZUS-compatible Indian URM fragility
        "ds2_median_sa": 0.10,  # Sa(g) at which P(DS>=DS2)=0.50
        "ds2_beta": 0.60,
        # Complete damage (DS4)
        "ds4_median_sa": 0.25,
        "ds4_beta": 0.65,
        "relative_cost": 1,
    },
    "confined_masonry": {
        "name": "Confined masonry",
        "description": "Masonry panels with RC columns and tie beams",
        "is_code": "IS 4326",
        "ds2_median_sa": 0.20,
        "ds2_beta": 0.55,
        "ds4_median_sa": 0.55,
        "ds4_beta": 0.60,
        "relative_cost": 2,
    },
    "rc_moment_frame": {
        "name": "RC moment frame with shear walls",
        "description": "Ductile RC per IS 13920, with shear walls",
        "is_code": "IS 456 + IS 13920",
        "ds2_median_sa": 0.35,
        "ds2_beta": 0.50,
        "ds4_median_sa": 0.90,
        "ds4_beta": 0.55,
        "relative_cost": 3,
    },
    "light_gauge_steel": {
        "name": "Light gauge steel frame",
        "description": "Cold-formed steel, low mass",
        "is_code": "IS 801",
        "ds2_median_sa": 0.40,
        "ds2_beta": 0.50,
        "ds4_median_sa": 1.00,
        "ds4_beta": 0.55,
        "relative_cost": 4,
    },
}


def compute_damage_probability(sa_g: float, median: float, beta: float) -> float:
    """
    P(DS >= ds | Sa) for a standard lognormal fragility function:
        P = Phi( ln(sa_g / median) / beta )
    where Phi is the standard normal CDF (scipy.stats.norm.cdf), median is
    the damage state's median capacity in g, and beta is its lognormal
    dispersion. sa_g <= 0 returns 0.0 (no probability of exceedance at zero
    or negative shaking) rather than raising on ln(0)/ln(negative).
    """
    if sa_g <= 0:
        return 0.0
    return float(norm.cdf(math.log(sa_g / median) / beta))
