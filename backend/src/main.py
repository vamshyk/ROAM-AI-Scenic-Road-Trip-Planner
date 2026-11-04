
from typing import Literal, Optional
from time import sleep, monotonic
from math import radians, sin, cos, sqrt, atan2
from copy import deepcopy

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .scenic import calculate_scenic_score
from .recommender import score_routes
from .itinerary import generate_itinerary
from .travel_intel import get_travel_intelligence
from .ai_summary import generate_trip_summary
from .ml.predictor import enhance_route_with_ml, models_available


# --------------------------------------------------
# ROAM APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="ROAM - AI Road Trip Planner",
    description="AI-powered personalized scenic road trip planning API",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    "User-Agent": "ROAM-Scenic-Road-Trip-Planner/1.0"
}

VALHALLA_URL = "https://valhalla1.openstreetmap.de/route"
OSRM_URL = "https://router.project-osrm.org"

geocode_cache = {}
route_cache = {}

ROUTE_CACHE_TTL = 900
MAX_ROUTE_CACHE_SIZE = 100


# --------------------------------------------------
# PERFORMANCE TIMING
# --------------------------------------------------

def log_stage(stage_name, started):
    elapsed = monotonic() - started
    print(f"[TIMING] {stage_name}: {elapsed:.2f}s")


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class TripRequest(BaseModel):
    origin: str = Field(min_length=2, max_length=100)
    destination: str = Field(min_length=2, max_length=100)
    days: int = Field(ge=1, le=30)
    vehicle: Literal["car", "bike"]
    preference: Literal[
        "explorer", "balanced", "efficient", "budget"
    ] = "balanced"


class RouteRequest(BaseModel):
    origin: str = Field(min_length=2, max_length=100)
    destination: str = Field(min_length=2, max_length=100)
    vehicle: Literal["car", "bike"] = "car"
    preference: Literal[
        "explorer", "balanced", "efficient", "budget"
    ] = "balanced"


class ItineraryRequest(BaseModel):
    origin: str = Field(min_length=2, max_length=100)
    destination: str = Field(min_length=2, max_length=100)
    days: int = Field(ge=1, le=30)
    vehicle: Literal["car", "bike"] = "car"
    route_id: Optional[int] = None


# --------------------------------------------------
# GEOCODING
# --------------------------------------------------

def get_coordinates(place: str):
    """Find a place's coordinates using Nominatim."""

    search_key = place.strip().lower()

    if search_key in geocode_cache:
        return geocode_cache[search_key]

    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": f"{place}, India",
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": "in"
            },
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()
        results = response.json()

        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"Could not find the location: {place}"
            )

        coordinates = {
            "latitude": float(results[0]["lat"]),
            "longitude": float(results[0]["lon"]),
            "display_name": results[0]["display_name"]
        }

        geocode_cache[search_key] = coordinates
        return coordinates

    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail=f"Location search service error: {str(error)}"
        )


# --------------------------------------------------
# ROUTE CACHE
# --------------------------------------------------

def get_route_cache_key(start, end, vehicle, preference="balanced"):
    return (
        round(start["latitude"], 5),
        round(start["longitude"], 5),
        round(end["latitude"], 5),
        round(end["longitude"], 5),
        vehicle,
        preference,
    )


def get_cached_route(key):
    cached = route_cache.get(key)

    if not cached:
        return None

    if monotonic() - cached["created_at"] > ROUTE_CACHE_TTL:
        del route_cache[key]
        return None

    return deepcopy(cached["data"])


def save_route_cache(key, data):
    if len(route_cache) >= MAX_ROUTE_CACHE_SIZE:
        oldest_key = min(
            route_cache,
            key=lambda item: route_cache[item]["created_at"]
        )
        del route_cache[oldest_key]

    route_cache[key] = {
        "created_at": monotonic(),
        "data": deepcopy(data)
    }


# --------------------------------------------------
# POLYLINE DECODING
# --------------------------------------------------

