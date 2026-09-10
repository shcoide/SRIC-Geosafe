import hashlib
from fastapi import APIRouter, Request, Response
from models.schemas import AnalyzeRequest, AnalyzeResponse
from services.usgs import get_earthquakes
from services.inference import (
    get_is1893_zone, get_vs30, get_site_class_spt, get_bedrock_pga, get_amplification_factor,
    get_liquefaction_risk, get_materials, get_guidelines,
    get_hazards, ZONE_RISK, ZONE_PGA, estimate_fundamental_period_sec, get_design_base_shear_coefficient,
    get_design_spectrum, get_building_period, get_amplification_frequency_hz, get_resonance_amplification,
)
from services.faults import nearest_fault
from rate_limit import limiter

router = APIRouter()

# Bounds retries/double-taps from a single client and protects USGS
# fair-use (services/usgs.py) plus the single 0.1 CPU Render instance this
# runs on, since this is by far the most expensive endpoint in the app
# (shapefile query + raster read + fault geometry + a live USGS call).
ANALYZE_RATE_LIMIT = "20/minute"


@router.post("/analyze", response_model=AnalyzeResponse)
@limiter.limit(
    ANALYZE_RATE_LIMIT,
    error_message="Too many analysis requests from this IP — please wait before retrying.",
)
async def analyze_location(request: Request, response: Response, req: AnalyzeRequest):
    zone_result = get_is1893_zone(req.lat, req.lon)
    zone = zone_result.zone
    vs30_result = get_vs30(req.lat, req.lon)
    vs30 = vs30_result.vs30
    site_class_vs30 = vs30_result.site_class
    spt_result = get_site_class_spt(req.lat, req.lon)
    site_class_spt, site_class_spt_source = spt_result if spt_result else (None, None)

    fault_result = nearest_fault(req.lat, req.lon)
    distance_to_fault = fault_result.distance_km if fault_result else None

    bedrock_result = get_bedrock_pga(zone, distance_to_fault)
    bedrock_pga = bedrock_result.pga
    amplification = get_amplification_factor(req.lat, req.lon, vs30_result)

    # Resonance uplift: does the proposed building's period fall near this
    # site's dominant amplification frequency? Multiplied into the response's
    # amplificationFactor (and therefore surface_pga) here, not inside
    # services/inference.py, the same pattern surface_pga's own multiplication
    # already follows.
    building_period_s, _period_clause = get_building_period(req.floors, req.building_type)
    amplification_frequency_hz = get_amplification_frequency_hz(req.lat, req.lon)
    site_period_s = (1.0 / amplification_frequency_hz) if amplification_frequency_hz else None
    resonance = get_resonance_amplification(site_period_s, building_period_s)
    amplification_factor = round(amplification.factor * resonance.resonance_factor, 3)

    surface_pga = round(bedrock_pga * amplification_factor, 4)

    period_sec = estimate_fundamental_period_sec(req.floors)
    base_shear = get_design_base_shear_coefficient(
        zone, site_class_vs30, period_sec, vs30_result.source
    )

    # surface_sa: the site's estimated real spectral acceleration (in g) at
    # the building's period, used only for the fragility-based material
    # ranking below — Z x Sa/g, i.e. the IS 1893 zone factor times the
    # design spectrum's spectral shape, WITHOUT the (I/R) force-reduction
    # term get_design_base_shear_coefficient applies for design purposes
    # (fragility curves expect an actual expected acceleration, not a
    # design-reduced force coefficient). ZONE_PGA is the same zone-factor
    # table get_bedrock_pga() already uses as "Z" elsewhere in this file.
    spectrum = get_design_spectrum(site_class_vs30, period_sec)
    surface_sa = round(ZONE_PGA[zone] * spectrum.sa_g, 4)

    liquefaction = get_liquefaction_risk(vs30, zone)
    overall_risk = ZONE_RISK[zone]

    earthquakes = await get_earthquakes(req.lat, req.lon)
    materials = get_materials(surface_sa, req.budget_preference)
    guidelines = get_guidelines(zone, site_class_vs30)
    hazards = get_hazards(zone, zone_result.source, req.lat, req.lon)

    location_id = hashlib.md5(f"{req.lat}{req.lon}".encode()).hexdigest()[:10]

    return AnalyzeResponse(
        locationId=location_id,
        name=req.location_name,
        coordinates={"lat": req.lat, "lon": req.lon},
        seismicZone=zone,
        seismicZoneSource=zone_result.source,
        bedrockPga=bedrock_pga,
        bedrockPgaSource=bedrock_result.source,
        amplificationFactor=amplification_factor,
        amplificationFactorSource=amplification.source,
        surfacePga=surface_pga,
        surfaceSa=surface_sa,
        resonanceFactor=resonance.resonance_factor,
        resonanceZone=resonance.resonance_zone,
        buildingPeriodS=building_period_s,
        amplificationFrequencyHz=amplification_frequency_hz,
        designBaseShearCoefficient=base_shear.ah,
        designBaseShearCoefficientSource=base_shear.source,
        vs30=vs30,
        vs30Source=vs30_result.source,
        siteClassVs30=site_class_vs30,
        siteClassVs30Source=vs30_result.source,
        siteClassSpt=site_class_spt,
        siteClassSptSource=site_class_spt_source,
        distanceToFault=distance_to_fault,
        faultName=fault_result.fault_name if fault_result else None,
        faultSlipType=fault_result.slip_type if fault_result else None,
        faultNetSlipRate=fault_result.net_slip_rate if fault_result else None,
        faultSource=fault_result.source if fault_result else None,
        liquefactionRisk=liquefaction,
        liquefactionRiskSource=vs30_result.source,
        overallRisk=overall_risk,
        hazards=hazards,
        earthquakes=earthquakes[:8],
        materials=materials,
        guidelines=guidelines,
    )
