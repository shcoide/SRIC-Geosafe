import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from data.site_calibration import check_region_overlaps
from data.zone_loader import load_zones, get_zones
from services.vs30_raster import load_raster, get_dataset as get_vs30_dataset
from services.faults import load_faults, get_faults
from rate_limit import limiter
from routers import analyze, coverage

logger = logging.getLogger(__name__)
# Every other logger.* call in this file is .warning()/.exception() (ERROR),
# which Python's logging module happens to print even with zero config, via
# its "last resort" fallback handler — but that fallback's own level is
# WARNING, so a plain logger.info() would be silently dropped (verified:
# uvicorn's own logging setup only configures its "uvicorn"/"uvicorn.error"/
# "uvicorn.access" loggers, never the root logger, so nothing else raises the
# effective level). The startup port log below needs INFO to actually reach
# Render's log tail, so this module gets its own handler instead of relying
# on that fallback. propagate=False keeps this from double-printing anything
# already visible via the root logger's fallback path (data/zone_loader.py,
# services/vs30_raster.py, etc. are unaffected — they still go through that
# same fallback exactly as before).
logger.setLevel(logging.INFO)
logger.propagate = False
_handler = logging.StreamHandler()
_handler.setLevel(logging.INFO)
_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_handler)

app = FastAPI(title="GeoSafe API", version="1.0.0")

# CORS only matters here for browser-originated requests (Expo web /
# `npx expo start --web`, or hitting /docs directly in a browser) — native
# iOS/Android requests never send an Origin header, so this has no effect
# on the mobile app itself.
#
# CORS_ALLOWED_ORIGINS, if set, is a comma-separated origin list and always
# wins — this is how the deployed Render instance should be configured.
# Setting it to "*" there is a legitimate, deliberate choice for this app
# specifically: GeoSafe's API is public, read-only, and requires no
# authentication, so there's no session/cookie/credential a malicious
# origin could exploit cross-origin — but it must be set explicitly via
# this env var on the deploy, not left as a silent code default.
#
# With no env var set at all (plain local development), the default is the
# actual handful of localhost origins the Expo dev client / web preview run
# on — never a wildcard by default.
DEFAULT_DEV_ORIGINS = [
    "http://localhost:8081",
    "http://127.0.0.1:8081",
    "http://localhost:19006",
    "http://127.0.0.1:19006",
]


def _resolve_allowed_origins() -> list[str]:
    raw = os.environ.get("CORS_ALLOWED_ORIGINS")
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return DEFAULT_DEV_ORIGINS


app.add_middleware(
    CORSMiddleware,
    allow_origins=_resolve_allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Rate limiting (backend/rate_limit.py) --------------------------------
# Protects USGS fair-use and the single 0.1 CPU Render instance from being
# starved by one client's retry loop or an accidental double-tap on
# POST /api/analyze — see routers/analyze.py for the per-route limit.
app.state.limiter = limiter


def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    # GEOSAFE_RATE_LIMITED: grep-able in Render's log tail so a spike of
    # 429s (a misbehaving client, or a legitimate traffic surge) is visible
    # without waiting for a user to report "the app is slow".
    logger.warning(
        "GEOSAFE_RATE_LIMITED path=%s client=%s limit=%s",
        request.url.path, get_remote_address(request), exc.detail,
    )
    return _rate_limit_exceeded_handler(request, exc)


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)


@app.middleware("http")
async def _capture_request_body(request: Request, call_next):
    """
    Reads and stashes the raw request body on request.state *before*
    routing, so it's still available in _unhandled_exception_handler below.
    A route's own body read (e.g. FastAPI parsing the AnalyzeRequest model)
    happens on a separately-constructed Request wrapping the same ASGI
    scope, whose underlying receive stream is already drained by then — by
    design, Starlette can't replay it, so trying to re-read the body inside
    an exception handler silently fails. request.state is backed by the
    shared ASGI scope dict, though, so anything stashed here is visible
    from any Request built on that scope, including the one the exception
    handler receives. This runs for every request, not just /analyze — but
    every body here is small JSON, so buffering it is cheap.
    """
    request.state.raw_body = await request.body()
    return await call_next(request)


