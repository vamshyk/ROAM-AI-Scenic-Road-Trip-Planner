
"""
ROAM - Optimized Scenic Feature Engineering

Loads local Karnataka OpenStreetMap datasets and calculates
scenic features using vectorized Shapely spatial-index queries.

Optimisation:
- Uses STRtree dwithin queries instead of buffering the
  entire route and running expensive intersection checks.
- Preserves the original search radii and feature counts.
- Uses complete route geometry.
"""

from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
import shapely

from pyproj import Transformer
from shapely.geometry import LineString
from shapely.strtree import STRtree


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

PROJECT = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:32643",
    always_xy=True
).transform


# --------------------------------------------------
# SCENIC FEATURE ENGINE
# --------------------------------------------------

class ScenicFeatureEngine:

    def __init__(self):
        total_start = perf_counter()

        print("\nLoading ROAM scenic datasets...")

        self.forests = self.load_dataset("forests.csv")
        self.water = self.load_dataset("water_bodies.csv")
        self.tourism = self.load_dataset("tourist_places.csv")
        self.roads = self.load_dataset("roads.csv")

        print("\nBuilding spatial indexes...")

        index_start = perf_counter()

        self.forest_tree = self.build_spatial_index(self.forests)
        self.water_tree = self.build_spatial_index(self.water)
        self.tourism_tree = self.build_spatial_index(self.tourism)
        self.road_tree = self.build_spatial_index(self.roads)

        self.road_values = (
            self.roads["feature_value"]
            .fillna("unknown")
            .astype(str)
            .to_numpy()
        )

        print(
            f"[SCENIC TIMING] Spatial indexes: "
            f"{perf_counter() - index_start:.2f}s"
        )

        print(
            f"[SCENIC TIMING] Engine initialization: "
            f"{perf_counter() - total_start:.2f}s"
        )

        print("Scenic datasets loaded successfully!")

    # --------------------------------------------------
    # LOAD DATASETS
    # --------------------------------------------------

    def load_dataset(self, filename):
        start = perf_counter()

        path = DATA_DIR / filename

        if not path.exists():
            raise FileNotFoundError(
                f"Dataset not found: {path}"
            )

        print(f"Loading {filename}...")

        df = pd.read_csv(path)

        if "geometry_wkt" not in df.columns:
            raise ValueError(
                f"{filename} does not contain geometry_wkt"
            )

        wkt_values = (
            df["geometry_wkt"]
            .fillna("")
            .astype(str)
            .to_numpy()
        )

        geometries = shapely.from_wkt(
            wkt_values,
            on_invalid="ignore"
        )

        valid_mask = (
            ~shapely.is_missing(geometries)
            & ~shapely.is_empty(geometries)
        )

        df = df.loc[valid_mask].copy()
        geometries = geometries[valid_mask]

        projected = shapely.transform(
            geometries,
            PROJECT,
            interleaved=False
        )

        df["geometry"] = list(projected)
        df.reset_index(drop=True, inplace=True)

        print(
            f"{filename}: {len(df):,} valid geometries loaded "
            f"in {perf_counter() - start:.2f}s"
        )

        return df

    # --------------------------------------------------
    # BUILD SPATIAL INDEX
    # --------------------------------------------------

    @staticmethod
    def build_spatial_index(dataframe):
        geometries = dataframe["geometry"].to_numpy()

        if len(geometries) == 0:
            return None

        return STRtree(geometries)

    # --------------------------------------------------
    # CREATE ROUTE GEOMETRY
    # --------------------------------------------------

    @staticmethod
    def create_route(coordinates):
        if coordinates is None or len(coordinates) < 2:
            raise ValueError(
                "A route needs at least two coordinates."
            )

        route = LineString(coordinates)

        return shapely.transform(
            route,
            PROJECT,
            interleaved=False
        )

    # --------------------------------------------------
    # FAST DISTANCE-BASED SPATIAL QUERY
    # --------------------------------------------------

    @staticmethod
    def query_within_distance(tree, route, radius_m):
        """
        Return geometries within radius_m of the route.

        STRtree performs the spatial filtering directly.
        This avoids creating a large route buffer and then
        running a separate vectorized intersection operation.
        """

        if tree is None:
            return np.array([], dtype=np.intp)

        try:
            indices = tree.query(
                route,
                predicate="dwithin",
                distance=radius_m
            )

            return np.asarray(
                indices,
                dtype=np.intp
            )

        except (TypeError, ValueError) as error:
            # Compatibility fallback for GEOS installations
            # that do not support the dwithin predicate.
            print(
                "[SCENIC WARNING] dwithin query unavailable; "
                f"using buffer fallback: {error}"
            )

            search_area = route.buffer(radius_m)

            candidates = tree.query(search_area)

            if len(candidates) == 0:
                return np.array([], dtype=np.intp)

            candidate_geometries = (
                tree.geometries.take(candidates)
            )

            matches = shapely.intersects(
                candidate_geometries,
                search_area
            )

            return np.asarray(
                candidates[matches],
                dtype=np.intp
            )

    # --------------------------------------------------
    # COUNT NEARBY FEATURES
    # --------------------------------------------------

    def nearby_count(self, route, tree, radius_m=500):
        indices = self.query_within_distance(
            tree,
            route,
            radius_m
        )

        return int(len(indices))

    # --------------------------------------------------
    # ROAD TYPE DISTRIBUTION
    # --------------------------------------------------

    def road_distribution(self, route, radius_m=30):
        if self.road_tree is None:
            return {}

        indices = self.query_within_distance(
            self.road_tree,
            route,
            radius_m
        )

        if len(indices) == 0:
            return {}

        nearby_values = self.road_values[indices]

        values, counts = np.unique(
            nearby_values,
            return_counts=True
        )

        return {
            str(value): int(count)
            for value, count in zip(values, counts)
        }

    # --------------------------------------------------
    # CALCULATE ROUTE FEATURES
    # --------------------------------------------------

    def calculate_features(self, coordinates):
        total_start = perf_counter()

        route = self.create_route(coordinates)

        print("Calculating scenic features...")

        start = perf_counter()

        forest_count = self.nearby_count(
            route,
            self.forest_tree,
            radius_m=500
        )

        forest_time = perf_counter() - start

        start = perf_counter()

        water_count = self.nearby_count(
            route,
            self.water_tree,
            radius_m=500
        )

        water_time = perf_counter() - start

        start = perf_counter()

        tourism_count = self.nearby_count(
            route,
            self.tourism_tree,
            radius_m=1000
        )

        tourism_time = perf_counter() - start

        start = perf_counter()

        roads = self.road_distribution(
            route,
            radius_m=30
        )

        road_time = perf_counter() - start

        features = {
            "route_length_km": round(
                route.length / 1000,
                2
            ),
            "nearby_forest_count": forest_count,
            "nearby_water_count": water_count,
            "nearby_tourist_places": tourism_count,
            "road_distribution": roads
        }

        print(
            "[SCENIC TIMING] Feature queries | "
            f"forest={forest_time:.2f}s | "
            f"water={water_time:.2f}s | "
            f"tourism={tourism_time:.2f}s | "
            f"roads={road_time:.2f}s | "
            f"total={perf_counter() - total_start:.2f}s"
        )

        return features


# --------------------------------------------------
# TEST THE FEATURE ENGINE
# --------------------------------------------------

if __name__ == "__main__":

    engine = ScenicFeatureEngine()

    test_coordinates = [
        (77.5946, 12.9716),
        (77.2, 12.7),
        (76.6394, 12.2958)
    ]

    results = engine.calculate_features(
        test_coordinates
    )

    print("\n========== ROAM SCENIC FEATURES ==========")

    for feature, value in results.items():
        print(f"\n{feature}:")
        print(value)

    print("\n========== TEST COMPLETED ==========")
