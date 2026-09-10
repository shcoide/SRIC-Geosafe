"""
Opens the USGS Global Vs30 GeoTIFF once, at FastAPI startup, and exposes
read_vs30() as a windowed single-pixel read — never a full-raster load,
never a per-request file open.

If the GeoTIFF is missing or fails to open, the dataset handle stays None
and read_vs30() always returns None, so services.inference.get_vs30() falls
through to the next tier (regional geological default).

Place the real file at VS30_RASTER_PATH before trusting this as a source —
see scripts/validate_vs30.py, which checks the raster against calibrated
borehole Vs30 values at city scale first.

VALIDATION STATUS (as of this comment): the read path above (load_raster()
opening the file at startup; read_vs30()'s windowed single-pixel lookup) was
verified against a synthetic in-memory GeoTIFF and confirmed correct — it
reads the pixel that actually contains the query point, and returns None
(not a wrong neighbor) for out-of-bounds points and nodata pixels. What has
NOT been done: comparing the real USGS raster against calibrated Vs30 at
city scale, because the real file (631 MB) is not present in this repo or
this environment, and the one download URL tried for it returned a
CloudFront "AccessDenied" rather than the file. No accuracy figure (MAE)
exists yet, so none of the three tiering policies below has been applied —
the raster stays in the "modeled" tier, unchanged, exactly as before this
comment was added. This is a known gap, not a resolved one; see README.md's
Known Limitations.

Once the real file is available, run `python scripts/validate_vs30.py`
against the calibrated Guwahati points in data/site_calibration.py and act
on its printed MAE:
  MAE < 30 m/s   -> raster usable as-is; no code change needed here.
  MAE 30-60 m/s  -> coarse but directionally correct for these flat alluvial
                    basins; read_vs30()'s caller should report this tier as
                    "modelled_coarse" instead of "modeled".
  MAE > 60 m/s   -> not reliable at city scale for alluvial basins (the
                    ~900m topographic-slope proxy this product uses breaks
                    down where slope itself carries little signal); the
                    "modeled" tier should be dropped for any point inside a
                    CITY_REGIONS bbox and kept only outside all city
                    coverage, reported as "modelled_unreliable_in_basin".
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

VS30_RASTER_PATH = Path(__file__).parent.parent / "data" / "global_vs30" / "global_vs30.tif"

_dataset = None
_open_attempted = False


def load_raster():
    """Opens VS30_RASTER_PATH and keeps the handle open for the process lifetime."""
    global _dataset, _open_attempted
    if _open_attempted:
        return _dataset
    _open_attempted = True

    if not VS30_RASTER_PATH.exists():
        logger.warning(
            "Global Vs30 raster not found at %s — read_vs30() will always return None.",
            VS30_RASTER_PATH,
        )
        return None

    try:
        import rasterio
        _dataset = rasterio.open(VS30_RASTER_PATH)
        logger.info(
            "Opened global Vs30 raster at %s (%dx%d px)",
            VS30_RASTER_PATH, _dataset.width, _dataset.height,
        )
    except Exception:
        logger.exception("Failed to open global Vs30 raster at %s", VS30_RASTER_PATH)
        _dataset = None

    return _dataset


def get_dataset():
    """Returns the cached rasterio dataset handle, or None if unavailable/not yet opened."""
    return _dataset if _open_attempted else load_raster()


def read_vs30(lat: float, lon: float) -> Optional[float]:
    """
    Windowed single-pixel read of the global Vs30 raster at (lat, lon).
    Returns None if the raster isn't loaded, the point falls outside its
    bounds, or the pixel is nodata.
    """
    dataset = _dataset if _open_attempted else load_raster()
    if dataset is None:
        return None

    row, col = dataset.index(lon, lat)
    if row < 0 or col < 0 or row >= dataset.height or col >= dataset.width:
        return None

    from rasterio.windows import Window
    window = Window(col_off=col, row_off=row, width=1, height=1)
    value = dataset.read(1, window=window)[0, 0]

    if dataset.nodata is not None and value == dataset.nodata:
        return None

    return float(value)
