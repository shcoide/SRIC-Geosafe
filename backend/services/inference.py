"""
Rule-based seismic inference engine.
This simulates what the trained ML model will do.
Replace infer() with model.predict() when real models are trained.
"""

from typing import Tuple, List

ZONE_PGA = {"II": 0.10, "III": 0.16, "IV": 0.24, "V": 0.36}
ZONE_RISK = {"II": "Low", "III": "Moderate", "IV": "High", "V": "Very High"}

def get_is1893_zone(lat: float, lon: float) -> str:
    """
    Rule-based IS 1893 zone lookup.
    Replace with PostGIS shapefile query in production.
    """
    # NE India (Assam, Meghalaya, Manipur, etc.) — Zone V
    if lat >= 24 and lat <= 29 and lon >= 89 and lon <= 97:
        return "V"
    # Uttarakhand, Himachal, parts of Kashmir — Zone IV/V
    if lat >= 30 and lat <= 36 and lon >= 74 and lon <= 82:
        return "V" if lat >= 33 else "IV"
    # J&K, Punjab hills
    if lat >= 32 and lat <= 37 and lon >= 72 and lon <= 77:
        return "IV"
    # Gujarat (Bhuj area) — Zone V
    if lat >= 22 and lat <= 25 and lon >= 68 and lon <= 72:
        return "V" if (lat >= 23 and lon <= 70) else "III"
    # Bihar, UP plains
    if lat >= 24 and lat <= 30 and lon >= 78 and lon <= 88:
        return "IV" if lat >= 28 else "III"
    # Andaman — Zone V
    if lat >= 10 and lat <= 14 and lon >= 92 and lon <= 94:
        return "V"
    # Most of peninsular India
    if lat >= 8 and lat <= 25 and lon >= 72 and lon <= 88:
        return "II" if lat < 16 else "III"
    return "III"

def get_vs30(lat: float, lon: float) -> float:
    """Returns estimated Vs30 in m/s. Replace with rasterio GeoTIFF lookup."""
    zone = get_is1893_zone(lat, lon)
    base = {"II": 500, "III": 360, "IV": 270, "V": 210}
    return float(base.get(zone, 300))

def get_site_class(vs30: float) -> str:
    if vs30 >= 760: return "A"
    if vs30 >= 360: return "B"
    if vs30 >= 180: return "C"
    if vs30 >= 90:  return "D"
    return "E"

def get_liquefaction_risk(vs30: float, zone: str) -> str:
    if vs30 < 180 and zone in ("IV", "V"): return "Very High"
    if vs30 < 250 and zone in ("IV", "V"): return "High"
    if vs30 < 360 and zone == "III":        return "Moderate"
    return "Low"

def get_materials(zone: str, site_class: str, floors: int, building_type: str) -> List[dict]:
    if zone in ("IV", "V"):
        recommended = [
            {"rank": 1, "name": "RC moment frame with shear walls", "reason": "Best ductility and lateral resistance for Zone IV/V. Proven in NE India earthquakes.", "isCode": "IS 456 + IS 13920", "suitable": True},
            {"rank": 2, "name": "Confined masonry", "reason": "Cost-effective for 1–2 storey. RC columns and tie beams confine masonry panels effectively.", "isCode": "IS 4326", "suitable": True},
            {"rank": 3, "name": "Light gauge steel frame", "reason": "Lightweight — reduces seismic inertial forces. Ideal for soft soil (Class D/E) sites.", "isCode": "IS 801", "suitable": True},
        ]
        avoid = [
            {"rank": 4, "name": "Unreinforced brick masonry", "reason": "No ductility. Collapses catastrophically in Zone IV/V without confinement.", "isCode": "IS 1905", "suitable": False},
            {"rank": 5, "name": "Flat slab without walls", "reason": "Punching shear failure at column connections during lateral loading.", "isCode": "IS 456", "suitable": False},
        ]
    elif zone == "III":
        recommended = [
            {"rank": 1, "name": "RC frame with infill walls", "reason": "Adequate for Zone III with proper gap detailing around infill panels.", "isCode": "IS 456 + IS 13920", "suitable": True},
            {"rank": 2, "name": "Reinforced masonry", "reason": "Suitable for low-rise (≤3 floors) residential in Zone III with steel reinforcement.", "isCode": "IS 1905", "suitable": True},
        ]
        avoid = [
            {"rank": 3, "name": "Unreinforced masonry above 2 storeys", "reason": "Insufficient seismic resistance for multi-storey in Zone III.", "isCode": "IS 1905", "suitable": False},
        ]
    else:
        recommended = [
            {"rank": 1, "name": "RC frame or reinforced masonry", "reason": "Standard construction adequate for Zone II with basic seismic detailing.", "isCode": "IS 456", "suitable": True},
        ]
        avoid = []
    return recommended + avoid

def get_guidelines(zone: str, site_class: str) -> List[dict]:
    base = [
        {"category": "Foundation", "recommendation": "Raft / mat foundation", "detail": "Required on Class C/D/E soil. Prevents differential settlement during ground shaking.", "isCodeRef": "IS 1893 Cl. 6.3"},
        {"category": "Column reinforcement", "recommendation": f"Min. {'1.5%' if zone in ('IV','V') else '1.0%'} steel ratio", "detail": "Confining hoops at 100 mm c/c in plastic hinge zones (500 mm from joint).", "isCodeRef": "IS 13920 Cl. 7.3"},
        {"category": "Beam-column joint", "recommendation": "Strong column – weak beam design", "detail": "Sum of column moment capacities must exceed sum of beam moment capacities at each joint.", "isCodeRef": "IS 13920 Cl. 7.2.1"},
        {"category": "Roof", "recommendation": "Lightweight RCC slab", "detail": "Avoid heavy roof mass. Each additional tonne of roof mass increases seismic force by PGA × 1000 kg.", "isCodeRef": "IS 1893 Cl. 7.6"},
        {"category": "Infill walls", "recommendation": "Leave gap between infill and RC frame", "detail": "Min. 20mm gap prevents short-column effect which causes brittle shear failure.", "isCodeRef": "IS 13920 Cl. 9.1"},
    ]
    if zone in ("IV", "V") and site_class in ("D", "E"):
        base.append({
            "category": "Liquefaction mitigation",
            "recommendation": "Deep foundation or ground improvement",
            "detail": "Pile foundation to competent layer below liquefiable zone, or dynamic compaction / stone columns.",
            "isCodeRef": "IS 1893 Part 1 Annex F"
        })
    return base

def get_hazards(zone: str, lat: float, lon: float) -> List[dict]:
    zone_eq = {"II": "Low", "III": "Moderate", "IV": "High", "V": "Very High"}
    flood_risk = "High" if (lat >= 24 and lat <= 30 and lon >= 84 and lon <= 92) else "Moderate" if lat < 20 else "Low"
    landslide_risk = "Moderate" if (lat >= 28 or (lat >= 24 and lon >= 90)) else "Low"
    cyclone_risk = "High" if (lat <= 14 and lon >= 80) or (lat >= 20 and lat <= 24 and lon >= 85 and lon <= 92) else "Low"

    return [
        {"type": "earthquake", "level": zone_eq[zone], "description": f"IS 1893 Zone {zone} seismic activity"},
        {"type": "flood", "level": flood_risk, "description": "Based on river proximity and elevation"},
        {"type": "landslide", "level": landslide_risk, "description": "Based on slope and geology"},
        {"type": "cyclone", "level": cyclone_risk, "description": "Based on coastal proximity"},
    ]
