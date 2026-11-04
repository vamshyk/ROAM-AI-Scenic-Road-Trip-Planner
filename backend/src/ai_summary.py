
"""
ROAM - AI Trip Summary Generator

Generates personalized trip summaries using the Gemini API.
Falls back to a rule-based summary when Gemini is unavailable.

Scenic scores are OSM-based scores on a 0-100 scale.
Experimental ML predictions are deliberately kept separate.
"""

import os
from typing import Optional

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# --------------------------------------------------
# GEMINI SETUP
# --------------------------------------------------

_model = None
GEMINI_MODEL = "gemini-2.5-flash"


def _get_model():
    """Initialize the Gemini client once per process."""
    global _model

    if _model is not None:
        return _model

    if not GENAI_AVAILABLE:
        return None

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        return None

    try:
        _model = genai.Client(api_key=api_key)
        return _model
    except Exception:
        return None


# --------------------------------------------------
# DATA HELPERS
# --------------------------------------------------

def _get_scenic_score(route: dict, scenic_data: Optional[dict]):
    """
    Get the OSM scenic score from the selected route.

    Priority:
    1. route.scenic_score
    2. route.scenic_features.scenic_score
    3. scenic_data.scenic_score

    Never use ml_scenic_score as the primary scenic score.
    """

    score = route.get("scenic_score")

    if score is None:
        features = route.get("scenic_features") or {}
        score = features.get("scenic_score")

    if score is None and scenic_data:
        score = scenic_data.get("scenic_score")

    try:
        return float(score) if score is not None else None
    except (TypeError, ValueError):
        return None


def _get_weather_summary(weather: Optional[dict]) -> str:
    """Read weather information from ROAM's travel intelligence response."""

    if not weather:
        return ""

    origin_weather = weather.get("origin_weather") or {}
    destination_weather = weather.get("destination_weather") or {}

    current = (
        origin_weather.get("current")
        or weather.get("current")
        or {}
    )

    parts = []

    if current:
        description = current.get("description", "Unknown")
        temperature = current.get("temperature_c")

        if temperature is not None:
            parts.append(
                f"Origin weather: {description}, {temperature}°C."
            )
        else:
            parts.append(f"Origin weather: {description}.")

    destination_current = destination_weather.get("current") or {}

    if destination_current:
        description = destination_current.get(
            "description", "Unknown"
        )
        temperature = destination_current.get("temperature_c")

        if temperature is not None:
            parts.append(
                f"Destination weather: {description}, {temperature}°C."
            )
        else:
            parts.append(f"Destination weather: {description}.")

    rain_risk = weather.get("trip_rain_risk")

    if rain_risk:
        parts.append(f"Overall trip rain risk: {rain_risk}.")

    return " ".join(parts)


def _get_itinerary_summary(itinerary: Optional[dict]) -> str:
    """Create a concise itinerary description."""

    if not itinerary:
        return ""

    itinerary_days = itinerary.get("days") or []
    descriptions = []

    for day in itinerary_days:
        day_number = day.get("day")
        start = day.get("from", "Unknown")
        end = day.get("to", "Unknown")
        distance = day.get("distance_km", 0)

        descriptions.append(
            f"Day {day_number}: {start} to {end}, "
            f"approximately {distance} km."
        )

    return " ".join(descriptions)


# --------------------------------------------------
# PROMPT BUILDER
# --------------------------------------------------