def decode_polyline6(encoded):
    """Decode Valhalla polyline6 into GeoJSON coordinates."""

    coordinates = []
    index = 0
    latitude = 0
    longitude = 0

    while index < len(encoded):
        values = []

        for _ in range(2):
            result = 0
            shift = 0

            while True:
                byte = ord(encoded[index]) - 63
                index += 1

                result |= (byte & 0x1F) << shift
                shift += 5

                if byte < 0x20:
                    break

            delta = (
                ~(result >> 1)
                if result & 1
                else result >> 1
            )

            values.append(delta)

        latitude += values[0]
        longitude += values[1]

        coordinates.append([
            longitude / 1_000_000,
            latitude / 1_000_000
        ])

    return coordinates


# --------------------------------------------------
# GEOMETRY UTILITIES
# --------------------------------------------------

def haversine_km(point_a, point_b):
    lon1, lat1 = point_a
    lon2, lat2 = point_b

    lat1 = radians(lat1)
    lat2 = radians(lat2)

    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)

    value = (
        sin(delta_lat / 2) ** 2
        + cos(lat1) * cos(lat2)
        * sin(delta_lon / 2) ** 2
    )

    return 6371 * 2 * atan2(
        sqrt(value),
        sqrt(1 - value)
    )


def sample_geometry(coordinates, sample_count=20):
    if not coordinates:
        return []

    if len(coordinates) <= sample_count:
        return coordinates

    samples = []

    for index in range(sample_count):
        position = round(
            index * (len(coordinates) - 1)
            / (sample_count - 1)
        )

        samples.append(coordinates[position])

    return samples


def is_duplicate_route(new_route, existing_routes):
    new_samples = sample_geometry(
        new_route["geometry"]["coordinates"]
    )

    if not new_samples:
        return True

    for existing_route in existing_routes:
        old_samples = sample_geometry(
            existing_route["geometry"]["coordinates"]
        )

        if not old_samples:
            continue

        matching_points = 0

        for index, point in enumerate(new_samples):
            old_index = round(
                index * (len(old_samples) - 1)
                / max(len(new_samples) - 1, 1)
            )

            if haversine_km(
                point,
                old_samples[old_index]
            ) < 1.5:
                matching_points += 1

        similarity = matching_points / len(new_samples)

        if similarity >= 0.90:
            return True

    return False


# --------------------------------------------------
# ROUTING PROFILES
# --------------------------------------------------

def get_route_profiles(vehicle):
    profiles = [
        {
            "route_type": "fastest",
            "name": "Fastest Route",
            "description": (
                "Uses standard routing preferences "
                "for a time-saving journey."
            ),
            "options": {
                "use_highways": 0.5,
                "use_tolls": 0.5
            }
        },
        {
            "route_type": "scenic",
            "name": "Scenic Candidate",
            "description": (
                "Reduces highway preference to explore "
                "alternative roads. Scenic quality is "
                "evaluated separately."
            ),
            "options": {
                "use_highways": 0.15,
                "use_tolls": 0.5
            }
        },
        {
            "route_type": "toll_aware",
            "name": "Toll-Aware Route",
            "description": (
                "Attempts to reduce toll-road usage."
            ),
            "options": {
                "use_highways": 0.5,
                "use_tolls": 0.0
            }
        }
    ]

    costing = "motorcycle" if vehicle == "bike" else "auto"

    return costing, profiles


# --------------------------------------------------
# VALHALLA ROUTING
# --------------------------------------------------

def request_valhalla_route(start, end, vehicle, profile):
    costing, _ = get_route_profiles(vehicle)

    payload = {
        "locations": [
            {
                "lat": start["latitude"],
                "lon": start["longitude"]
            },
            {
                "lat": end["latitude"],
                "lon": end["longitude"]
            }
        ],
        "costing": costing,
        "costing_options": {
            costing: profile["options"]
        },
        "units": "kilometers",
        "directions_type": "instructions"
    }

    response = requests.post(
        VALHALLA_URL,
        json=payload,
        headers=HEADERS,
        timeout=40
    )

    response.raise_for_status()

    data = response.json()
    trip = data.get("trip")

    if not trip or not trip.get("legs"):
        raise ValueError("Valhalla returned no usable route.")

    summary = trip.get("summary", {})
    leg = trip["legs"][0]
    encoded_shape = leg.get("shape")

    if not encoded_shape:
        raise ValueError("Valhalla did not return route geometry.")

    coordinates = decode_polyline6(encoded_shape)

    if not coordinates:
        raise ValueError("Could not decode route geometry.")

    distance_km = round(
        float(summary.get("length", 0)), 2
    )

    duration_minutes = round(
        float(summary.get("time", 0)) / 60, 1
    )

    maneuvers = [
        {
            "instruction": maneuver.get("instruction", ""),
            "distance_km": round(
                float(maneuver.get("length", 0)), 2
            ),
            "duration_seconds": round(
                float(maneuver.get("time", 0)), 1
            )
        }
        for maneuver in leg.get("maneuvers", [])
    ]

    return {
        "route_type": profile["route_type"],
        "name": profile["name"],
        "description": profile["description"],
        "distance_km": distance_km,
        "duration_minutes": duration_minutes,
        "duration_hours": round(duration_minutes / 60, 2),
        "has_toll": bool(summary.get("has_toll", False)),
        "has_highway": bool(summary.get("has_highway", False)),
        "has_ferry": bool(summary.get("has_ferry", False)),
        "geometry": {
            "type": "LineString",
            "coordinates": coordinates
        },
        "maneuvers": maneuvers,
        "scenic_score": None,
        "scenic_score_status": "Pending evaluation",
        "scenic_features": None,
        "recommendation_score": None,
        "is_recommended": False,
        "is_fastest": False,
    }


