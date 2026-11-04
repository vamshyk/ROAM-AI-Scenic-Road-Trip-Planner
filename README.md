\# ROAM — Beyond the Route



\*\*An AI-powered scenic road trip planner built to help travellers discover more than just the fastest route.\*\*



ROAM is a full-stack road trip planning application that combines real-world road routing, local OpenStreetMap data, scenic feature analysis, machine learning and day-wise itinerary generation.



The goal is to help travellers plan journeys based on both travel efficiency and the experience along the way.



\---



\## Key Features



\- \*\*Road route calculation:\*\* Calculate road routes between locations using routing services.

\- \*\*Scenic intelligence:\*\* Analyse route geometry against local OpenStreetMap datasets.

\- \*\*Multiple route profiles:\*\* Support route comparisons and personalized route recommendations.

\- \*\*Scenic scoring:\*\* Generate a 0–100 heuristic score using forest, water, tourist attraction and road-distribution features.

\- \*\*Day-wise itinerary:\*\* Divide journeys into daily travel segments with overnight stops.

\- \*\*Points of interest:\*\* Identify food, fuel, attractions and viewpoints near the route.

\- \*\*AI trip summaries:\*\* Generate trip descriptions with an AI-powered summary and fallback functionality.

\- \*\*Weather information:\*\* Provide weather-related travel information.

\- \*\*Machine learning:\*\* Predict scenic scores and classify route environments using trained ML models.



\## Technology Stack



| Component | Technologies |

|---|---|

| Frontend | React, TypeScript, Vite |

| Styling | CSS |

| Maps | MapLibre |

| Backend | Python, FastAPI |

| Database | SQLite |

| Geospatial processing | GeoPandas, Shapely |

| Data source | OpenStreetMap |

| Machine learning | Scikit-learn, NumPy, Pandas |

| Version control | Git, GitHub |



\## System Architecture



```text

&#x20;             USER

&#x20;               |

&#x20;               v

&#x20;      REACT + TYPESCRIPT

&#x20;         FRONTEND

&#x20;               |

&#x20;         REST API

&#x20;               |

&#x20;               v

&#x20;         FASTAPI

&#x20;         BACKEND

&#x20;               |

&#x20;      +--------+---------+

&#x20;      |        |         |

&#x20;      v        v         v

&#x20;   ROUTING  SCENIC     ITINERARY

&#x20;    ENGINE  ENGINE     GENERATOR

&#x20;      |        |         |

&#x20;      v        v         v

&#x20;  ROAD DATA  LOCAL OSM   POI DATA

&#x20;             DATASETS

&#x20;               |

&#x20;               v

&#x20;       SCENIC FEATURES

&#x20;               |

&#x20;               v

&#x20;         ML PREDICTOR

&#x20;               |

&#x20;               v

&#x20;       ROUTE RECOMMENDER

&#x20;               |

&#x20;               v

&#x20;        TRIP RESPONSE

&#x20;               |

&#x20;               v

&#x20;         FRONTEND UI

```



\## Project Structure



```text

AI-Scenic-Road-Trip-Planner/

|

|-- backend/

|   |-- data/

|   |   |-- karnataka.db

|   |   |-- models/

|   |   |-- processed/

|   |

|   |-- src/

|   |   |-- main.py

|   |   |-- scenic.py

|   |   |-- scenic\_features.py

|   |   |-- itinerary.py

|   |   |-- recommender.py

|   |   |-- ai\_summary.py

|   |   |-- travel\_intel.py

|   |   |-- db.py

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

|   |

|   |-- package.json

|

|-- .gitignore

|-- README.md

```



\## Installation and Setup



\### Prerequisites



\- Python 3.11 or compatible version

\- Node.js and npm

\- Git



\### 1. Clone the repository



```bash

git clone YOUR\_GITHUB\_REPOSITORY\_URL

cd AI-Scenic-Road-Trip-Planner

```



\### 2. Configure the backend



