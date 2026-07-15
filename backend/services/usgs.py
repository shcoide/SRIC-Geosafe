import httpx
import math
from typing import List

async def get_earthquakes(lat: float, lon: float, radius_km: int = 300) -> List[dict]:
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "latitude": lat,
        "longitude": lon,
        "maxradiuskm": radius_km,
        "minmagnitude": 3.5,
        "limit": 30,
        "orderby": "magnitude",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            data = r.json()
            results = []
            for feature in data.get("features", []):
                props = feature["properties"]
                coords = feature["geometry"]["coordinates"]
                eq_lat, eq_lon = coords[1], coords[0]
                dist = haversine(lat, lon, eq_lat, eq_lon)
                year = 2000
                if props.get("time"):
                    from datetime import datetime
                    year = datetime.utcfromtimestamp(props["time"] / 1000).year
                results.append({
                    "magnitude": round(props.get("mag", 0), 1),
                    "place": props.get("place", "Unknown"),
                    "year": year,
                    "depth": round(abs(coords[2]), 1) if len(coords) > 2 else 10.0,
                    "distanceKm": round(dist, 1),
                })
            return results
    except Exception:
        return []

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))