# --------------------------------------------------
# OSRM FALLBACK
# --------------------------------------------------

def get_osrm_fallback(start, end):
    coordinates = (
        f"{start['longitude']},{start['latitude']};"
        f"{end['longitude']},{end['latitude']}"
    )

    response = requests.get(
        f"{OSRM_URL}/route/v1/driving/{coordinates}",
        params={
            "overview": "full",
            "geometries": "geojson",
            "steps": "true",
            "alternatives": "true"
        },
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if data.get("code") != "Ok" or not data.get("routes"):
        raise ValueError("OSRM could not find a route.")

    routes = sorted(
        data["routes"],
        key=lambda item: item["duration"]
    )

    formatted = []

    for index, route in enumerate(routes):
        distance_km = round(route["distance"] / 1000, 2)
        duration_minutes = round(route["duration"] / 60, 1)

        formatted.append({
            "route_type": (
                "fastest" if index == 0 else "alternative"
            ),
            "name": (
                "Fastest Route"
                if index == 0
                else f"Alternative Route {index}"
            ),
            "description": "Calculated using OSRM fallback routing.",
            "distance_km": distance_km,
            "duration_minutes": duration_minutes,
            "duration_hours": round(duration_minutes / 60, 2),
            "geometry": route["geometry"],
            "maneuvers": [],
            "has_toll": None,
            "has_highway": None,
            "has_ferry": None,
            "scenic_score": None,
            "scenic_score_status": "Pending evaluation",
            "scenic_features": None,
            "recommendation_score": None,
            "is_recommended": False,
            "is_fastest": index == 0,
        })

    return formatted


# --------------------------------------------------
# SCENIC EVALUATION + ML
# --------------------------------------------------

def evaluate_scenic_routes(routes, warnings):
    for route in routes:
        try:
            # IMPORTANT:
            # Use the complete route geometry.
            # Do not reduce it to 12 sampled points.
            coordinates = route["geometry"]["coordinates"]

            result = calculate_scenic_score(
                coordinates,
                route_info=route
            )

            if not result:
                route["scenic_score"] = None
                route["scenic_score_status"] = "Scenic data unavailable"
                route["scenic_features"] = None
                warnings.append(
                    f"Scenic evaluation unavailable for {route['name']}."
                )
                continue

            route["scenic_score"] = result.get("scenic_score")
            route["scenic_features"] = result

            if route["scenic_score"] is None:
                route["scenic_score_status"] = "Scenic score unavailable"
                warnings.append(
                    f"Scenic score unavailable for {route['name']}."
                )
            else:
                method = result.get("scoring_method", "heuristic")

                if method == "local_osm_db":
                    route["scenic_score_status"] = (
                        "Calculated using local OSM data"
                    )
                elif method == "heuristic":
                    route["scenic_score_status"] = (
                        "Estimated (build OSM DB for accuracy)"
                    )
                else:
                    route["scenic_score_status"] = "Calculated"

            print(
                f"[SCENIC] {route['name']} | "
                f"Route points: {len(coordinates)} | "
                f"Scenic score: {route['scenic_score']}"
            )

        except Exception as error:
            route["scenic_score"] = None
            route["scenic_score_status"] = "Scenic evaluation failed"
            route["scenic_features"] = None
            warnings.append(
                f"Scenic evaluation failed for {route['name']}: {error}"
            )

    # Keep ML predictions separate from the primary OSM score.
    for route in routes:
        try:
            enhance_route_with_ml(route)
        except Exception as error:
            print(f"ML enhancement warning: {error}")


# --------------------------------------------------
# ROUTE RECOMMENDATION
# --------------------------------------------------

def prepare_route_results(routes, preference="balanced"):
    if not routes:
        raise ValueError("No usable routes were found.")

    routes = score_routes(routes, profile=preference)

    for index, route in enumerate(routes, start=1):
        route["route_id"] = index

    return routes[0]


# --------------------------------------------------
# API ENDPOINTS
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Welcome to ROAM - Beyond the Route!",
        "status": "Backend is running",
        "version": "2.0.0"
    }


