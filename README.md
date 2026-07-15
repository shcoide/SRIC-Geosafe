# GeoSafe — Seismic Risk Intelligence App

GeoSafe is a mobile application (React Native + Expo) paired with a Python FastAPI backend. It lets a user search any Indian city or use their phone's GPS to instantly see:

- IS 1893 seismic hazard zone (Zone II – V)
- Peak Ground Acceleration (PGA) and site class (Vs30)
- Historical earthquake data pulled live from USGS
- Flood, landslide, and cyclone risk estimates
- Recommended structural materials (with IS code references)
- Architectural and construction guidelines

The risk engine is rule-based (no ML model needed to run it). The architecture is designed so a trained XGBoost model can be dropped in later without changing any other code.

---

## What Has Been Built

### 1. Expo Project Bootstrap

The React Native project was created using `create-expo-app` with the `blank-typescript` template. The following configuration changes were applied to match the spec:

**`app.json`** — Updated from the scaffold defaults to:
- Set `name: "GeoSafe"` and `slug: "geosafe"`
- Added `scheme: "geosafe"` (required by Expo Router for deep linking)
- Switched web bundler to `"metro"`
- Added iOS bundle identifier `com.geosafe.app` and the location permission description
- Added Android package name and `ACCESS_FINE_LOCATION` permission
- Registered `expo-router` and `expo-location` as Expo config plugins

**`package.json`** — Changed `"main"` from `"index.ts"` to `"expo-router/entry"` so Expo Router takes control of the app entry point.

---

### 2. All Dependencies Installed

#### Frontend (npm)

| Package | Version | Purpose |
|---|---|---|
| `expo-router` | ~56.2.11 | File-system based navigation (tabs + stack screens) |
| `expo-location` | ~56.0.18 | GPS coordinates and reverse geocoding |
| `expo-constants` | ~56.0.18 | Access to app config at runtime |
| `expo-linking` | ~56.0.14 | Deep link handling |
| `expo-status-bar` | ~56.0.4 | Controls iOS/Android status bar style |
| `react-native-safe-area-context` | ~5.7.0 | Handles notch/home-indicator safe areas |
| `react-native-screens` | 4.25.2 | Native screen containers (required by Router) |
| `react-native-maps` | 1.27.2 | Map view with markers and circles |
| `zustand` | ^5.0.14 | Lightweight global state management |
| `axios` | ^1.18.1 | HTTP client for FastAPI calls |
| `@react-native-async-storage/async-storage` | ^3.1.1 | Persistent key-value storage |
| `react-native-paper` | ^5.15.3 | Material Design UI components |
| `@expo/vector-icons` | ^15.1.1 | Icon set (MaterialCommunityIcons used throughout) |
| `react-native-vector-icons` | ^10.3.0 | Underlying icon library |

#### Backend (pip, Python 3.11)

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.111.0 | Web framework for the REST API |
| `uvicorn[standard]` | 0.29.0 | ASGI server that runs FastAPI |
| `httpx` | 0.27.0 | Async HTTP client used to call USGS API |
| `pydantic` | 2.7.1 | Request/response data validation and serialisation |
| `python-dotenv` | 1.0.1 | Loads `.env` file into environment variables |
| `numpy` | >=2.0.0 | Numerical operations (ready for ML model swap-in) |

> **Note:** Python 3.14 (system default on this machine) does not yet have pre-built wheels for `pydantic-core`. The virtual environment was created with **Python 3.11** (Homebrew) which has full support.

---

### 3. Complete File Structure

