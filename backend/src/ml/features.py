"""
ROAM - ML Feature Extraction

Versioned features based on measurements available in the local OSM database.

IMPORTANT:
These features describe mapped OSM objects near a route. They do not directly
measure subjective scenic beauty, elevation, mountain coverage or coastline.
"""

from __future__ import annotations

import numpy as np


FEATURE_SCHEMA_VERSION = "2.0"

FEATURE_NAMES = [
    "forest_density_per_10km",
    "water_density_per_10km",
    "tourism_density_per_10km",
    "track_road_ratio",
    "primary_trunk_road_ratio",
    "secondary_tertiary_road_ratio",
    "residential_service_road_ratio",
    "other_road_ratio",
    "has_toll",
    "has_ferry",
    "distance_norm",
]

N_FEATURES = len(FEATURE_NAMES)

ENVIRONMENT_CLASSES = [
    "Forest",
    "Water-Rich",
    "Tourism-Rich",
    "Track-Rich",
    "Highway",
    "Rural",
    "Mixed",
]


def _safe_float(value, default=0.0):
    try:
        result = float(value)
        if np.isfinite(result):
            return result
    except (TypeError, ValueError):
        pass
    return float(default)


def _route_distance_km(route: dict, scenic_data: dict) -> float:
    distance = _safe_float(scenic_data.get("route_length_km"))

    if distance <= 0:
        distance = _safe_float(route.get("distance_km"))

    if distance <= 0:
        distance = _safe_float(route.get("distance"))

    return max(distance, 0.1)


def _road_ratio(road_distribution: dict, categories: set[str]) -> float:
    counts = {
        str(key).lower(): max(_safe_float(value), 0.0)
        for key, value in road_distribution.items()
    }

    total = sum(counts.values())

    if total <= 0:
        return 0.0

    selected = sum(
        count for category, count in counts.items()
        if category in categories
    )

    return float(selected / total)


def _route_flag(route: dict, names: tuple[str, ...]) -> float:
    for name in names:
        value = route.get(name)

        if isinstance(value, bool):
            return float(value)

        if isinstance(value, (int, float)):
            return float(value > 0)

        if isinstance(value, str):
            return float(value.strip().lower() in {
                "true", "yes", "1", "available"
            })

    return 0.0


def extract_features(
    route: dict,
    scenic_data: dict | None = None,
) -> np.ndarray:
    """
    Extract the version 2.0 OSM feature vector.

    scenic_data is the result returned by calculate_scenic_score().
    """

    scenic_data = scenic_data or {}

    distance_km = _route_distance_km(route, scenic_data)

    forest_count = max(
        _safe_float(scenic_data.get("nearby_forest_count")), 0.0
    )
    water_count = max(
        _safe_float(scenic_data.get("nearby_water_count")), 0.0
    )
    tourism_count = max(
        _safe_float(scenic_data.get("nearby_tourist_places")), 0.0
    )

    road_distribution = scenic_data.get("road_distribution") or {}

    if not isinstance(road_distribution, dict):
        road_distribution = {}

    # These are proportions of nearby mapped road objects, not route length.
    track_ratio = _road_ratio(road_distribution, {"track"})
    primary_trunk_ratio = _road_ratio(
        road_distribution, {"primary", "trunk", "trunk_link"}
    )
    secondary_tertiary_ratio = _road_ratio(
        road_distribution, {"secondary", "tertiary", "tertiary_link"}
    )
    residential_service_ratio = _road_ratio(
        road_distribution, {
            "residential", "service", "living_street", "unclassified"
        }
    )

    other_road_ratio = max(
        0.0,
        1.0 - (
            track_ratio
            + primary_trunk_ratio
            + secondary_tertiary_ratio
            + residential_service_ratio
        ),
    )

    features = [
        forest_count / distance_km * 10.0,
        water_count / distance_km * 10.0,
        tourism_count / distance_km * 10.0,
        track_ratio,
        primary_trunk_ratio,
        secondary_tertiary_ratio,
        residential_service_ratio,
        other_road_ratio,
        _route_flag(route, ("has_toll", "toll")),
        _route_flag(route, ("has_ferry", "ferry")),
        min(distance_km / 500.0, 1.0),
    ]

    result = np.asarray(features, dtype=np.float64)

    if result.shape != (N_FEATURES,):
        raise ValueError(
            f"Invalid feature vector shape: {result.shape}; "
            f"expected {(N_FEATURES,)}"
        )

    if not np.all(np.isfinite(result)):
        raise ValueError("Feature vector contains non-finite values.")

    return result


def _classify_environment(features: np.ndarray) -> str:
    """
    Experimental rule-based labels for synthetic training only.

    These labels are not verified real-world environment annotations.
    """

    forest = features[0]
    water = features[1]
    tourism = features[2]
    track = features[3]
    highway = features[4] + features[5]
    residential = features[6]

    if forest >= 2.0:
        return "Forest"
    if water >= 1.5:
        return "Water-Rich"
    if tourism >= 1.5:
        return "Tourism-Rich"
    if track >= 0.18:
        return "Track-Rich"
    if highway >= 0.35:
        return "Highway"
    if residential >= 0.65:
        return "Rural"

    return "Mixed"


def _synthetic_proxy_score(features: np.ndarray) -> float:
    """
    Generate an explicitly synthetic proxy target.

    This is not a ground-truth scenic quality score.
    """

    forest = min(features[0] / 5.0, 1.0)
    water = min(features[1] / 4.0, 1.0)
    tourism = min(features[2] / 3.0, 1.0)
    track = features[3]
    highway = features[4] + features[5]
    residential = features[6]

    score = (
        3.0
        + 2.0 * forest
        + 1.2 * water
        + 0.8 * tourism
        + 1.0 * track
        - 1.0 * highway
        - 0.5 * residential
    )

    return float(np.clip(score, 0.5, 9.8))


def generate_synthetic_dataset(
    n_samples: int = 5000,
    random_state: int = 42,
):
    """
    Generate synthetic feature vectors and proxy labels.

    Use only for testing the ML pipeline. Metrics from this dataset must
    never be described as real-world scenic prediction accuracy.
    """

    if n_samples < 100:
        raise ValueError("At least 100 synthetic samples are required.")

    rng = np.random.default_rng(random_state)

    X = np.zeros((n_samples, N_FEATURES), dtype=np.float64)

    # Simulated OSM feature densities.
    X[:, 0] = rng.gamma(shape=1.5, scale=1.4, size=n_samples)
    X[:, 1] = rng.gamma(shape=1.2, scale=0.9, size=n_samples)
    X[:, 2] = rng.gamma(shape=1.1, scale=0.8, size=n_samples)

    # Simulated nearby road-category proportions.
    road_profiles = rng.dirichlet(
        alpha=[1.2, 1.5, 2.0, 3.0, 1.5],
        size=n_samples,
    )

    X[:, 3:8] = road_profiles

    X[:, 8] = rng.binomial(1, 0.15, size=n_samples)
    X[:, 9] = rng.binomial(1, 0.03, size=n_samples)
    X[:, 10] = rng.uniform(0.05, 1.0, size=n_samples)

    # Add small variation to avoid perfectly repeated examples.
    X[:, :3] += rng.normal(0, 0.05, size=(n_samples, 3))
    X[:, :3] = np.clip(X[:, :3], 0, None)

    y_score = np.asarray([
        _synthetic_proxy_score(row) for row in X
    ])

    y_score += rng.normal(0, 0.35, size=n_samples)
    y_score = np.clip(y_score, 0.5, 9.8)

    y_class = np.asarray([
        _classify_environment(row) for row in X
    ])

    return X, y_score, y_class