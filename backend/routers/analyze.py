import hashlib
from fastapi import APIRouter
from models.schemas import AnalyzeRequest, AnalyzeResponse
from services.usgs import get_earthquakes
from services.inference import (
    get_is1893_zone, get_vs30, get_site_class,
    get_liquefaction_risk, get_materials, get_guidelines,
    get_hazards, ZONE_PGA, ZONE_RISK
)

router = APIRouter()

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_location(req: AnalyzeRequest):
    zone = get_is1893_zone(req.lat, req.lon)
    vs30 = get_vs30(req.lat, req.lon)
    site_class = get_site_class(vs30)
    pga = ZONE_PGA[zone]
    liquefaction = get_liquefaction_risk(vs30, zone)
    overall_risk = ZONE_RISK[zone]

    earthquakes = await get_earthquakes(req.lat, req.lon)
    materials = get_materials(zone, site_class, req.floors, req.building_type)
    guidelines = get_guidelines(zone, site_class)
    hazards = get_hazards(zone, req.lat, req.lon)

    location_id = hashlib.md5(f"{req.lat}{req.lon}".encode()).hexdigest()[:10]

    return AnalyzeResponse(
        locationId=location_id,
        name=req.location_name,
        coordinates={"lat": req.lat, "lon": req.lon},
        seismicZone=zone,
        pga=pga,
        vs30=vs30,
        siteClass=site_class,
        distanceToFault=float(max(5, abs(req.lat - 26) * 15)),
        liquefactionRisk=liquefaction,
        overallRisk=overall_risk,
        hazards=hazards,
        earthquakes=earthquakes[:8],
        materials=materials,
        guidelines=guidelines,
    )