def _body_snippet(request: Request) -> str:
    """Truncated, decoded text of the body captured by _capture_request_body, so a huge or malformed body can't flood the log."""
    raw = getattr(request.state, "raw_body", b"")
    if not raw:
        return ""
    return raw.decode("utf-8", errors="replace")[:1000]


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catches anything not already handled by FastAPI's own HTTPException /
    validation-error handling (a real bug, not a client error). Logs one
    grep-able line — GEOSAFE_ERROR — with the request path, client IP, and
    the raw request body (e.g. the analyzeLocation() payload for a crash in
    POST /api/analyze), plus the full traceback via exc_info=True. The goal:
    a remote "it crashed" report should be debuggable from Render's log
    viewer (`grep GEOSAFE_ERROR`) alone, without reproducing it locally.
    """
    logger.error(
        "GEOSAFE_ERROR path=%s method=%s client=%s body=%s error=%r",
        request.url.path, request.method, get_remote_address(request), _body_snippet(request), exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "Something went wrong processing this request."},
    )


app.include_router(analyze.router, prefix="/api")
app.include_router(coverage.router, prefix="/api")


# --- Startup data loaders ---------------------------------------------------
# Each loader (data/zone_loader.py, services/vs30_raster.py,
# services/faults.py) already catches its own load failures internally and
# leaves its cache at None rather than raising — the try/except here is a
# second, independent line of defense so that a startup event can never
# crash the whole app's boot, even if that internal handling is ever
# weakened by a future change to one of those modules. Each data source
# that fails to load simply stays unloaded; its consumer
# (get_is1893_zone() / get_vs30() / nearest_fault(), all in
# services/inference.py and services/faults.py) has a documented fallback
# for exactly that case. See GET /health below for how to tell, from
# outside the process, which of the three actually loaded.

@app.on_event("startup")
def _load_is1893_zones():
    try:
        load_zones()
    except Exception:
        logger.exception(
            "Startup: failed to load the IS 1893 zone shapefile — "
            "get_is1893_zone() will use its bounding-box fallback."
        )


@app.on_event("startup")
def _load_vs30_raster():
    try:
        load_raster()
    except Exception:
        logger.exception(
            "Startup: failed to open the Vs30 raster — "
            "get_vs30() will skip its 'modeled' tier."
        )


@app.on_event("startup")
def _load_active_faults():
    try:
        load_faults()
    except Exception:
        logger.exception(
            "Startup: failed to load the active faults dataset — "
            "nearest_fault() will always return None."
        )


@app.on_event("startup")
def _check_region_overlaps():
    """
    CITY_REGIONS are independently hand-declared provisional bboxes (see
    data/site_calibration.py), so nothing prevents two of them from covering
    the same ground — find_containing_region() already has a deterministic
    most-specific-region-wins rule for that case, so this is not a fatal
    condition, just a fact worth surfacing: log a WARNING per overlapping
    pair (visible in Render's log tail) rather than raising, so a bug in
    this check itself can never take the service down.
    """
    try:
        overlaps = check_region_overlaps()
        for name_a, name_b, area_km2 in overlaps:
            logger.warning(
                "Startup: CITY_REGIONS '%s' and '%s' overlap (~%.1f km^2) — "
                "find_containing_region() resolves points in the overlap to "
                "whichever region is smaller/more specific.",
                name_a, name_b, area_km2,
            )
    except Exception:
        logger.exception("Startup: failed to check CITY_REGIONS for overlaps.")


# This file has no `if __name__ == "__main__":` block — there is no
# `python main.py` entry point in any environment, local or deployed. The
# app is only ever started via the uvicorn CLI, which decides the port
# entirely from its own `--port` flag, outside this file:
#   - Locally:  uvicorn main:app --reload --port 8000 --host 0.0.0.0
#   - Render:   uvicorn main:app --host 0.0.0.0 --port $PORT
# (the exact Render start command lives in Render's dashboard, not in this
# repo — see the README's "Deploying the Backend (Render)" section). So
# there is no in-code `uvicorn.run(..., port=...)` call to check, and no
# in-code port default that could drift out of sync with `$PORT` — reading
# os.environ.get("PORT") below just mirrors the same value Render already
# substituted into that `--port $PORT` flag, purely so it's visible in the
# log without cross-checking the dashboard.
@app.on_event("startup")
def _log_bound_port():
    logger.info(
        "Startup: bound to port %s (from $PORT; falls back to 8000 locally "
        "when $PORT isn't set — see the comment above).",
        os.environ.get("PORT", "8000"),
    )


@app.get("/health")
def health():
    """
    dataSources reports which of the three startup-loaded datasets are
    actually usable right now, so a broken deploy (missing/corrupt data
    file, failed load) is visible immediately from this one endpoint,
    rather than discovered only when a user's /analyze silently degrades
    to fallback values.
    """
    return {
        "status": "ok",
        "message": "GeoSafe API is running",
        "dataSources": {
            "seismicZones": get_zones() is not None,
            "vs30Raster": get_vs30_dataset() is not None,
            "activeFaults": get_faults() is not None,
        },
    }
