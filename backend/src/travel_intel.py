
"""
ROAM - Travel Intelligence

Provides weather forecasts, fuel and food stops,
viewpoints, and travel risk information.

Performance improvements:
- Parallel weather requests
- 10-minute weather cache
- Timing logs
"""

import math
from datetime import date
from time import monotonic
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from copy import deepcopy

import requests

try:
    from . import db
    DB_SUPPORT = True
except ImportError:
    DB_SUPPORT = False


HEADERS = {"User-Agent": "ROAM-Scenic-Road-Trip-Planner/1.0"}
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CACHE_TTL = 600
MAX_WEATHER_CACHE_SIZE = 256

weather_cache = {}
weather_cache_lock = Lock()


# --------------------------------------------------
# WEATHER CODES
# --------------------------------------------------

WMO_CODES = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Icy fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Drizzle", "🌦️"),
    55: ("Heavy drizzle", "🌧️"),
    61: ("Light rain", "🌧️"),
    63: ("Rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    71: ("Light snow", "🌨️"),
    73: ("Snow", "❄️"),
    75: ("Heavy snow", "❄️"),
    77: ("Snow grains", "❄️"),
    80: ("Light showers", "🌦️"),
    81: ("Showers", "🌧️"),
    82: ("Heavy showers", "🌧️"),
    85: ("Snow showers", "🌨️"),
    86: ("Heavy snow showers", "❄️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm w/ hail", "⛈️"),
    99: ("Thunderstorm w/ hail", "⛈️"),
}


def _wmo_description(code: int) -> tuple[str, str]:
    return WMO_CODES.get(code, ("Unknown", "🌡️"))


def _risk_level(precipitation_mm: float) -> str:
    if precipitation_mm < 2:
        return "Low"
    elif precipitation_mm < 10:
        return "Moderate"
    return "High"


# --------------------------------------------------
# WEATHER CACHE
# --------------------------------------------------

def _weather_cache_key(lat, lon, days):
    return (
        round(float(lat), 3),
        round(float(lon), 3),
        int(days),
    )


def _get_cached_weather(key):
    with weather_cache_lock:
        cached = weather_cache.get(key)

        if not cached:
            return None

        if monotonic() - cached["created_at"] > WEATHER_CACHE_TTL:
            del weather_cache[key]
            return None

        return deepcopy(cached["data"])


def _save_weather_cache(key, data):
    with weather_cache_lock:
        if len(weather_cache) >= MAX_WEATHER_CACHE_SIZE:
            oldest_key = min(
                weather_cache,
                key=lambda item: weather_cache[item]["created_at"]
            )
            del weather_cache[oldest_key]

        weather_cache[key] = {
            "created_at": monotonic(),
            "data": deepcopy(data),
        }


# --------------------------------------------------
# WEATHER FETCHING
# --------------------------------------------------

def get_weather(
    lat: float,
    lon: float,
    days: int = 7
) -> Optional[dict]:

    days = min(max(days, 1), 16)

    cache_key = _weather_cache_key(lat, lon, days)
    cached = _get_cached_weather(cache_key)

    if cached is not None:
        print(f"Weather cache hit: {lat}, {lon}")
        return cached

    started = monotonic()

    try:
        response = requests.get(
            OPEN_METEO_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": (
                    "temperature_2m,weathercode,windspeed_10m,"
                    "relativehumidity_2m"
                ),
                "daily": (
                    "weathercode,temperature_2m_max,temperature_2m_min,"
                    "precipitation_sum,windspeed_10m_max"
                ),
                "timezone": "Asia/Kolkata",
                "forecast_days": days,
                "wind_speed_unit": "kmh",
                "temperature_unit": "celsius",
                "precipitation_unit": "mm",
            },
            headers=HEADERS,
            timeout=15,
        )

        response.raise_for_status()
        data = response.json()

    except requests.RequestException as error:
        print(f"Weather request failed: {error}")
        return None

    current_raw = data.get("current", {})
    code = current_raw.get("weathercode", 0)
    description, icon = _wmo_description(code)

    current = {
        "temperature_c": current_raw.get("temperature_2m"),
        "weather_code": code,
        "description": description,
        "icon": icon,
        "wind_kmh": current_raw.get("windspeed_10m"),
        "humidity_pct": current_raw.get("relativehumidity_2m"),
    }

    daily_raw = data.get("daily", {})

    dates = daily_raw.get("time", [])
    codes = daily_raw.get("weathercode", [])
    max_temps = daily_raw.get("temperature_2m_max", [])
    min_temps = daily_raw.get("temperature_2m_min", [])
    precip = daily_raw.get("precipitation_sum", [])
    wind_max = daily_raw.get("windspeed_10m_max", [])

    daily_forecast = []

    for i, day_date in enumerate(dates):
        day_code = codes[i] if i < len(codes) else 0
        day_desc, day_icon = _wmo_description(day_code)

        precip_mm = (
            precip[i]
            if i < len(precip) and precip[i] is not None
            else 0.0
        )

        daily_forecast.append({
            "date": day_date,
            "description": day_desc,
            "icon": day_icon,
            "temp_max_c": max_temps[i] if i < len(max_temps) else None,
            "temp_min_c": min_temps[i] if i < len(min_temps) else None,
            "precipitation_mm": round(precip_mm, 1),
            "wind_max_kmh": wind_max[i] if i < len(wind_max) else None,
            "rain_risk": _risk_level(precip_mm),
        })

    fog_risk = "Low"

    if current.get("humidity_pct") and current["humidity_pct"] > 85:
        if current.get("wind_kmh") and current["wind_kmh"] < 10:
            fog_risk = "Moderate"

    if current.get("weather_code") in (45, 48):
        fog_risk = "High"

    result = {
        "current": current,
        "daily_forecast": daily_forecast,
        "fog_risk": fog_risk,
        "best_travel_days": _find_best_days(daily_forecast),
    }

    _save_weather_cache(cache_key, result)

    print(
        f"Weather fetched in {monotonic() - started:.2f}s "
        f"for {lat}, {lon}"
    )

    return result


