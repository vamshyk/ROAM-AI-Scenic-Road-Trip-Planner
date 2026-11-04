# ROAM — Beyond the Route

**An AI-powered scenic road trip planner built to help travellers discover more than just the fastest route.**

ROAM is a full-stack road trip planning application combining road routing, OpenStreetMap geospatial data, scenic feature analysis, machine learning, and day-wise itinerary generation.

## Key Features

- **Road routing:** Calculate road routes between locations using Valhalla with OSRM fallback.
- **Route alternatives:** Compare fastest, scenic-candidate, and toll-aware routing profiles.
- **Scenic scoring:** Calculate a heuristic score from 0–100 using mapped forest, water, tourist attraction, and road-distribution features.
- **Day-wise itineraries:** Divide a trip into daily travel segments with overnight stops.
- **Points of interest:** Identify food, fuel, attractions, and viewpoints near the route.
- **AI trip summaries:** Generate AI-assisted trip descriptions with fallback functionality.
- **Weather information:** Provide weather-related travel information.
- **Machine learning:** Predict scenic scores and classify route environments using trained models.

## Technology Stack

| Component | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite |
| Maps | MapLibre |
| Styling | CSS |
| Backend | Python, FastAPI |
| Database | SQLite |
| Geospatial processing | Shapely, GeoPandas |
| Data source | OpenStreetMap |
| Machine learning | Scikit-learn, NumPy, Pandas |
| Version control | Git, GitHub |

## Architecture

```text
                 USER
                   |
                   v
           REACT + TYPESCRIPT
                FRONTEND
                   |
                REST API
                   |
                   v
                FASTAPI
                BACKEND
                   |
       +-----------+-----------+
       |           |           |
       v           v           v
    ROUTING     SCENIC      ITINERARY
    ENGINE      ENGINE      GENERATOR
       |           |           |
       v           v           v
   ROUTE DATA   LOCAL OSM    POI DATA
                DATASETS
                   |
                   v
             SCENIC FEATURES
                   |
                   v
              ML PREDICTOR
                   |
                   v
           ROUTE RECOMMENDER
                   |
                   v
              TRIP RESPONSE
                   |
                   v
               FRONTEND
```

## Project Structure

```text
ROAM-AI-Scenic-Road-Trip-Planner/
|
|-- backend/
|   |-- data/
|   |   |-- karnataka.db
|   |   |-- models/
|   |   |-- raw/             (generated locally)
|   |   |-- processed/       (generated locally)
|   |
|   |-- src/
|   |   |-- main.py
|   |   |-- scenic.py
|   |   |-- scenic_features.py
|   |   |-- extract_features.py
|   |   |-- data_pipeline.py
|   |   |-- build_database.py
|   |   |-- itinerary.py
|   |   |-- recommender.py
|   |   |-- ai_summary.py
|   |   |-- travel_intel.py
|   |   |-- ml/
|   |
|   |-- tests/
|   |-- requirements.txt
|   |-- .env.example
|
|-- frontend/
|   |-- src/
|   |   |-- components/
|   |   |-- App.tsx
|   |   |-- App.css
|   |   |-- index.css
|   |-- package.json
|
|-- .gitignore
|-- README.md
```

## Installation and Setup

### Prerequisites

- Python 3.14 (tested development environment)
- Node.js and npm
- Git
- Internet connection for external routing, geocoding, weather, and dataset downloads

### 1. Clone the repository

```powershell
git clone https://github.com/vamshyk/ROAM-AI-Scenic-Road-Trip-Planner.git

cd ROAM-AI-Scenic-Road-Trip-Planner
```

### 2. Set up the backend

```powershell
cd backend

python -m venv .venv

.\.venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt

Copy-Item .env.example .env
```

Add your Gemini API key to `backend/.env` if you want to use the external AI summary service.

The application also includes fallback summary functionality.

### 3. Prepare the scenic datasets

The repository includes:

- The Karnataka SQLite database.
- Trained machine learning model artifacts.

The scenic feature engine additionally requires these generated CSV files:

- `forests.csv`
- `water_bodies.csv`
- `tourist_places.csv`
- `roads.csv`

These files are excluded from Git because of their size.

