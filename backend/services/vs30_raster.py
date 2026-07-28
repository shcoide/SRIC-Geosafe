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