```
GeoSafe/
├── app/                          ← All screens (Expo Router file-based routing)
│   ├── _layout.tsx               ← Root stack navigator
│   ├── (tabs)/
│   │   ├── _layout.tsx           ← Bottom tab bar (Search / Map / Recent)
│   │   ├── index.tsx             ← Home / Search screen
│   │   ├── map.tsx               ← Interactive seismic map screen
│   │   └── history.tsx           ← Recent searches screen
│   └── results/
│       ├── [locationId].tsx      ← Hazard overview (dynamic route)
│       ├── earthquake.tsx        ← Earthquake data detail screen
│       ├── materials.tsx         ← Structural material recommendations screen
│       └── guidelines.tsx        ← IS-code architectural guidelines screen
├── components/
│   ├── SearchBar.tsx             ← Search input + GPS button
│   ├── RiskBanner.tsx            ← Coloured overall-risk banner
│   ├── HazardCard.tsx            ← Single hazard type card (earthquake/flood/etc)
│   ├── MaterialCard.tsx          ← Ranked material recommendation card
│   └── LoadingOverlay.tsx        ← Spinner shown while API call is in progress
├── services/
│   ├── api.ts                    ← Axios client + analyzeLocation() function
│   ├── geocoding.ts              ← OpenCage geocoding (text → lat/lon)
│   └── location.ts               ← Expo Location (GPS + reverse geocode)
├── store/
│   └── useLocationStore.ts       ← Zustand global state (result, searches, loading)
├── types/
│   └── index.ts                  ← All TypeScript interfaces
├── constants/
│   ├── colors.ts                 ← Design system colour tokens
│   └── riskConfig.ts             ← Zone labels, risk-level colour mappings, hazard icons
├── backend/
│   ├── main.py                   ← FastAPI app entry point + CORS middleware
│   ├── requirements.txt          ← Python dependency list
│   ├── routers/
│   │   └── analyze.py            ← POST /api/analyze route handler
│   ├── services/
│   │   ├── usgs.py               ← Fetches earthquakes from USGS FDSN API
│   │   ├── inference.py          ← Rule-based IS 1893 zone + risk engine
│   │   └── vs30.py               ← Vs30 lookup (thin wrapper around inference.py)
│   └── models/
│       └── schemas.py            ← Pydantic request/response models
├── app.json                      ← Expo app configuration
├── package.json                  ← npm dependencies and scripts
├── tsconfig.json                 ← TypeScript compiler config
└── .env                          ← API URL and OpenCage key (not committed to git)
```

---

### 4. Detailed File Descriptions

#### `types/index.ts`
Defines every TypeScript interface used across the app. Key types:
- `LocationResult` — the full response shape returned by the backend
- `HazardSummary` — one row in the hazard breakdown (type + level + description)
- `EarthquakeRecord` — one USGS earthquake entry
- `MaterialRecommendation` — one ranked construction material with IS code
- `ArchitecturalGuideline` — one design rule with IS code reference
- `SearchResult` — a geocoding suggestion (name, display name, lat, lon)

#### `constants/colors.ts`
Single source of truth for all colours. Structured as:
- `Colors.primary` / `primaryLight` / `primaryBorder` — brand blue tones
- `Colors.risk.low/moderate/high/veryHigh` — each has `bg`, `border`, `text`, `dot` for consistent risk-level styling
- `Colors.hazard.*` — per-hazard-type accent colours
- `Colors.surface.*` — background and border neutrals
- `Colors.text.*` — primary / secondary / muted text

#### `constants/riskConfig.ts`
Maps data values to display values:
- `RISK_COLORS` — maps `"Low" | "Moderate" | "High" | "Very High"` to the colour objects above
- `ZONE_LABELS` — maps `"II"–"V"` to human-readable descriptions
- `ZONE_RISK` — maps IS 1893 zone to risk level string
- `HAZARD_ICONS` — maps hazard type to MaterialCommunityIcons icon name

#### `store/useLocationStore.ts`
Zustand store. Holds:
- `currentResult` — the last `LocationResult` fetched from the backend (shared across all result screens)
- `recentSearches` — up to 10 past searches, persisted in memory for the session
- `loading` / `error` — global UI state flags
- Actions: `setCurrentResult`, `addRecentSearch`, `setLoading`, `setError`, `clearError`

#### `services/api.ts`
- Creates an Axios client pointed at `http://localhost:8000/api` in development
- Exports `analyzeLocation(params)` which POSTs `{ lat, lon, location_name, floors, building_type }` to the backend and returns a typed `LocationResult`

