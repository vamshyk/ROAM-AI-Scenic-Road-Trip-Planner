
"""
ROAM - Local Scenic Intelligence

Uses complete route geometry and local Karnataka
OpenStreetMap datasets to calculate scenic features.
"""

from functools import lru_cache
from time import perf_counter

from .scenic_features import ScenicFeatureEngine


@lru_cache(maxsize=1)
def get_scenic_engine():
    """Load the scenic engine once and reuse it."""
    return ScenicFeatureEngine()


def calculate_scenic_score(coordinates, route_info=None):
    """
    Calculate scenic features and the initial heuristic score.

    Coordinates must be in (longitude, latitude) order.
    Complete route geometry should be supplied.
    """

    total_start = perf_counter()

    try:
        if coordinates is None or len(coordinates) < 2:
            return None

        engine = get_scenic_engine()
        features = engine.calculate_features(coordinates)

        route_length = features["route_length_km"]

        if route_length <= 0:
            return None

        routing_distance = None
        distance_difference = None
        distance_difference_percent = None

        if route_info:
            routing_distance = route_info.get("distance_km")

            if routing_distance is not None:
                routing_distance = float(routing_distance)

                distance_difference = round(
                    route_length - routing_distance, 2
                )

                if routing_distance > 0:
                    distance_difference_percent = round(
                        abs(distance_difference)
                        / routing_distance * 100,
                        2
                    )

        forest_density = (
            features["nearby_forest_count"] / route_length
        )

        water_density = (
            features["nearby_water_count"] / route_length
        )

        attraction_density = (
            features["nearby_tourist_places"] / route_length
        )

        road_distribution = features["road_distribution"]
        total_roads = sum(road_distribution.values())

        track_ratio = (
            road_distribution.get("track", 0) / total_roads
            if total_roads > 0
            else 0
        )

        # Preserve the existing heuristic scoring formula.
        forest_score = min(forest_density / 5, 1) * 40
        water_score = min(water_density / 2, 1) * 25

        attraction_score = min(
            attraction_density / 1.5, 1
        ) * 20

        track_score = min(
            track_ratio / 0.15, 1
        ) * 15

        scenic_score = round(
            forest_score
            + water_score
            + attraction_score
            + track_score,
            1
        )

        result = {
            "scenic_score": min(scenic_score, 100),
            "scoring_method": "local_osm_db",

            "route_length_km": route_length,
            "routing_distance_km": routing_distance,

            "geometry_distance_difference_km": (
                distance_difference
            ),

            "geometry_distance_difference_percent": (
                distance_difference_percent
            ),

            "nearby_forest_count": features[
                "nearby_forest_count"
            ],

            "nearby_water_count": features[
                "nearby_water_count"
            ],

            "nearby_tourist_places": features[
                "nearby_tourist_places"
            ],

            "road_distribution": road_distribution,

            "feature_scores": {
                "forest_score": round(forest_score, 2),
                "water_score": round(water_score, 2),
                "attraction_score": round(attraction_score, 2),
                "track_score": round(track_score, 2)
            }
        }

        print(
            "[SCENIC DISTANCE CHECK] "
            f"Geometry={route_length:.2f} km | "
            f"Routing={routing_distance} km | "
            f"Difference={distance_difference} km"
        )

        print(
            f"[SCENIC TIMING] Complete scoring call: "
            f"{perf_counter() - total_start:.2f}s"
        )

        return result

    except Exception as error:
        print(f"Scenic evaluation error: {error}")
        return None