@app.get("/api/health")
def health_check():
    from . import db as roam_db

    return {
        "status": "healthy",
        "application": "ROAM",
        "version": "2.0.0",
        "backend": "FastAPI",
        "routing_engine": "Valhalla with OSRM fallback",
        "scenic_engine": (
            "Local OSM DB"
            if roam_db.is_db_available()
            else "Heuristic fallback"
        ),
        "ml_models": (
            "Loaded"
            if models_available()
            else "Not trained (run src/ml/trainer.py)"
        ),
        "route_cache": "Enabled - 15 minutes",
        "message": "ROAM is ready"
    }


@app.post("/api/plan-trip")
def plan_trip(trip: TripRequest):
    """Full trip planning endpoint."""

    request_started = monotonic()
    print("\n========== NEW ROAM TRIP ==========")

    origin_str = trip.origin.strip()
    destination_str = trip.destination.strip()
    vehicle = trip.vehicle
    days = trip.days
    preference = trip.preference

    # Geocoding
    geocoding_started = monotonic()

    start = get_coordinates(origin_str)

    if destination_str.lower() not in geocode_cache:
        sleep(1.1)

    end = get_coordinates(destination_str)

    log_stage("Geocoding", geocoding_started)

    # Route cache
    cache_started = monotonic()

    cache_key = get_route_cache_key(
        start, end, vehicle, preference
    )

    cached_result = get_cached_route(cache_key)

    log_stage("Route cache lookup", cache_started)

    if cached_result:
        cached_result["cache_hit"] = True
        print("[CACHE] Existing trip result returned.")
        log_stage("TOTAL TRIP PLANNING (CACHE HIT)", request_started)
        return cached_result

    print("[CACHE] New trip calculation required.")

    # Routing
    routing_started = monotonic()

    costing, profiles = get_route_profiles(vehicle)
    formatted_routes = []
    warnings = []

    for profile in profiles:
        profile_started = monotonic()

        try:
            route = request_valhalla_route(
                start, end, vehicle, profile
            )

            log_stage(
                f"Valhalla - {profile['name']}",
                profile_started
            )

            if not is_duplicate_route(route, formatted_routes):
                formatted_routes.append(route)
            else:
                print(
                    f"[ROUTE] Duplicate route skipped: "
                    f"{profile['name']}"
                )

        except (
            requests.RequestException,
            ValueError,
            KeyError,
            TypeError
        ) as error:

            log_stage(
                f"Valhalla failed - {profile['name']}",
                profile_started
            )

            warnings.append(
                f"{profile['name']} could not be calculated: {error}"
            )

    routing_source = "Valhalla"

    if not formatted_routes:
        fallback_started = monotonic()

        try:
            formatted_routes = get_osrm_fallback(start, end)
            routing_source = "OSRM fallback"

        except (
            requests.RequestException,
            ValueError,
            KeyError
        ) as error:
            raise HTTPException(
                status_code=502,
                detail=f"Both routing services failed: {error}"
            )

        finally:
            log_stage("OSRM fallback", fallback_started)

    log_stage("Route calculation", routing_started)

    # Scenic scoring + ML
    scenic_started = monotonic()

    evaluate_scenic_routes(formatted_routes, warnings)

    log_stage("Scenic scoring and ML", scenic_started)

    # Recommendation
    recommendation_started = monotonic()

    recommended = prepare_route_results(
        formatted_routes,
        preference
    )

    if len(formatted_routes) == 1:
        warnings.append(
            "Only one distinct route was found. The routing service "
            "did not provide sufficiently different alternatives."
        )

    log_stage("Route recommendation", recommendation_started)

    # Itinerary
    itinerary_started = monotonic()

    try:
        itinerary = generate_itinerary(
            origin_name=origin_str,
            destination_name=destination_str,
            origin=start,
            destination=end,
            route=recommended,
            days=days,
            vehicle=vehicle,
        )

    except Exception as error:
        itinerary = None
        warnings.append(f"Itinerary generation failed: {error}")

    log_stage("Itinerary generation", itinerary_started)

    # Travel intelligence
    travel_started = monotonic()

    try:
        travel_intel = get_travel_intelligence(
            origin=start,
            destination=end,
            route=recommended,
            days=days,
            vehicle=vehicle,
        )

    except Exception as error:
        travel_intel = None
        warnings.append(f"Travel intelligence failed: {error}")

    log_stage("Travel intelligence", travel_started)

    # AI summary
    summary_started = monotonic()

    try:
        ai_summary = generate_trip_summary(
            origin=origin_str,
            destination=destination_str,
            days=days,
            vehicle=vehicle,
            route=recommended,
            scenic_data=recommended.get("scenic_features"),
            weather=travel_intel,
            itinerary=itinerary,
        )

    except Exception as error:
        ai_summary = None
        warnings.append(f"AI summary failed: {error}")

    log_stage("AI summary", summary_started)

    # Final response
    result = {
        "status": "success",
        "message": "ROAM route options calculated successfully!",
        "origin": start,
        "destination": end,
        "vehicle": vehicle,
        "days": days,
        "preference": preference,
        "distance_km": recommended["distance_km"],
        "duration_minutes": recommended["duration_minutes"],
        "duration_hours": recommended["duration_hours"],
        "geometry": recommended["geometry"],
        "routes": formatted_routes,
        "route_count": len(formatted_routes),
        "recommended_route_id": recommended["route_id"],
        "recommendation": recommended.get("recommendation_reason"),
        "routing_engine": routing_source,
        "routing_profile": costing,
        "itinerary": itinerary,
        "travel_intel": travel_intel,
        "ai_summary": ai_summary,
        "warnings": warnings,
        "source": "OpenStreetMap, Valhalla and OSRM",
        "attribution": "© OpenStreetMap contributors",
        "cache_hit": False,
    }

    cache_save_started = monotonic()
    save_route_cache(cache_key, result)
    log_stage("Route cache save", cache_save_started)

    log_stage("TOTAL TRIP PLANNING", request_started)
    print("========== ROAM TRIP COMPLETE ==========\n")

    return result