#### `services/geocoding.ts`
- Calls OpenCage Geocoding API with `countrycode=in` to restrict results to India
- Falls back gracefully (returns centre-of-India coordinates) if no API key is set or the call fails, so the app always works

#### `services/location.ts`
- `requestLocationPermission()` — asks iOS/Android for foreground location permission
- `getCurrentCoordinates()` — returns `{ lat, lon }` from device GPS
- `reverseGeocode()` — converts coordinates back to a place name using Expo's built-in geocoder

#### `components/SearchBar.tsx`
Renders a styled text input (with a magnify icon) and a "Use GPS" button side by side. Accepts `value`, `onChangeText`, `onGpsPress`, and `loading` props.

#### `components/RiskBanner.tsx`
A coloured card that shows the overall risk level (`Low` / `Moderate` / `High` / `Very High`) with its matching background and border colour. Also displays IS 1893 zone, PGA value, and Vs30.

#### `components/HazardCard.tsx`
A compact touchable card for one hazard type. Shows an icon (colour-coded by hazard type), the hazard name, and the risk level. Used in a grid of four on the results overview screen.

#### `components/MaterialCard.tsx`
Displays one ranked structural material recommendation with:
- A numbered circle (colour changes by rank: green → blue → grey)
- Material name and reason
- IS code badge

#### `components/LoadingOverlay.tsx`
Full-screen centred spinner shown while the backend call is in progress.

#### `app/_layout.tsx`
The root Stack navigator. Defines all screen routes and their header titles:
- `(tabs)` — the tab group (no header, tabs handle their own headers)
- `results/[locationId]` — Hazard overview
- `results/earthquake` — Earthquake analysis
- `results/materials` — Material recommendations
- `results/guidelines` — Design guidelines

#### `app/(tabs)/_layout.tsx`
The bottom tab bar. Three tabs: Search (magnify icon), Map (map-outline icon), Recent (history icon). Active tab uses brand blue.

#### `app/(tabs)/index.tsx` — Home / Search Screen
- Renders the `SearchBar` and calls `searchLocations()` on each keystroke (debounced by minimum 3 characters)
- Shows an autocomplete suggestion list while typing
- On selection, calls `analyzeLocation()`, saves the result to the store, adds to recent searches, and navigates to `/results/[locationId]`
- Also shows recent searches when the input is empty
- Shows `LoadingOverlay` while the API call is running

#### `app/(tabs)/map.tsx` — Seismic Map Screen
Shows a `MapView` centred on the last analysed location (or a default India view). Places a `Marker` at the location and a `Circle` with 300 km radius to visualise the earthquake search area. A hint banner appears when no location has been searched yet.

#### `app/(tabs)/history.tsx` — Recent Searches Screen
Reads `recentSearches` from the Zustand store and renders them as a tappable list. Tapping re-runs the analysis for that location and navigates to the results.

#### `app/results/[locationId].tsx` — Hazard Overview (Dynamic Route)
The main results screen. Shows:
- Location name and coordinates
- `RiskBanner` with overall risk
- A grid of four `HazardCard`s (earthquake, flood, landslide, cyclone)
- Four stat boxes (earthquake count, max magnitude, fault distance, liquefaction risk)
- Buttons to navigate to Materials and Guidelines screens

#### `app/results/earthquake.tsx` — Earthquake Analysis
Shows a site parameters card (zone, PGA, Vs30, fault distance, liquefaction risk) followed by a list of recent earthquakes fetched from USGS, each labelled Light / Moderate / Strong with a colour-coded pill.

#### `app/results/materials.tsx` — Material Recommendations
Shows a banner summarising the basis for recommendations, then lists suitable structural systems via `MaterialCard` components, followed by a list of materials to avoid.

#### `app/results/guidelines.tsx` — Architectural Guidelines
Lists IS-code-referenced design rules (foundation type, column steel ratio, beam-column joint design, roof weight, infill wall gaps). Each item has a category label, recommendation, detail text, and IS code badge.

