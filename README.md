# GeoSafe

Site-specific seismic hazard assessment and structural material recommendation for Indian construction sites

`React Native` · `Expo SDK 56` · `FastAPI` · `Python 3.11` · `Deployed on Render` · `IS 1893:2016 compliant` · `SRIC Internship · IIT Kharagpur`

> 📲 **[Download Android APK](#)** — link to be added

Indian seismic design practice assigns a site one of four IS 1893 zone labels and stops there — the same label applies whether a building is three storeys or fifteen, and whether the underlying soil amplifies ground motion or damps it. GeoSafe decomposes hazard into bedrock motion, site amplification, and structural vulnerability as three separate, independently-sourced terms, and reports a confidence tier alongside every value it returns, so a zone label is never mistaken for a site-specific measurement.

---

## What makes this different

Site suitability is not a property of the site alone — it is a property of the site and the proposed building height together. At Dehradun, the dominant amplification frequency measured across 50 MASW sites ranges from 3-4 Hz in the north of the city to 1-1.5 Hz in the south-west. A 3-4 Hz site resonates with the natural period of a low-rise building, so low-rise construction carries the higher risk there; a 1-1.5 Hz site resonates with a mid-rise building's natural period, shifting the risk to taller structures in the south-west. A single IS 1893 zone label — Dehradun is Zone IV throughout — cannot express this, because it says nothing about frequency, only about a bounding-box classification of peak ground acceleration. Any hazard output that ignores building height alongside site frequency will misrank risk for at least one class of structure in a city like this.

Every value GeoSafe's backend returns — Vs30, site class, amplification factor, seismic zone, fault distance, liquefaction risk — carries a `source` field: `measured` (a calibrated field survey point within 2 km), `interpolated` (a city-scale survey region), `modeled` (the USGS Global Vs30 raster) or `assumed` (a regional geological default), plus `regional_bbox` for the three hazards that are classified by location bounding box rather than by any physical dataset. The app surfaces this tier in the UI rather than collapsing it into the number. Most production hazard tools return a single value with no indication of how it was derived; GeoSafe treats "how confident is this" as a first-class output, not an internal implementation detail.

The 2001 Bhuj earthquake (M7.7) caused severe damage across Kachchh, but HVSR measurements taken at the affected sites show no strong impedance contrast — the standard signature of site amplification is absent. The damage cannot be attributed to soft-soil resonance; it is better explained by proximity to strong bedrock motion alone. This is why GeoSafe's hazard engine keeps bedrock PGA, site amplification, and vulnerability as three independent terms rather than one blended score: a model that folds amplification into every hazard estimate by default would apply a Bhuj-style correction to a site that never needed one, and would systematically underpredict damage at a site like Bhuj, where the danger was never in the soil.

---

## Tech stack

| Layer | Stack |
|---|---|
| Mobile client | React Native, Expo SDK 56, TypeScript, Expo Router |
| State | Zustand |
| Backend | FastAPI, Python 3.11, Uvicorn |
| Geospatial | GeoPandas, Shapely, PyProj, Rasterio |
| Seismic data | USGS FDSN Earthquake Catalog API (live) |
| Fault geometry | GEM Global Active Faults (600 features, clipped to India) |
| Map rendering | MapLibre React Native, OpenStreetMap tiles |
| Geocoding | OpenCage API |
| Deployment | Render (backend), EAS Build + OTA updates (app) |
| Rate limiting | SlowAPI |

---

## Architecture

```
                     ┌─────────────────────────┐
User input  ──────▶  │  OpenCage geocoding      │
(city name / GPS)    │  text → lat, lon         │
                     └────────────┬─────────────┘
                                  │  lat, lon, floors, building_type
                                  ▼
                     ┌─────────────────────────────────────────────┐
                     │  POST /api/analyze  (FastAPI, 20 req/min/IP) │
                     │                                               │
                     │  1. IS 1893 zone       shapefile / bbox      │
                     │  2. Vs30 + site class  4-tier resolution      │
                     │  3. SPT-N site class   independent dataset    │
                     │  4. Nearest fault      GEM geometry, AEQD     │
                     │  5. Hazard decomposition                      │
                     │       bedrock PGA × amplification = surface   │
                     │  6. USGS earthquake catalog (async, live)     │
                     │  7. Materials + guidelines + hazard inference │
                     └────────────────────┬──────────────────────────┘
                                          │  AnalyzeResponse
                                          │  (every field paired with *Source)
                                          ▼
                     ┌─────────────────────────────────────────────┐
                     │  App screens                                 │
                     │  results/[locationId] → earthquake →         │
                     │  materials → guidelines                      │
                     └───────────────────────────────────────────────┘
```

Vs30 and the seismic zone are resolved as independent inputs — Vs30 is never derived from the zone. Resolution runs through four tiers of decreasing confidence:

1. **Calibrated survey point** (within 2 km of a field measurement) → `source: measured`
2. **City interpolation region** (a declared survey-scale polygon or bbox for Guwahati, Dehradun, Bhuj) → `source: interpolated`
3. **USGS Global Vs30 raster** (topographic-slope proxy, ~1 km resolution) → `source: modeled`
4. **Regional geological default** (keyed to geomorphological province, not seismic zone) → `source: assumed`

---

## Research context

This project began as an SRIC (Summer Research Internship at IIT Kharagpur) placement under Professor Priyanka Dey, Department of Architecture, IIT Kharagpur. The brief was to test whether site-specific geotechnical and seismological data — rather than IS 1893's four-zone national classification alone — could produce a usable, defensible hazard assessment for Indian construction sites, and to build the data pipeline and inference logic that assessment would require.

| Location | Zone | Role | Key data source |
|---|---|---|---|
| Guwahati, Assam | V | Primary training site | 244 borelogs, 43 geophysical tests (Kumar et al. 2018) |
| Kachchh / Bhuj, Gujarat | V | Held-out validation | 2001 M7.7 earthquake damage record, EERI field survey |
| Dehradun, Uttarakhand | IV | Zone IV contrast | 50 MASW sites, SHAKE2000 amplification analysis |

The validation plan is to hold Bhuj entirely out of any future training set and test whether a damage-trained model retrodicts the 2001 damage pattern — specifically, whether it correctly attributes the damage to bedrock motion rather than site amplification, given that HVSR data at Bhuj shows no impedance contrast to amplify. A model that gets Bhuj right for the wrong reason (by inventing amplification where none was measured) would not be considered validated.

---

## Key technical decisions

- **Hazard decomposed into three terms — not a single score.**
  Reason: Bhuj. A blended score cannot represent a site where damage came from bedrock proximity with no site amplification.

- **Vs30 and SPT-N site class carried independently, not merged.**
  Reason: they are documented to systematically disagree in high-plasticity Indian clay, observed at both Guwahati and Lucknow — merging them would silently discard a real discrepancy.

- **Material recommendations stay rule-based.**
  Reason: no IS code provision links site class to material selection. Branching material choice on site class would produce authoritative-looking output with no citable basis; this is the intended insertion point for a damage-trained model, not more hardcoded logic.

- **Distance to nearest fault computed from real GEM geometry, projected to an azimuthal equidistant CRS.**
  Reason: shapely distance in WGS84 is in degrees, not metres; at Guwahati's latitude, treating degrees as a fixed metric distance introduces roughly 8-12% error.

- **Region overlap resolved by smallest-area-region-wins.**
  Reason: dict insertion order is not a defensible precedence rule when two hand-declared city regions happen to overlap.

- **Render cold-start handled with a session-level warm flag, not a generic spinner.**
  Reason: the backend runs on Render's free tier, where a spun-down instance takes 30-60s to wake. The app tracks whether the backend has answered at least once this session (`isBackendWarmed()` in `services/api.ts`) so the "waking up the server" message shows exactly once, on the first genuinely slow request, and never again once the server is known to be awake.

---

## Known limitations

- IS 1893 zone boundaries use bounding-box rules where no real zone shapefile is present; the app falls back to this automatically and labels the result `source: approximate`. No official IS 1893 zone shapefile is publicly available.
- Guwahati calibration values (`backend/data/site_calibration.py`) are currently placeholder points pending extraction of real coordinates and values from Kumar et al. (2018). The provenance system labels them accurately as calibrated data, but the underlying numbers are illustrative, not yet the paper's actual survey results.
- Flood, landslide, and cyclone risk are classified by regional bounding box only (`source: regional_bbox`). No elevation, drainage, or slope data is currently used for any of the three.
- No trained ML model exists yet. Material recommendations now come from a fragility-based ranking (`backend/data/fragility_curves.py`), not a trained model — four typologies (unreinforced masonry, confined masonry, RC moment frame, light gauge steel) are ranked by collapse probability at the site's estimated spectral acceleration, using published lognormal fragility parameters. Fragility parameters are indicative, adapted from published literature. Rankings are for comparative guidance only, not a substitute for site-specific fragility analysis or structural design.
- **`suitable` is a relative ranking, not an absolute safety threshold.** An earlier version marked a typology `suitable: false` whenever its collapse probability exceeded a fixed 30% cutoff — at Zone V's typical estimated spectral acceleration, all four typologies exceed 30%, so that version returned an empty "Recommended" list for every Zone V site, exactly where a recommendation matters most. `suitable: true` never means "safe in absolute terms" — each `MaterialRecommendation.note` states the real basis explicitly, and the materials screen shows an additional disclaimer whenever the site's estimated spectral acceleration exceeds 0.24g (IS 1893 Zone IV's zone factor): "All structural systems face elevated seismic demand at this site... engage a structural engineer before construction."
- **Material rankings use a band-tolerance cost-sensitivity approach — within a collapse-probability band (10 percentage points at the default "moderate" width; narrower or wider depending on `budget_preference`), lower-cost typologies are preferred.** A prior version fixed `suitable` to the top two of the four typologies by raw collapse probability — since these typologies' fragility curves never cross rank order across the Sa range this app produces, that meant the *same two typologies* (light gauge steel, RC moment frame) were always recommended regardless of zone, while a much cheaper, adequate option like confined masonry was marked "avoid" at low-hazard sites purely because it ranked 3rd, not because a ~1% collapse probability was actually unsafe. The band-tolerance rule instead lets any typology within tolerance of — and no more expensive than — the current best join the suitable set, so a cheap, comparably-safe option can be recommended even outside the raw top two. Cost indices (`relativeCost`, `data/fragility_curves.py`) are indicative Indian market rates, not quantity surveys.
- The USGS Global Vs30 raster (631 MB) is **not validated at city scale, and not deployed**. Its read path (`backend/services/vs30_raster.py`) is confirmed correct against a synthetic test raster, but the real file is not present in this environment, and the one download URL tried for it returned an access-denied error rather than the file — so `scripts/validate_vs30.py` has never been run against real data, and no mean absolute error (MAE) against the calibrated Guwahati points exists. This matters specifically because the product is a ~900m topographic-slope proxy, which is a reasonable Vs30 proxy in hilly terrain but a weak one in flat alluvial basins — exactly where Guwahati, Dehradun, and Bhuj sit — so its accuracy here is genuinely unknown, not just unmeasured out of laziness. Until a real MAE is measured, the `modeled` tier stays in the resolution chain unchanged (between `interpolated` and `assumed`) and is also not deployed to Render, whose free tier has an ephemeral, size-constrained filesystem anyway — deployments fall through to the `assumed` regional-default tier at points with no calibrated or interpolated coverage. See `backend/services/vs30_raster.py`'s module docstring for the exact MAE-based policy (usable / `modelled_coarse` / `modelled_unreliable_in_basin`) that will be applied once real validation data is available.
- The building-resonance factor (`resonanceFactor`, `resonanceZone`) is a simplified period-proximity approximation, not a full dynamic analysis — it compares the building's IS 1893 (Part 1):2016 Cl 7.6.2 empirical period against the site's measured dominant amplification frequency and flags proximity, not coupled response. It is currently backed by measured amplification-frequency data for Dehradun North and South only; every other location resolves `resonanceZone: "indeterminate"`.

---

## Setup — local development

### Frontend

```bash
git clone <repo-url>
cd GeoSafe
npm install
cp .env.example .env
```

`.env` / `.env.local`:

```
EXPO_PUBLIC_API_URL=http://<lan-ip-or-host>:8000/api   # optional override, leave unset normally
EXPO_PUBLIC_OPENCAGE_KEY=your_opencage_key_here         # free tier: https://opencagedata.com
EXPO_PUBLIC_MAPTILER_KEY=your_maptiler_key_here         # optional — falls back to plain OSM tiles
```

```bash
npx expo start
```

### Backend

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000 --host 0.0.0.0
```

`--host 0.0.0.0` is required, not optional — the Android emulator, iOS Simulator, and any physical device on the same Wi-Fi are all separate machines from the backend's point of view; `127.0.0.1` accepts none of them.

Verify: `http://localhost:8000/health` → `{"status":"ok", ...}`. Interactive docs: `http://localhost:8000/docs`.

### EAS environment variable (OpenCage key)

`EXPO_PUBLIC_OPENCAGE_KEY` is a real secret and is deliberately not committed in `eas.json`. To make it available to a `preview`/`production` EAS build:

```bash
eas env:create --scope project --environment preview --name EXPO_PUBLIC_OPENCAGE_KEY --value <your-key>
```

---

## Deployment

### Backend (Render)

- **Python version**: the repo-root `.python-version` file pins the build to `3.11.9`. Without it, Render defaults to a newer Python for which `pydantic-core` (pinned transitively by `pydantic==2.7.1`) has no pre-built wheel, failing the build.
- **Start command** — Render assigns the port at runtime via `$PORT`; there is no `--port 8000` in production:
  ```
  uvicorn main:app --host 0.0.0.0 --port $PORT
  ```
- **CORS**: set `CORS_ALLOWED_ORIGINS` (comma-separated) in Render's environment variables. With it unset, the backend defaults to localhost-only dev origins. GeoSafe's API is public, read-only, and requires no authentication, so `CORS_ALLOWED_ORIGINS=*` is a legitimate, deliberate choice in production for this specific app — it must be set explicitly, not left as a code default.
- **Health endpoint**: `GET /health` reports which of the three startup-loaded datasets are actually usable in the running process — see [API reference](#api-reference) below.

### App distribution (EAS)

```bash
eas build --platform android --profile preview
eas update --branch preview
```

No Google Play developer account is required to distribute the app as a standalone APK for direct install (`eas build --profile preview` produces an installable `.apk`); a Play Store listing is only needed for Play Store distribution, which this project does not currently use.

---

## API reference

### `POST /api/analyze`

Request:

```json
{
  "lat": 26.1445,
  "lon": 91.7362,
  "location_name": "Guwahati, Assam",
  "floors": 3,
  "building_type": "residential"
}
```

Response (`AnalyzeResponse`, abridged): `seismicZone` + `seismicZoneSource`, `bedrockPga` + `bedrockPgaSource`, `amplificationFactor` + `amplificationFactorSource`, `surfacePga` (= bedrock × amplification), `designBaseShearCoefficient` + source, `vs30` + source, `siteClassVs30` + source, `siteClassSpt` (nullable) + source, `distanceToFault` / `faultName` / `faultSlipType` / `faultNetSlipRate` + source, `liquefactionRisk` + source, `overallRisk`, plus arrays of `hazards`, `earthquakes`, `materials`, and `guidelines`. Every resolved field is paired with a `*Source` field reporting its confidence tier. Rate-limited to 20 requests/minute per client IP; a `429` response carries an accurate `Retry-After` header.

**Design guidelines (`guidelines[].isCodeRef`) — verification status.** These clause citations (`backend/services/inference.py`'s `get_guidelines()`) were written to be plausible but have not been checked against the actual BIS documents, except one: **IS 1893 Cl. 7.6.2** (the fundamental period formula, confirmed — it was implemented directly from the code text). Every other citation (`IS 1893 Cl. 6.3`, `IS 13920 Cl. 7.3`, `IS 13920 Cl. 7.2.1`, `IS 1893 Cl. 7.6`, `IS 13920 Cl. 9.1`, `IS 1893 Part 1 Annex F`) is unverified. Before relying on any of them: open IS 1893:2016, IS 13920:2016, and IS 4326:2013 and verify each clause number and edition year — IS codes are revised periodically, and a clause number in one edition may refer to different content in another.

### `GET /api/coverage`

Returns every declared calibration/interpolation region (`CoverageRegion[]`) — id, name, state, resolved seismic zone, centre, bounds, boundary polygon, `geometrySource` (`provisional_bbox` or `survey_hull`), the calibrated points inside it, and a `dataQuality` flag (`calibrated` vs `regional`). Used by the map screen to render coverage shading.

### `GET /api/coverage/check?lat=&lon=`

Returns whether a tapped point falls inside a known coverage region (`inCoverage`, `regionId`, `regionName`), the `expectedVs30Source` that `/api/analyze` would actually resolve to at that point, and the `nearestRegion` (id, name, distance in km) if the point falls outside all of them.

### `GET /health`

```json
{
  "status": "ok",
  "message": "GeoSafe API is running",
  "dataSources": {
    "seismicZones": true,
    "vs30Raster": false,
    "activeFaults": true
  }
}
```

The three `dataSources` booleans report whether the IS 1893 zone shapefile, the Vs30 raster, and the GEM active faults dataset are actually loaded in the running process — independent of whether the request-time fallback logic is working, so a broken deploy is visible from this one endpoint before any user hits it.

---

## References

- Kumar, A. et al. (2018). Site characterization and seismic microzonation of Guwahati, India — geotechnical and geophysical dataset (244 borelogs, 43 geophysical tests).
- Dehradun microzonation study (2007). MASW-based Vs30 mapping and amplification analysis, 50 survey sites.
- Jain, S.K. et al. (2001). *Bhuj, India Earthquake of January 26, 2001: Reconnaissance Report.* EERI (Earthquake Engineering Research Institute) field report.
- GEER (2001). *India-US reconnaissance of the January 26, 2001 Bhuj earthquake.* Geotechnical Extreme Events Reconnaissance Association.
- HVSR-based site characterization of Bhuj, Gujarat (2016).
- EGU (2024). Seismic hazard characterization of the Uttarakhand Himalaya.
- Bureau of Indian Standards. IS 1893 (Part 1):2016 — *Criteria for Earthquake Resistant Design of Structures.*
- Bureau of Indian Standards. IS 13920:2016 — *Ductile Detailing of Reinforced Concrete Structures Subjected to Seismic Forces.*
- Bureau of Indian Standards. IS 456:2000 — *Plain and Reinforced Concrete — Code of Practice.*
- Bureau of Indian Standards. IS 4326:2013 — *Earthquake Resistant Design and Construction of Buildings.*
- GEM Foundation. Global Active Faults Database.
