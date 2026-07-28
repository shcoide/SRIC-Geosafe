from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from data.zone_loader import load_zones
from services.vs30_raster import load_raster
from services.faults import load_faults
from routers import analyze

app = FastAPI(title="GeoSafe API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api")

@app.on_event("startup")
def _load_is1893_zones():
    load_zones()

@app.on_event("startup")
def _load_vs30_raster():
    load_raster()

@app.on_event("startup")
def _load_active_faults():
    load_faults()

@app.get("/health")
def health():
    return {"status": "ok", "message": "GeoSafe API is running"}