```powershell

cd backend



python -m venv .venv



.\\.venv\\Scripts\\Activate.ps1



pip install -r requirements.txt

```



Create your environment file:



```powershell

Copy-Item .env.example .env

```



Add the required API keys to `.env` if you want to use external AI services.



\### 3. Configure the scenic datasets



The repository includes the Karnataka SQLite database and trained ML model artifacts.



The scenic feature engine also requires these processed datasets inside `backend/data/processed/`:



\- `forests.csv`

\- `water\_bodies.csv`

\- `tourist\_places.csv`

\- `roads.csv`



These large processed datasets are excluded from Git. Obtain or regenerate them using the project's data preparation pipeline before running the local OSM scenic scoring engine.



The scenic engine should not be considered fully configured on a fresh clone until these files are available.



\### 4. Start the backend



From the `backend` directory:



```powershell

python -m uvicorn src.main:app --reload

```



Backend:



`http://127.0.0.1:8000`



Interactive API documentation:



`http://127.0.0.1:8000/docs`



\### 5. Start the frontend



Open a second terminal:



```powershell

cd frontend



npm install



npm run dev

```



Frontend:



`http://localhost:5173`



\## API Endpoints



The FastAPI backend exposes the following application endpoints:



| Endpoint | Purpose |

|---|---|

| `GET /api/health` | Backend health check |

| `POST /api/route` | Road route calculation |

| `POST /api/plan-trip` | Trip planning |

| `/api/itinerary` | Itinerary functionality |

| `/api/weather` | Weather information |

| `/api/ml/status` | ML model status |



For request parameters and response schemas, refer to the interactive Swagger documentation at `/docs`.



\## Scenic Scoring Methodology



ROAM calculates a heuristic scenic score from 0 to 100 using locally available OpenStreetMap features.



| Feature | Maximum contribution |

|---|---:|

| Forest score | 40 |

| Water score | 25 |

| Attraction score | 20 |

| Track road score | 15 |

| \*\*Total\*\* | \*\*100\*\* |



The scoring engine uses route geometry and spatial queries against local datasets.



\*\*Important limitation:\*\* These features describe mapped OpenStreetMap objects near a route. They do not directly measure subjective scenic beauty, elevation, mountain coverage or coastline.



\## Machine Learning



ROAM includes two machine learning components:



1\. \*\*Scenic score prediction:\*\* A Random Forest regression model.

2\. \*\*Environment classification:\*\* A classification model that predicts route environment categories.



The current training pipeline uses a synthetic dataset with 5,000 generated samples.



The models demonstrate the machine learning pipeline and experimental predictive capabilities.



\*\*Research limitation:\*\* The training labels are synthetic proxy labels, not independently verified real-world scenic-quality ratings. Reported evaluation metrics therefore measure performance on the synthetic task, not proven real-world scenic accuracy.



The ML predictions are experimental and do not replace the local OSM heuristic scenic score.



\## Testing



Run the backend tests from the project root:



```powershell

python -m pytest backend\\tests -q

```



Current verified result:



\*\*25 tests passed.\*\*



The test suite covers:



\- Scenic scoring

\- Route recommendation

\- Itinerary generation

\- ML feature extraction

\- ML model training

\- AI summary generation



\## Future Improvements



\- Integrate elevation and terrain datasets.

\- Improve scenic scoring using verified real-world ratings.

\- Collect user preferences and feedback for personalized recommendations.

\- Improve weather-aware route suggestions.

\- Expand geographic coverage beyond Karnataka.

\- Improve dataset preparation and fresh-install automation.

\- Add further validation of points of interest and travel facilities.



\## Project Information



\*\*Project:\*\* ROAM — Beyond the Route  

\*\*Category:\*\* Full-Stack Development, Geospatial Analytics and Machine Learning  

\*\*Primary focus:\*\* AI-powered scenic road trip planning



\---



\*ROAM aims to make road trips more meaningful by helping travellers explore the journey, not just reach the destination.\*