def _build_prompt(
    origin: str,
    destination: str,
    days: int,
    vehicle: str,
    route: dict,
    scenic_data: Optional[dict],
    weather: Optional[dict],
    itinerary: Optional[dict],
) -> str:
    """Build the Gemini prompt using verified trip information."""

    distance = route.get("distance_km", 0) or 0
    duration = route.get("duration_minutes", 0) or 0

    hours = int(duration // 60)
    minutes = int(duration % 60)

    route_name = route.get("name", "Recommended route")

    scenic_score = _get_scenic_score(route, scenic_data)

    route_features = route.get("scenic_features") or scenic_data or {}

    forest_count = route_features.get("nearby_forest_count")
    water_count = route_features.get("nearby_water_count")
    tourist_count = route_features.get("nearby_tourist_places")

    weather_summary = _get_weather_summary(weather)
    itinerary_summary = _get_itinerary_summary(itinerary)

    scenic_line = (
        f"- OSM scenic score: {scenic_score:.1f}/100 "
        "(mapped-feature-based heuristic score)"
        if scenic_score is not None
        else "- OSM scenic score: Not available"
    )

    mapped_features = []

    if forest_count is not None:
        mapped_features.append(f"mapped green features: {forest_count}")

    if water_count is not None:
        mapped_features.append(f"mapped water features: {water_count}")

    if tourist_count is not None:
        mapped_features.append(f"mapped tourist places: {tourist_count}")

    feature_line = (
        "- Mapped route features: " + ", ".join(mapped_features)
        if mapped_features
        else ""
    )

    prompt = f"""
You are ROAM, an expert road-trip travel guide specialising
in Karnataka, India.

Write an engaging, practical trip summary using ONLY the
verified information supplied below.

TRIP DETAILS:
- Origin: {origin}
- Destination: {destination}
- Duration: {days} days
- Vehicle: {vehicle}
- Road distance: {distance:.1f} km
- Estimated driving time: {hours} hr {minutes} min
- Selected route: {route_name}
- Highway sections: {"Yes" if route.get("has_highway") else "No"}
- Toll roads: {"Yes" if route.get("has_toll") else "No"}
{scenic_line}
{feature_line}
- Weather: {weather_summary or "Weather information unavailable"}
- Day-wise plan: {itinerary_summary or "Detailed itinerary unavailable"}

IMPORTANT ACCURACY RULES:
1. The OSM scenic score is out of 100, never out of 10.
2. Do not confuse the OSM scenic score with an experimental ML score.
3. Do not claim that mapped feature counts are verified scenic attractions.
4. Do not invent viewpoints, restaurants, hotels, road conditions,
   local events, or specific attractions.
5. If information is unavailable, keep the description general.
6. Treat weather information as a forecast, not a guarantee.
7. Do not claim that the trip is spread comfortably over several
   days unless the itinerary supports that statement.

WRITE THESE SECTIONS:

**Trip Overview**
Two or three sentences describing the journey.

**What to Expect**
Three or four sentences about the route using verified details.

**Best Moments**
Two or three useful bullet points. Avoid invented locations.

**Practical Tips**
Two or three practical tips based on vehicle, tolls, weather,
and available route information.

**Local Flavour**
One or two general sentences about the destination. Avoid
unsupported specific claims.

Use a warm, inspiring and practical tone.
Keep the total length between 150 and 230 words.
Do not use Markdown heading symbols (#).
"""

    return prompt.strip()


# --------------------------------------------------
# FALLBACK SUMMARY
# --------------------------------------------------

def _build_fallback_summary(
    origin: str,
    destination: str,
    days: int,
    vehicle: str,
    route: dict,
    scenic_data: Optional[dict],
    weather: Optional[dict] = None,
    itinerary: Optional[dict] = None,
) -> str:
    """Generate a useful summary without the Gemini API."""

    distance = route.get("distance_km", 0) or 0
    duration = route.get("duration_minutes", 0) or 0

    hours = int(duration // 60)
    minutes = int(duration % 60)

    scenic_score = _get_scenic_score(route, scenic_data)

    vehicle_phrase = "ride" if vehicle.lower() == "bike" else "drive"

    route_name = route.get("name", "selected route")

    summary = (
        f"Your {days}-day {vehicle} journey from {origin} to "
        f"{destination} covers approximately {distance:.1f} km, "
        f"with an estimated {hours} hr {minutes} min of "
        f"driving time. "
    )

    summary += (
        f"You will follow ROAM's {route_name.lower()}, "
        f"planned for your selected travel preferences. "
    )

    if scenic_score is not None:
        summary += (
            f"The route has an OSM-based scenic score of "
            f"{scenic_score:.1f}/100, calculated from mapped "
            f"features along the route. "
        )

    if route.get("has_toll"):
        summary += (
            "Keep your FASTag ready for toll sections. "
        )

    if not route.get("has_highway"):
        summary += (
            "This option avoids highway sections, so allow "
            "extra time for the journey. "
        )

    weather_summary = _get_weather_summary(weather)

    if weather_summary:
        summary += weather_summary + " "

    if days > 1 and itinerary and itinerary.get("days"):
        summary += (
            f"Your itinerary contains {len(itinerary['days'])} "
            f"planned travel days. Check the daily stops and "
            f"overnight arrangements before departure."
        )
    elif days > 1:
        summary += (
            f"Your trip is planned across {days} days. "
            "Confirm suitable overnight stops before travelling."
        )

    return summary.strip()


# --------------------------------------------------
# PUBLIC API
# --------------------------------------------------

def generate_trip_summary(
    origin: str,
    destination: str,
    days: int,
    vehicle: str,
    route: dict,
    scenic_data: Optional[dict] = None,
    weather: Optional[dict] = None,
    itinerary: Optional[dict] = None,
) -> dict:
    """
    Generate a trip summary.

    Returns:
        {
            "summary": "...",
            "source": "gemini" or "fallback"
        }
    """

    model = _get_model()

    if model is not None:
        try:
            prompt = _build_prompt(
                origin=origin,
                destination=destination,
                days=days,
                vehicle=vehicle,
                route=route,
                scenic_data=scenic_data,
                weather=weather,
                itinerary=itinerary,
            )

            response = model.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )

            summary_text = (response.text or "").strip()

            if summary_text:
                return {
                    "summary": summary_text,
                    "source": "gemini",
                }

        except Exception as error:
            print(f"[ROAM] Gemini summary failed: {error}")

    # Fallback summary
    return {
        "summary": _build_fallback_summary(
            origin=origin,
            destination=destination,
            days=days,
            vehicle=vehicle,
            route=route,
            scenic_data=scenic_data,
            weather=weather,
            itinerary=itinerary,
        ),
        "source": "fallback",
        "note": (
            "Gemini API is unavailable or GEMINI_API_KEY is missing. "
            "Using ROAM's rule-based summary."
        ),
    }
