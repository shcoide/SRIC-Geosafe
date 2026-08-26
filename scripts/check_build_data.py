#!/usr/bin/env python3
"""
Render build-time gate: verifies the large geospatial datasets this app
depends on are actually present and non-empty in the built image, before
uvicorn ever starts.

Render's free tier filesystem is ephemeral between spin-downs — nothing
written or fetched at runtime survives a cold start. So
backend/data/is1893_zones/is1893_zones.shp and
backend/data/global_vs30/global_vs30.tif must either be committed straight
to the repo, or fetched during THIS SAME build step — never lazily
downloaded at first request or first startup, since that would appear to
work on a warm local machine or a still-running instance, then silently
vanish the next time Render spins the service back up.

Without this check, a deploy missing either file still boots and still
serves 200s: data/zone_loader.py and services/vs30_raster.py both catch
their own load failures and degrade to a documented fallback rather than
crashing (get_is1893_zone() falls back to a coarse bounding-box
approximation, get_vs30() falls back to a regional geological default —
see backend/services/inference.py). That's the right behavior at runtime,
but it means a broken deploy looks identical to a healthy one from the
outside unless something checks for it explicitly. This script is that
check, run where a human (or CI) will actually notice: the build log.

Usage (as the first step of Render's build command, before installing
Python deps or starting the server):

    python scripts/check_build_data.py && pip install -r backend/requirements.txt

Exits 0 if both files are present and non-empty, 1 otherwise (with the
missing/empty paths listed on stderr).
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    REPO_ROOT / "backend" / "data" / "is1893_zones" / "is1893_zones.shp",
    REPO_ROOT / "backend" / "data" / "global_vs30" / "global_vs30.tif",
]


def main() -> int:
    missing = [p for p in REQUIRED_FILES if not p.exists()]
    empty = [p for p in REQUIRED_FILES if p.exists() and p.stat().st_size == 0]

    if not missing and not empty:
        for path in REQUIRED_FILES:
            print(f"[check_build_data] OK: {path.relative_to(REPO_ROOT)} ({path.stat().st_size:,} bytes)")
        return 0

    print("[check_build_data] BUILD FAILED — required geospatial data file(s) missing or empty:", file=sys.stderr)
    for path in missing:
        print(f"  MISSING: {path.relative_to(REPO_ROOT)}", file=sys.stderr)
    for path in empty:
        print(f"  EMPTY:   {path.relative_to(REPO_ROOT)}", file=sys.stderr)
    print(
        "\nThese must be committed to the repo (or fetched during this same build "
        "step) — never left to load at runtime. Render's free tier filesystem is "
        "ephemeral between spin-downs, so anything not present at build time will "
        "silently be missing after the next cold start, and the app will degrade "
        "to its bounding-box / regional-default fallbacks with no visible error. "
        "See README.md (\"Required data files\") and backend/data/zone_loader.py / "
        "backend/services/vs30_raster.py for the fallback behavior this check "
        "exists to catch before it reaches production.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