def _find_best_days(forecast: list[dict]) -> list[str]:
    return [
        day["date"]
        for day in forecast
        if day["rain_risk"] == "Low"
        and day.get("temp_max_c") is not None
        and 15 <= day["temp_max_c"] <= 35
    ][:3]


# --------------------------------------------------
# FUEL AND FOOD STOPS
# --------------------------------------------------

def get_stops_along_route(
    route_coords: list[list[float]],
    total_distance: float,
    vehicle: str,
) -> dict:

    poi_types = ["fuel", "food", "viewpoint", "hotel"]

    if vehicle == "bike":
        poi_types.append("medical")

    stops = {item: [] for item in poi_types}

    if DB_SUPPORT and db.is_db_available():
        try:
            all_pois = db.query_pois_along_route(
                route_coords,
                poi_types,
                radius_deg=0.06
            )

            for poi in all_pois:
                category = poi.get("poi_type", "other")

                if category in stops:
                    stops[category].append({
                        "name": poi.get("name") or "Unnamed",
                        "lat": poi["lat"],
                        "lon": poi["lon"],
                        "type": category,
                    })

        except Exception as error:
            print(f"POI lookup failed: {error}")

    if not stops["fuel"]:
        stops["fuel"] = _heuristic_fuel_stops(
            total_distance,
            vehicle
        )

    for key in stops:
        stops[key] = stops[key][:8]

    return {
        "fuel_stations": stops.get("fuel", []),
        "food_stops": stops.get("food", []),
        "viewpoints": stops.get("viewpoint", []),
        "hotels": stops.get("hotel", []),
        "medical": stops.get("medical", []),
    }


def _heuristic_fuel_stops(
    distance_km: float,
    vehicle: str
) -> list[dict]:

    spacing_km = 35 if vehicle == "car" else 40
    count = max(1, int(distance_km / spacing_km))

    return [
        {
            "name": f"Fuel stop {i + 1} (estimated)",
            "km_from_start": round(
                (i + 1) * distance_km / (count + 1),
                1
            ),
            "type": "fuel",
            "note": (
                "Estimated advisory, not a verified station location."
            ),
        }
        for i in range(min(count, 5))
    ]


# --------------------------------------------------
# COMBINED TRAVEL INTELLIGENCE
# --------------------------------------------------

def get_travel_intelligence(
    origin: dict,
    destination: dict,
    route: dict,
    days: int,
    vehicle: str,
) -> dict:

    started = monotonic()

    coords = route.get("geometry", {}).get("coordinates", [])
    total_distance = route.get("distance_km", 0)

    if coords:
        step = max(1, len(coords) // 20)
        sampled = coords[::step][:20]
    else:
        sampled = []

    forecast_days = min(days + 2, 16)

    # Fetch both forecasts at the same time.
    with ThreadPoolExecutor(max_workers=2) as executor:
        origin_future = executor.submit(
            get_weather,
            origin["latitude"],
            origin["longitude"],
            forecast_days,
        )

        destination_future = executor.submit(
            get_weather,
            destination["latitude"],
            destination["longitude"],
            forecast_days,
        )

        origin_weather = origin_future.result()
        destination_weather = destination_future.result()

    weather_finished = monotonic()

    stops = get_stops_along_route(
        sampled,
        total_distance,
        vehicle
    )

    stops_finished = monotonic()

    rain_risk = "Low"

    if origin_weather and destination_weather:
        origin_days = origin_weather.get("daily_forecast", [])[:days]
        dest_days = destination_weather.get("daily_forecast", [])[:days]

        all_risks = [
            item["rain_risk"]
            for item in origin_days + dest_days
        ]

        if "High" in all_risks:
            rain_risk = "High"
        elif "Moderate" in all_risks:
            rain_risk = "Moderate"

    print(
        "[TIMING] Travel intelligence | "
        f"weather={weather_finished - started:.2f}s | "
        f"stops={stops_finished - weather_finished:.2f}s | "
        f"total={monotonic() - started:.2f}s"
    )

    return {
        "origin_weather": origin_weather,
        "destination_weather": destination_weather,
        "trip_rain_risk": rain_risk,
        "stops": stops,
        "fuel_station_count": len(stops.get("fuel_stations", [])),
        "food_stop_count": len(stops.get("food_stops", [])),
        "viewpoint_count": len(stops.get("viewpoints", [])),
    }