@app.post("/api/route")
def calculate_route(route_request: RouteRequest):
    """Route-only endpoint."""

    request_started = monotonic()

    origin = route_request.origin.strip()
    destination = route_request.destination.strip()
    vehicle = route_request.vehicle
    preference = route_request.preference

    geocoding_started = monotonic()

    start = get_coordinates(origin)

    if destination.lower() not in geocode_cache:
        sleep(1.1)

    end = get_coordinates(destination)

    log_stage("Route API geocoding", geocoding_started)

    cache_key = get_route_cache_key(
        start, end, vehicle, preference
    )

    cached = get_cached_route(cache_key)

    if cached:
        cached["cache_hit"] = True
        cached["message"] = "Route options retrieved from ROAM cache."
        log_stage("Route API total (CACHE HIT)", request_started)
        return cached

    routing_started = monotonic()

    costing, profiles = get_route_profiles(vehicle)
    formatted_routes = []
    warnings = []

    for profile in profiles:
        profile_started = monotonic()

        try:
            route = request_valhalla_route(
                start, end, vehicle, profile
            )

            log_stage(
                f"Route API Valhalla - {profile['name']}",
                profile_started
            )

            if not is_duplicate_route(route, formatted_routes):
                formatted_routes.append(route)

        except (
            requests.RequestException,
            ValueError,
            KeyError,
            TypeError
        ) as error:
            warnings.append(
                f"{profile['name']} could not be calculated: {error}"
            )

            log_stage(
                f"Route API Valhalla failed - {profile['name']}",
                profile_started
            )

    routing_source = "Valhalla"

    if not formatted_routes:
        fallback_started = monotonic()

        try:
            formatted_routes = get_osrm_fallback(start, end)
            routing_source = "OSRM fallback"

        except (
            requests.RequestException,
            ValueError,
            KeyError
        ) as error:
            raise HTTPException(
                status_code=502,
                detail=f"Both routing services failed: {error}"
            )

        finally:
            log_stage("Route API OSRM fallback", fallback_started)

    log_stage("Route API routing", routing_started)

    scenic_started = monotonic()

    evaluate_scenic_routes(formatted_routes, warnings)

    log_stage("Route API scenic scoring and ML", scenic_started)

    recommended = prepare_route_results(
        formatted_routes,
        preference
    )

    if len(formatted_routes) == 1:
        warnings.append("Only one distinct route was found.")

    result = {
        "status": "success",
        "message": "ROAM route options calculated successfully!",
        "origin": start,
        "destination": end,
        "vehicle": vehicle,
        "distance_km": recommended["distance_km"],
        "duration_minutes": recommended["duration_minutes"],
        "duration_hours": recommended["duration_hours"],
        "geometry": recommended["geometry"],
        "routes": formatted_routes,
        "route_count": len(formatted_routes),
        "recommended_route_id": recommended["route_id"],
        "recommendation": recommended.get("recommendation_reason"),
        "routing_engine": routing_source,
        "routing_profile": costing,
        "warnings": warnings,
        "source": "OpenStreetMap, Valhalla and OSRM",
        "attribution": "© OpenStreetMap contributors",
        "cache_hit": False,
    }

    save_route_cache(cache_key, result)

    log_stage("Route API TOTAL", request_started)

    return result