#### `backend/main.py`
FastAPI application entry point. Registers CORS middleware (allows all origins — suitable for development), includes the `analyze` router under the `/api` prefix, and exposes a `/health` endpoint.

#### `backend/routers/analyze.py`
Single route: `POST /api/analyze`. Orchestrates all backend services:
1. Gets IS 1893 zone from coordinates
2. Looks up Vs30 and derives NEHRP site class
3. Fetches earthquakes from USGS asynchronously
4. Generates materials, guidelines, and hazards from the inference engine
5. Returns a fully populated `AnalyzeResponse`

#### `backend/services/inference.py`
The core rule-based engine. Functions:
- `get_is1893_zone(lat, lon)` — maps coordinates to IS 1893 seismic zone (II–V) using bounding-box rules for major Indian regions
- `get_vs30(lat, lon)` — returns estimated shear-wave velocity in m/s based on zone
- `get_site_class(vs30)` — maps Vs30 to NEHRP site class (A–E)
- `get_liquefaction_risk(vs30, zone)` — derives liquefaction risk level
- `get_materials(zone, site_class, floors, building_type)` — returns ranked suitable and unsuitable structural systems
- `get_guidelines(zone, site_class)` — returns IS-code-referenced construction guidelines
- `get_hazards(zone, lat, lon)` — returns all four hazard estimates

#### `backend/services/usgs.py`
- `get_earthquakes(lat, lon, radius_km=300)` — calls the USGS FDSN web service API asynchronously, fetches up to 30 earthquakes ≥ M3.5 within 300 km, converts timestamps to years, computes distances using the Haversine formula, and returns a clean list. Returns an empty list on any network error so the rest of the analysis still completes.

#### `backend/models/schemas.py`
Pydantic v2 models for strict request validation and response serialisation:
- `AnalyzeRequest` — the POST body
- `AnalyzeResponse` — the full response (matches `LocationResult` TypeScript type exactly)
- Plus sub-models for each nested object (hazard, earthquake, material, guideline)

#### `.env`
```
EXPO_PUBLIC_API_URL=http://localhost:8000/api
EXPO_PUBLIC_OPENCAGE_KEY=your_key_here
```
Variables prefixed with `EXPO_PUBLIC_` are automatically injected into the React Native bundle. Replace `your_key_here` with a free OpenCage key (2,500 req/day free tier) from https://opencagedata.com.

---

## How to Run the App

### Prerequisites

Make sure these are installed and working:

```bash
node -v          # Must be 18 or higher  (currently v25.6.1)
python3.11 -V    # Must be 3.11.x        (at /opt/homebrew/bin/python3.11)
watchman --version
xcode-select -p  # Must print a path
```

---

### Terminal 1 — Start the Backend

