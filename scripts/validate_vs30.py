#!/usr/bin/env python3
"""
Compares the USGS Global Vs30 raster against calibrated borehole Vs30 values
in Guwahati (backend/data/site_calibration.py) and prints the absolute and
percentage error at each point, plus the mean absolute error (MAE) overall.

This exists to answer one question before the raster is trusted as a Vs30
source at city scale: how far off is the global product here? Run it after
placing the real GeoTIFF at backend/data/global_vs30/global_vs30.tif.

The printed MAE recommendation below mirrors the three-tier policy this
project has committed to (see backend/services/vs30_raster.py's module
docstring and README.md's Known Limitations):
  MAE < 30 m/s   -> raster usable; keep it as the "modeled" tier, unchanged.
  MAE 30-60 m/s  -> coarse but directionally correct; flag results from it
                    "modelled_coarse" instead of "modeled".
  MAE > 60 m/s   -> not reliable at city scale for alluvial basins; drop it
                    for any point inside a CITY_REGIONS bbox, keep it only
                    outside all coverage, flagged "modelled_unreliable_in_basin".
This script only *prints* which tier the measured MAE falls into — applying
it (changing services/inference.py's resolution chain and source labels,
and updating the README) is a separate, deliberate follow-up step once a
real MAE is known, not something this script does automatically.

Usage:
    python scripts/validate_vs30.py
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from data.site_calibration import CALIBRATED_VS30_POINTS  # noqa: E402
from services.vs30_raster import VS30_RASTER_PATH, read_vs30  # noqa: E402


def _policy_for_mae(mae: float) -> str:
    if mae < 30:
        return "MAE < 30 m/s -> raster usable. Keep the 'modeled' tier as-is."
    if mae <= 60:
        return (
            "30 <= MAE <= 60 m/s -> coarse but directionally correct. "
            "Flag results from this tier 'modelled_coarse' instead of 'modeled'."
        )
    return (
        "MAE > 60 m/s -> not reliable at city scale for alluvial basins. "
        "Drop the raster tier for any point inside a CITY_REGIONS bbox; keep it "
        "only outside all city coverage, flagged 'modelled_unreliable_in_basin'."
    )


def main() -> int:
    if not VS30_RASTER_PATH.exists():
        print(f"Global Vs30 raster not found at {VS30_RASTER_PATH} — nothing to validate.")
        print("Place the USGS Global Vs30 GeoTIFF there and re-run.")
        return 1

    # All current calibrated points are in Guwahati.
    rows = []
    for (lat, lon), point in CALIBRATED_VS30_POINTS.items():
        borehole_vs30 = point["vs30"]
        raster_vs30 = read_vs30(lat, lon)
        rows.append((point["name"], borehole_vs30, raster_vs30))

    print(f"{'Point':<24}{'Calibrated Vs30':>16}{'Raster Vs30':>14}{'Abs. error':>13}{'% error':>10}")
    errors = []
    for name, borehole_vs30, raster_vs30 in rows:
        if raster_vs30 is None:
            print(f"{name:<24}{borehole_vs30:>16.1f}{'no data':>14}{'--':>13}{'--':>10}")
            continue
        error = abs(raster_vs30 - borehole_vs30)
        pct_error = (error / borehole_vs30) * 100 if borehole_vs30 else float("nan")
        errors.append(error)
        print(f"{name:<24}{borehole_vs30:>16.1f}{raster_vs30:>14.1f}{error:>13.1f}{pct_error:>9.1f}%")

    if not errors:
        print("\nNo raster coverage for any calibrated point — cannot compute MAE.")
        return 1

    mae = sum(errors) / len(errors)
    print(f"\nMean absolute error over {len(errors)}/{len(rows)} point(s): {mae:.1f} m/s")
    print(f"Policy: {_policy_for_mae(mae)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
