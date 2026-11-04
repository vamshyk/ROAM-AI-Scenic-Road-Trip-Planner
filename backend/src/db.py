
"""
ROAM - Database Manager

Read-only access to the local Karnataka OSM SQLite database.
Supports spatial feature, POI, and route-aware settlement queries.
"""

import math
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "karnataka.db"

QUERY_RADIUS_DEG = 0.045
SETTLEMENT_RADIUS_DEG = 0.18


def is_db_available() -> bool:
    """Check whether the local OSM database exists."""
    return DB_PATH.exists() and DB_PATH.stat().st_size > 1000


def get_connection() -> sqlite3.Connection:
    """Return a read-only SQLite connection."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _haversine_km(lon1, lat1, lon2, lat2):
    """Calculate the distance between two geographic coordinates."""
    radius = 6371.0

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    delta_lat = lat2_rad - lat1_rad
    delta_lon = math.radians(lon2 - lon1)

    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2) ** 2
    )

    value = max(0.0, min(1.0, value))

    return radius * 2 * math.atan2(
        math.sqrt(value),
        math.sqrt(1 - value)
    )


def _bounding_box(lat, lon, radius_km):
    """Convert a kilometre radius into a geographic bounding box."""
    lat_radius = radius_km / 111.0

    cos_lat = max(abs(math.cos(math.radians(lat))), 0.1)
    lon_radius = radius_km / (111.0 * cos_lat)

    return (
        lat - lat_radius,
        lat + lat_radius,
        lon - lon_radius,
        lon + lon_radius,
    )


def query_features_near(
    lat: float,
    lon: float,
    radius_deg: float = QUERY_RADIUS_DEG
) -> list[dict]:
    """Return geographic features within a bounding box."""

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT feature_type, name
            FROM geo_features
            WHERE lat BETWEEN ? AND ?
              AND lon BETWEEN ? AND ?
            """,
            (
                lat - radius_deg,
                lat + radius_deg,
                lon - radius_deg,
                lon + radius_deg,
            )
        ).fetchall()

    return [dict(row) for row in rows]


def query_pois_near(
    lat: float,
    lon: float,
    poi_types: list[str],
    radius_deg: float = QUERY_RADIUS_DEG
) -> list[dict]:
    """Return POIs of requested types within a bounding box."""

    if not poi_types:
        return []

    placeholders = ",".join("?" for _ in poi_types)

    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT poi_type, name, lat, lon
            FROM pois
            WHERE poi_type IN ({placeholders})
              AND lat BETWEEN ? AND ?
              AND lon BETWEEN ? AND ?
            ORDER BY poi_type, name
            """,
            (
                *poi_types,
                lat - radius_deg,
                lat + radius_deg,
                lon - radius_deg,
                lon + radius_deg,
            )
        ).fetchall()

    return [dict(row) for row in rows]


def query_settlements_near(
    lat: float,
    lon: float,
    radius_deg: float = SETTLEMENT_RADIUS_DEG
) -> list[dict]:
    """Return settlements near a geographic coordinate."""

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT name, place_type, lat, lon, population
            FROM settlements
            WHERE lat BETWEEN ? AND ?
              AND lon BETWEEN ? AND ?
            ORDER BY
                CASE place_type
                    WHEN 'city' THEN 1
                    WHEN 'town' THEN 2
                    WHEN 'village' THEN 3
                    ELSE 4
                END,
                population DESC NULLS LAST
            LIMIT 100
            """,
            (
                lat - radius_deg,
                lat + radius_deg,
                lon - radius_deg,
                lon + radius_deg,
            )
        ).fetchall()

    return [dict(row) for row in rows]


def query_settlements_along_route(
    route_samples: list[tuple[float, float, float]],
    radius_km: float = 15.0,
    max_candidates: int = 500,
) -> list[dict]:
    """
    Find mapped settlements near sampled route coordinates.

    Each route sample is:
        (longitude, latitude, cumulative_route_distance_km)

    The returned route distance is approximate, based on the nearest
    sampled route coordinate. It is intended for itinerary planning,
    not navigation.
    """

    if not route_samples or radius_km <= 0:
        return []

    if not is_db_available():
        return []

    candidates = {}

    try:
        with get_connection() as conn:

            for lon, lat, route_distance in route_samples:

                min_lat, max_lat, min_lon, max_lon = _bounding_box(
                    lat,
                    lon,
                    radius_km
                )

                rows = conn.execute(
                    """
                    SELECT name, place_type, lat, lon, population
                    FROM settlements
                    WHERE lat BETWEEN ? AND ?
                      AND lon BETWEEN ? AND ?
                    LIMIT 500
                    """,
                    (min_lat, max_lat, min_lon, max_lon)
                ).fetchall()

                for row in rows:
                    settlement = dict(row)

                    name = settlement.get("name")
                    settlement_lat = settlement.get("lat")
                    settlement_lon = settlement.get("lon")

                    if (
                        not name
                        or settlement_lat is None
                        or settlement_lon is None
                    ):
                        continue

                    distance_from_route = _haversine_km(
                        lon,
                        lat,
                        settlement_lon,
                        settlement_lat
                    )

                    if distance_from_route > radius_km:
                        continue

                    key = (
                        str(name).strip().lower(),
                        round(float(settlement_lat), 5),
                        round(float(settlement_lon), 5),
                    )

                    existing = candidates.get(key)

                    if (
                        existing is None
                        or distance_from_route
                        < existing["distance_from_route_km"]
                    ):
                        settlement["route_distance_km"] = float(
                            route_distance
                        )

                        settlement["distance_from_route_km"] = (
                            distance_from_route
                        )

                        candidates[key] = settlement

        results = list(candidates.values())

        results.sort(
            key=lambda item: (
                item["distance_from_route_km"],
                -int(item.get("population") or 0)
            )
        )

        return results[:max_candidates]

    except sqlite3.Error as error:
        print(
            f"[DATABASE] Route settlement lookup warning: {error}"
        )
        return []


def query_pois_along_route(
    route_samples: list[tuple[float, float]],
    poi_types: list[str],
    radius_deg: float = 0.06
) -> list[dict]:
    """
    Find and deduplicate POIs around sampled route coordinates.

    Each sample is (longitude, latitude).
    """

    if not route_samples or not poi_types:
        return []

    if not is_db_available():
        return []

    placeholders = ",".join("?" for _ in poi_types)

    seen = set()
    results = []

    try:
        with get_connection() as conn:

            for lon, lat in route_samples:

                rows = conn.execute(
                    f"""
                    SELECT poi_type, name, lat, lon
                    FROM pois
                    WHERE poi_type IN ({placeholders})
                      AND lat BETWEEN ? AND ?
                      AND lon BETWEEN ? AND ?
                    ORDER BY poi_type, name
                    """,
                    (
                        *poi_types,
                        lat - radius_deg,
                        lat + radius_deg,
                        lon - radius_deg,
                        lon + radius_deg,
                    )
                ).fetchall()

                for row in rows:
                    poi = dict(row)

                    key = (
                        str(poi.get("name") or "").strip().lower(),
                        poi.get("poi_type"),
                        round(float(poi["lat"]), 5),
                        round(float(poi["lon"]), 5),
                    )

                    if key in seen:
                        continue

                    seen.add(key)
                    results.append(poi)

        return results

    except sqlite3.Error as error:
        print(f"[DATABASE] Route POI lookup warning: {error}")
        return []
