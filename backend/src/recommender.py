
"""
ROAM - Route Recommendation Engine

Ranks routes using:
  - Scenic quality (0–100)
  - Travel time
  - Distance
  - Toll avoidance

Scenic scores are provided by the local OSM feature engine.
"""

from typing import Optional


# --------------------------------------------------
# DEFAULT PREFERENCE WEIGHTS
# --------------------------------------------------

DEFAULT_WEIGHTS = {
    "scenic": 0.40,
    "time": 0.30,
    "distance": 0.15,
    "no_toll": 0.15,
}

PREFERENCE_PROFILES = {
    "explorer": {
        "scenic": 0.50, "time": 0.20,
        "distance": 0.15, "no_toll": 0.15
    },
    "balanced": {
        "scenic": 0.40, "time": 0.30,
        "distance": 0.15, "no_toll": 0.15
    },
    "efficient": {
        "scenic": 0.15, "time": 0.50,
        "distance": 0.25, "no_toll": 0.10
    },
    "budget": {
        "scenic": 0.30, "time": 0.25,
        "distance": 0.20, "no_toll": 0.25
    },
}


# --------------------------------------------------
# NORMALISATION
# --------------------------------------------------

def _normalise(
    value: float,
    min_val: float,
    max_val: float,
    invert: bool = False
) -> float:
    """Normalise a value to the range 0–1."""

    if max_val == min_val:
        return 0.5

    normalised = (value - min_val) / (max_val - min_val)

    return 1.0 - normalised if invert else normalised


# --------------------------------------------------
# ROUTE SCORING
# --------------------------------------------------

def score_routes(
    routes: list[dict],
    profile: str = "balanced",
    user_weights: Optional[dict] = None
) -> list[dict]:
    """
    Score and rank routes.

    Scenic score: 0–100
    Recommendation score: 0–10
    """

    if not routes:
        return routes

    weights = dict(PREFERENCE_PROFILES.get(profile, DEFAULT_WEIGHTS))

    if user_weights:
        weights.update(user_weights)

    # Read route values without treating a valid zero as missing.
    scenic_scores = [
        float(r.get("scenic_score") if r.get(
            "scenic_score") is not None else 0)
        for r in routes
    ]

    durations = [float(r["duration_minutes"]) for r in routes]
    distances = [float(r["distance_km"]) for r in routes]

    min_scenic, max_scenic = min(scenic_scores), max(scenic_scores)
    min_duration, max_duration = min(durations), max(durations)
    min_distance, max_distance = min(distances), max(distances)

    # Calculate weighted scores.
    for route in routes:

        scenic_val = float(
            route.get("scenic_score")
            if route.get("scenic_score") is not None
            else 0
        )

        duration_val = float(route["duration_minutes"])
        distance_val = float(route["distance_km"])
        has_toll = route.get("has_toll", False)

        norm_scenic = _normalise(
            scenic_val, min_scenic, max_scenic
        )

        norm_time = _normalise(
            duration_val, min_duration, max_duration, invert=True
        )

        norm_distance = _normalise(
            distance_val, min_distance, max_distance, invert=True
        )

        norm_no_toll = 0.0 if has_toll else 1.0

        composite = (
            weights["scenic"] * norm_scenic
            + weights["time"] * norm_time
            + weights["distance"] * norm_distance
            + weights["no_toll"] * norm_no_toll
        )

        route["recommendation_score"] = round(composite * 10, 2)

    # Rank routes from highest to lowest recommendation score.
    routes.sort(
        key=lambda r: r["recommendation_score"],
        reverse=True
    )

    fastest_duration = min(durations)
    best = routes[0]

    # Mark recommendation and fastest-route status.
    for route in routes:
        route["is_recommended"] = route is best
        route["is_fastest"] = (
            float(route["duration_minutes"]) == fastest_duration
        )

    # Generate explanations after ranking.
    for route in routes:
        route["recommendation_reason"] = _build_reason(
            route, routes
        )

    return routes


# --------------------------------------------------
# RECOMMENDATION EXPLANATION
# --------------------------------------------------

def _build_reason(route: dict, all_routes: list[dict]) -> str:
    """Generate a reason using the correct scenic-score scale."""

    parts = []

    scenic = route.get("scenic_score")
    features = route.get("scenic_features") or {}
    environment = features.get("environment", "")

    if route.get("is_recommended"):

        if scenic is not None and len(all_routes) > 1:
            highest_scenic = max(
                float(r.get("scenic_score") or 0)
                for r in all_routes
            )

            if float(scenic) == highest_scenic:
                parts.append(
                    f"strongest scenic score ({float(scenic):.1f}/100)"
                )
            else:
                parts.append(
                    "best overall balance of scenery and efficiency"
                )

        elif route.get("is_fastest"):
            parts.append("fastest and most efficient option")

        else:
            parts.append(
                "best overall balance of scenery and efficiency"
            )

    else:

        if route.get("is_fastest"):
            parts.append("fastest route")

        if not route.get("has_toll"):
            parts.append("avoids tolls")

        if scenic is not None:
            parts.append(
                f"scenic score {float(scenic):.1f}/100"
            )

    if environment and environment not in ("Mixed", "Highway"):
        parts.append(f"{environment.lower()} terrain")

    if not parts:
        parts.append("alternative routing option")

    return "ROAM recommends this for its " + ", ".join(parts) + "."
