import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from data.zone_loader import load_zones, get_zones
from services.vs30_raster import load_raster, get_dataset as get_vs30_dataset
from services.faults import load_faults, get_faults
from rate_limit import limiter
from routers import analyze, coverage

logger = logging.getLogger(__name__)

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