To generate them:

**Step A — Download the Karnataka OpenStreetMap PBF extract.**

From the `backend` directory, run:

```powershell
New-Item -ItemType Directory -Force data\raw | Out-Null

Invoke-WebRequest `
  -Uri "https://download.geofabrik.de/asia/india/karnataka-latest.osm.pbf" `
  -OutFile "data\raw\karnataka-latest.osm.pbf"
```

**Step B — Run the geographic feature extractor.**

Remain in the `backend` directory:

```powershell
python -m src.extract_features
```

This generates the processed CSV datasets in:

```text
backend/data/processed/
```

The extractor also generates `amenities.csv`, which contains additional mapped amenities.

The scenic engine loads the four datasets listed above. Dataset extraction can take time depending on the download, hardware, and data size.

**Database note:** `src.data_pipeline` is a separate pipeline that downloads compressed Karnataka OSM data and builds the SQLite database. It does not generate the processed CSV files used by the scenic feature engine. The repository already includes a database, so rebuilding it is not normally required for the initial setup.

### 4. Start the backend

From the `backend` directory:

```powershell
python -m uvicorn src.main:app --reload
```

Backend:

`http://127.0.0.1:8000`

Interactive API documentation:

`http://127.0.0.1:8000/docs`

### 5. Start the frontend

Open a second terminal from the project root:

```powershell
cd frontend

npm install

npm run dev
```

Frontend:

`http://localhost:5173`

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Backend health check |
| `POST /api/route` | Road route calculation |
| `POST /api/plan-trip` | Trip planning |
| `/api/itinerary` | Itinerary functionality |
| `/api/weather` | Weather information |
| `/api/ml/status` | ML model status |

Use the interactive Swagger documentation at `/docs` for request parameters and response schemas.

## Scenic Scoring Methodology

ROAM calculates a heuristic scenic score from 0 to 100 using locally available OpenStreetMap features.

| Feature | Maximum contribution |
|---|---:|
| Forest score | 40 |
| Water score | 25 |
| Attraction score | 20 |
| Track road score | 15 |
| **Total** | **100** |

The scoring engine analyses route geometry and nearby mapped features using spatial queries.

**Important limitation:** These features represent mapped OpenStreetMap objects near a route. They do not directly measure subjective scenic beauty, elevation, mountain coverage, or coastline.

## Machine Learning

ROAM includes two machine learning components:

1. **Scenic score prediction:** Random Forest regression.
2. **Environment classification:** Classification of route environment categories.

The current training pipeline uses a synthetic dataset containing 5,000 generated samples.

The models demonstrate the machine learning workflow and experimental predictive capabilities.

**Research limitation:** Training labels are synthetic proxy labels, not independently verified real-world scenic-quality ratings. Evaluation metrics therefore measure performance on the synthetic task, not proven real-world scenic accuracy.

ML predictions are experimental and do not replace the local OSM heuristic scenic score.

## Testing

Run the backend tests from the project root:

```powershell
python -m pytest backend\tests -q
```

Latest verified development result:

**25 tests passed.**

The test suite covers:

- Scenic scoring
- Route recommendation
- Itinerary generation
- ML feature extraction
- ML model training
- AI summary generation

## Current Limitations

- Scenic scoring depends on locally available processed OSM datasets.
- Scenic quality is approximated using mapped geographic features.
- ML models use synthetic proxy training labels.
- Routing, geocoding, and weather information depend on external services.
- Points of interest are based on mapped data and may not reflect current operating status.
- Geographic coverage and dataset preparation can be expanded.

## Future Improvements

- Integrate elevation and terrain datasets.
- Improve scenic scoring with verified real-world ratings.
- Collect user preferences and feedback for personalized recommendations.
- Improve weather-aware route suggestions.
- Expand geographic coverage beyond Karnataka.
- Automate dataset preparation and validation.
- Improve verification of points of interest and travel facilities.

## Project Information

**Project:** ROAM — Beyond the Route
**Category:** Full-Stack Development, Geospatial Analytics, and Machine Learning
**Primary focus:** AI-powered scenic road trip planning

---

*ROAM aims to make road trips more meaningful by helping travellers explore the journey, not just reach the destination.*
