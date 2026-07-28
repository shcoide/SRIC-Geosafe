#!/usr/bin/env python3
"""
Compares the USGS Global Vs30 raster against calibrated borehole Vs30 values
in Guwahati (backend/data/site_calibration.py) and prints the mean absolute
error, in m/s, at each point plus overall.

This exists to answer one question before the raster is trusted as a Vs30
source at city scale: how far off is the global product here? Run it after
placing the real GeoTIFF at backend/data/global_vs30/global_vs30.tif.

Usage:
    python scripts/validate_vs30.py
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from data.site_calibration import CALIBRATED_VS30_POINTS  # noqa: E402
from services.vs30_raster import VS30_RASTER_PATH, read_vs30  # noqa: E402


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

    print(f"{'Point':<24}{'Borehole Vs30':>15}{'Raster Vs30':>15}{'Abs. error':>14}")
    errors = []
    for name, borehole_vs30, raster_vs30 in rows:
        if raster_vs30 is None:
            print(f"{name:<24}{borehole_vs30:>15.1f}{'no data':>15}{'--':>14}")
            continue
        error = abs(raster_vs30 - borehole_vs30)
        errors.append(error)
        print(f"{name:<24}{borehole_vs30:>15.1f}{raster_vs30:>15.1f}{error:>14.1f}")

    if not errors:
        print("\nNo raster coverage for any calibrated point — cannot compute MAE.")
        return 1

    mae = sum(errors) / len(errors)
    print(f"\nMean absolute error over {len(errors)}/{len(rows)} point(s): {mae:.1f} m/s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