@app.post("/api/itinerary")
def get_itinerary(req: ItineraryRequest):
    """Generate a day-wise itinerary for a trip."""

    request_started = monotonic()

    origin_str = req.origin.strip()
    destination_str = req.destination.strip()

    start = get_coordinates(origin_str)

    if destination_str.lower() not in geocode_cache:
        sleep(1.1)

    end = get_coordinates(destination_str)

    cache_key = get_route_cache_key(
        start, end, req.vehicle
    )

    cached = get_cached_route(cache_key)

    if cached:
        routes = cached.get("routes", [])

        if req.route_id:
            route = next(
                (
                    r for r in routes
                    if r.get("route_id") == req.route_id
                ),
                None
            )
        else:
            route = next(
                (
                    r for r in routes
                    if r.get("is_recommended")
                ),
                routes[0] if routes else None
            )

    else:
        _, profiles = get_route_profiles(req.vehicle)
        route = None

        for profile in profiles[:1]:
            try:
                route = request_valhalla_route(
                    start, end, req.vehicle, profile
                )
                break
            except Exception:
                continue

    if not route:
        raise HTTPException(
            status_code=404,
            detail="Could not calculate a route for this journey."
        )

    itinerary_started = monotonic()

    itinerary = generate_itinerary(
        origin_name=origin_str,
        destination_name=destination_str,
        origin=start,
        destination=end,
        route=route,
        days=req.days,
        vehicle=req.vehicle,
    )

    log_stage("Standalone itinerary", itinerary_started)
    log_stage("Itinerary API TOTAL", request_started)

    return {
        "status": "success",
        "itinerary": itinerary
    }


@app.get("/api/weather")
def get_weather_for_location(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    days: int = Query(default=7, ge=1, le=16),
):
    """Get weather forecast for a specific coordinate."""

    from .travel_intel import get_weather

    weather = get_weather(lat, lon, days)

    if not weather:
        raise HTTPException(
            status_code=502,
            detail="Weather service unavailable."
        )

    return {
        "status": "success",
        "weather": weather
    }


@app.get("/api/ml/status")
def ml_status():
    """Check if ML models are trained and available."""

    from .ml.trainer import METRICS_PATH
    import json

    available = models_available()
    metrics = None

    if available and METRICS_PATH.exists():
        try:
            with open(METRICS_PATH) as file:
                metrics = json.load(file)
        except Exception:
            pass

    return {
        "models_available": available,
        "metrics": metrics,
        "message": (
            "ML models are ready."
            if available
            else "Run 'python -m src.ml.trainer' to train models."
        )
    }