```bash
cd /Users/shivam/Desktop/PriyankaMa\'am/GeoSafe/backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

What each part does:
- `source venv/bin/activate` — activates the Python 3.11 virtual environment with all packages installed
- `uvicorn main:app` — starts the FastAPI server from `main.py`, exposing the `app` object
- `--reload` — auto-restarts the server whenever you edit a Python file
- `--port 8000` — listens on port 8000

**Verify it is running:** Open http://localhost:8000/health in your browser — you should see `{"status":"ok","message":"GeoSafe API is running"}`.

**Interactive API docs:** http://localhost:8000/docs (Swagger UI, auto-generated by FastAPI)

---

### Terminal 2 — Start the Expo App

```bash
cd /Users/shivam/Desktop/PriyankaMa\'am/GeoSafe
npx expo start
```

This starts the Metro bundler and shows a QR code and menu.

---

## Testing on iOS

### Option A — iOS Simulator (Mac only, no Apple account needed)

```bash
npx expo start --ios
```

Or press `i` in the Expo dev menu after running `npx expo start`.

**Requirements:**
- Xcode installed from the Mac App Store (already confirmed: `xcode-select -p` passes)
- iOS Simulator app (comes with Xcode)

**Known issue:** `react-native-maps` sometimes shows a blank map in the Simulator — this is a known Simulator limitation and works correctly on a real device.

---

### Option B — Real iPhone (requires Expo Go app)

1. Install **Expo Go** from the App Store on your iPhone
2. Make sure your iPhone and Mac are on the **same Wi-Fi network**
3. Run `npx expo start` on your Mac
4. Scan the QR code shown in the terminal with your iPhone camera

**Important:** On a real device, `localhost` in `services/api.ts` won't resolve to your Mac. Find your Mac's local IP:

```bash
ipconfig getifaddr en0
```

Then edit `services/api.ts` line 4:

```typescript
// Change this:
? 'http://localhost:8000/api'
// To this (use your actual IP):
? 'http://192.168.x.x:8000/api'
```

---

### Option C — Build a standalone iOS app (requires Apple Developer account)

```bash
npx expo run:ios
```

This builds a native `.app` bundle and installs it on the Simulator or a connected device.

---

## Testing on Android

### Option A — Android Emulator

1. Install **Android Studio** from https://developer.android.com/studio
2. Open Android Studio → Virtual Device Manager → Create a virtual device (e.g. Pixel 8, API 34)
3. Start the emulator
4. Then run:

```bash
npx expo start --android
```

Or press `a` in the Expo dev menu.

---

### Option B — Real Android Phone (requires Expo Go app)

1. Install **Expo Go** from the Google Play Store on your Android phone
2. Enable **USB Debugging** on your phone:
   - Go to Settings → About Phone → tap Build Number 7 times to unlock Developer Options
   - Settings → Developer Options → enable USB Debugging
3. Connect phone to Mac via USB (or use same Wi-Fi)
4. Run `npx expo start`
5. Scan the QR code with the Expo Go app

**Same IP change applies** as for iPhone (see Option B under iOS above).

---

### Option C — Build a standalone Android APK

```bash
npx expo run:android
```

Requires Android SDK and Java 17+ installed.

---

## Getting an OpenCage API Key (Optional but Recommended)

Without a key, searching "Mumbai" will return a generic India-centre coordinate instead of the real location. The app still works — the backend will correctly analyse wherever you pass it.

1. Go to https://opencagedata.com and sign up (free, no credit card)
2. Copy your API key from the dashboard
3. Edit `.env`:
   ```
   EXPO_PUBLIC_OPENCAGE_KEY=paste_your_key_here
   ```
4. Restart the Expo bundler (`Ctrl+C` then `npx expo start` again)

---

## What to Build Next

- [ ] Replace the bounding-box zone lookup in `backend/services/inference.py` with a PostGIS shapefile query for precise IS 1893 zone boundaries
- [ ] Replace the Vs30 estimate with a rasterio lookup against a GeoTIFF Vs30 raster (global Vs30 data is freely available from USGS)
- [ ] Train and integrate an XGBoost model — the `infer()` function in `inference.py` is designed as the swap-in point
- [ ] Add a free OpenCage API key to `.env` for accurate city search
- [ ] Add AsyncStorage persistence to `useLocationStore` so recent searches survive app restarts
- [ ] Add a `GuidelineItem.tsx` component (listed in spec but not used in any screen yet)
- [ ] Add error boundaries and a proper empty-state UI for the results screens when `result` is null
- [ ] Set up EAS Build for distributing signed builds to testers

---

## Quick Command Reference

| Command | What it does |
|---|---|
| `source venv/bin/activate` | Activates the Python 3.11 virtual environment |
| `uvicorn main:app --reload --port 8000` | Starts FastAPI backend with auto-reload |
| `npx expo start` | Starts Metro bundler, shows QR code |
| `npx expo start --ios` | Starts and opens iOS Simulator directly |
| `npx expo start --android` | Starts and opens Android Emulator directly |
| `ipconfig getifaddr en0` | Gets your Mac's local IP for real-device testing |
| `pip install -r requirements.txt` | (Re-)installs all Python backend packages |
| `npm install` | (Re-)installs all frontend packages |
