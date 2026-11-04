
"""
ROAM - Test Suite

Tests for scenic scoring, itinerary generation, recommender,
ML features, and API endpoint smoke tests.

Run with:
    cd backend
    .venv\Scripts\python.exe -m pytest tests/ -v
"""

import sys
from pathlib import Path

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import numpy as np


# --------------------------------------------------
# SCENIC TESTS - CURRENT OSM SCORING SYSTEM
# --------------------------------------------------

class TestScenicScoring:

    def test_scenic_score_returns_valid_result(self):
        """OSM scenic scorer should return a valid result dictionary."""
        from src.scenic import calculate_scenic_score

        route_info = {
            "route_type": "fastest",
            "has_highway": False,
            "has_toll": False,
            "has_ferry": False,
            "distance_km": 150,
        }

        coords = [
            [76.6, 12.3],
            [76.5, 12.5],
            [76.4, 12.7],
        ]

        result = calculate_scenic_score(coords, route_info=route_info)

        assert result is not None
        assert isinstance(result, dict)
        assert "scenic_score" in result
        assert 0 <= result["scenic_score"] <= 100

    def test_scenic_score_uses_local_osm_data(self):
        """Scenic scoring should identify its OSM-based scoring method."""
        from src.scenic import calculate_scenic_score

        coords = [
            [76.6, 12.3],
            [76.5, 12.5],
            [76.4, 12.7],
        ]

        result = calculate_scenic_score(coords)

        assert result is not None
        assert result["scoring_method"] == "local_osm_db"

    def test_scenic_feature_breakdown(self):
        """All four scenic feature scores should be present and valid."""
        from src.scenic import calculate_scenic_score

        coords = [
            [76.6, 12.3],
            [76.5, 12.5],
            [76.4, 12.7],
        ]

        result = calculate_scenic_score(coords)

        assert result is not None

        feature_scores = result["feature_scores"]

        expected_features = {
            "forest_score",
            "water_score",
            "attraction_score",
            "track_score",
        }

        assert expected_features.issubset(feature_scores.keys())

        for name in expected_features:
            assert isinstance(feature_scores[name], (int, float))
            assert 0 <= feature_scores[name] <= 100

    def test_empty_coords_returns_none(self):
        """Empty or insufficient coordinates should return None."""
        from src.scenic import calculate_scenic_score

        assert calculate_scenic_score([]) is None
        assert calculate_scenic_score(None) is None
        assert calculate_scenic_score([[76.6, 12.3]]) is None

    def test_scenic_score_in_valid_range(self):
        """OSM scenic score should always remain within [0, 100]."""
        from src.scenic import calculate_scenic_score

        coords = [
            [76.6, 12.3],
            [76.5, 12.5],
            [76.4, 12.7],
        ]

        result = calculate_scenic_score(coords)

        assert result is not None

        score = result["scenic_score"]

        assert isinstance(score, (int, float))
        assert 0 <= score <= 100

    def test_scenic_result_contains_route_measurements(self):
        """Scenic result should contain route measurement information."""
        from src.scenic import calculate_scenic_score

        coords = [
            [76.6, 12.3],
            [76.5, 12.5],
            [76.4, 12.7],
        ]

        route_info = {"distance_km": 150}

        result = calculate_scenic_score(coords, route_info=route_info)

        assert result is not None
        assert result["route_length_km"] > 0
        assert result["routing_distance_km"] == 150
        assert "geometry_distance_difference_km" in result


# --------------------------------------------------
# RECOMMENDER TESTS
# --------------------------------------------------

class TestRecommender:

    def _make_routes(self):
        """Create sample routes for testing."""
        return [
            {
                "name": "Fastest Route",
                "route_type": "fastest",
                "distance_km": 150.0,
                "duration_minutes": 180.0,
                "has_toll": False,
                "has_highway": True,
                "has_ferry": False,
                "scenic_score": 4.5,
                "scenic_features": {"environment": "Highway"},
                "is_recommended": False,
                "is_fastest": True,
            },
            {
                "name": "Scenic Candidate",
                "route_type": "scenic",
                "distance_km": 185.0,
                "duration_minutes": 240.0,
                "has_toll": False,
                "has_highway": False,
                "has_ferry": False,
                "scenic_score": 8.2,
                "scenic_features": {"environment": "Forest"},
                "is_recommended": False,
                "is_fastest": False,
            },
            {
                "name": "Toll-Aware Route",
                "route_type": "toll_aware",
                "distance_km": 155.0,
                "duration_minutes": 195.0,
                "has_toll": False,
                "has_highway": False,
                "has_ferry": False,
                "scenic_score": 5.5,
                "scenic_features": {"environment": "Rural"},
                "is_recommended": False,
                "is_fastest": False,
            },
        ]

    def test_recommender_marks_one_as_recommended(self):
        """Exactly one route should be marked recommended."""
        from src.recommender import score_routes

        routes = self._make_routes()
        result = score_routes(routes, profile="balanced")

        recommended = [r for r in result if r["is_recommended"]]

        assert len(recommended) == 1

    def test_explorer_prefers_scenic(self):
        """Explorer profile should recommend the high-scenic-score route."""
        from src.recommender import score_routes

        routes = self._make_routes()
        result = score_routes(routes, profile="explorer")

        recommended = next(r for r in result if r["is_recommended"])

        assert recommended["scenic_score"] >= 7.0

    def test_efficient_prefers_fast(self):
        """Efficient profile should favour faster routes."""
        from src.recommender import score_routes

        routes = self._make_routes()
        result = score_routes(routes, profile="efficient")

        recommended = next(r for r in result if r["is_recommended"])

        min_duration = min(r["duration_minutes"] for r in result)

        assert recommended["duration_minutes"] <= min_duration * 1.15

    def test_recommendation_reason_is_string(self):
        """All routes should have a string recommendation reason."""
        from src.recommender import score_routes

        routes = self._make_routes()
        result = score_routes(routes, profile="balanced")

        for route in result:
            assert isinstance(route.get("recommendation_reason"), str)
            assert len(route["recommendation_reason"]) > 0

    def test_all_routes_get_scores(self):
        """All routes should receive a numeric recommendation score."""
        from src.recommender import score_routes

        routes = self._make_routes()
        result = score_routes(routes, profile="balanced")

        for route in result:
            assert "recommendation_score" in route
            assert isinstance(route["recommendation_score"], float)
            assert 0 <= route["recommendation_score"] <= 10


# --------------------------------------------------
# ITINERARY TESTS
# --------------------------------------------------

class TestItinerary:

    def _make_route(self):
        return {
            "name": "Fastest Route",
            "distance_km": 150.0,
            "duration_minutes": 180.0,
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [77.5946, 12.9716],
                    [77.2, 12.6],
                    [76.9, 12.5],
                    [76.6394, 12.2958],
                ],
            },
        }

    def test_itinerary_has_correct_day_count(self):
        """Itinerary should have exactly the requested number of days."""
        from src.itinerary import generate_itinerary

        origin = {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "display_name": "Bengaluru",
        }

        destination = {
            "latitude": 12.2958,
            "longitude": 76.6394,
            "display_name": "Mysuru",
        }

        for days in [1, 3, 5]:
            itinerary = generate_itinerary(
                "Bengaluru",
                "Mysuru",
                origin,
                destination,
                self._make_route(),
                days,
                "car",
            )

            assert len(itinerary["days"]) == days

    def test_itinerary_distances_sum_to_total(self):
        """Day distances should approximately sum to total distance."""
        from src.itinerary import generate_itinerary

        origin = {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "display_name": "Bengaluru",
        }

        destination = {
            "latitude": 12.2958,
            "longitude": 76.6394,
            "display_name": "Mysuru",
        }

        itinerary = generate_itinerary(
            "Bengaluru",
            "Mysuru",
            origin,
            destination,
            self._make_route(),
            3,
            "car",
        )

        total_from_days = sum(
            day["distance_km"] for day in itinerary["days"]
        )

        total_route = itinerary["total_distance_km"]

        assert abs(total_from_days - total_route) < 0.5

    def test_last_day_reaches_destination(self):
        """The last day should end at the destination."""
        from src.itinerary import generate_itinerary

        origin = {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "display_name": "Bengaluru",
        }

        destination = {
            "latitude": 12.2958,
            "longitude": 76.6394,
            "display_name": "Mysuru",
        }

        itinerary = generate_itinerary(
            "Bengaluru",
            "Mysuru",
            origin,
            destination,
            self._make_route(),
            2,
            "car",
        )

        last_day = itinerary["days"][-1]

        assert last_day["overnight_stay"]["place_type"] == "destination"

    def test_format_time_helper(self):
        """Time formatter should produce correct output."""
        from src.itinerary import _format_time

        assert _format_time(90) == "1 hr 30 min"
        assert _format_time(60) == "1 hr 0 min"
        assert _format_time(45) == "45 min"
        assert _format_time(0) == "0 min"


# --------------------------------------------------
# ML FEATURE TESTS
# --------------------------------------------------

class TestMLFeatures:

    def test_feature_vector_shape(self):
        """Feature extraction should produce correct shape."""
        from src.ml.features import extract_features, N_FEATURES

        route = {
            "distance_km": 150,
            "has_highway": False,
            "has_toll": False,
            "has_ferry": False,
        }

        features = extract_features(route)

        assert features.shape == (N_FEATURES,)

    def test_feature_values_in_range(self):
        """All feature values should be in [0, 1]."""
        from src.ml.features import extract_features

        route = {
            "distance_km": 600,
            "has_highway": True,
            "has_toll": True,
            "has_ferry": True,
        }

        scenic_data = {
            "feature_breakdown": {
                "forest_fraction": 0.4,
                "water_fraction": 0.2,
                "mountain_fraction": 0.15,
                "farmland_fraction": 0.10,
                "urban_fraction": 0.10,
                "coastal_fraction": 0.05,
            }
        }

        features = extract_features(route, scenic_data)

        assert np.all(features >= 0.0)
        assert np.all(features <= 1.0)

    def test_synthetic_dataset_shape(self):
        """Synthetic dataset should have correct shapes."""
        from src.ml.features import generate_synthetic_dataset, N_FEATURES

        n = 500

        X, y_score, y_class = generate_synthetic_dataset(n_samples=n)

        assert X.shape == (n, N_FEATURES)
        assert y_score.shape == (n,)
        assert y_class.shape == (n,)

    def test_synthetic_scores_in_range(self):
        """Synthetic proxy scores should all be in [0, 10]."""
        from src.ml.features import generate_synthetic_dataset

        _, y_score, _ = generate_synthetic_dataset(n_samples=200)

        assert float(y_score.min()) >= 0.0
        assert float(y_score.max()) <= 10.0

    def test_synthetic_class_labels_are_valid(self):
        """All synthetic class labels should be from the known set."""
        from src.ml.features import (
            generate_synthetic_dataset,
            ENVIRONMENT_CLASSES,
        )

        _, _, y_class = generate_synthetic_dataset(n_samples=300)

        for label in y_class:
            assert label in ENVIRONMENT_CLASSES, f"Unknown class: {label}"


# --------------------------------------------------
# ML TRAINING TESTS
# --------------------------------------------------

class TestMLTraining:

    def test_train_produces_models(self, tmp_path, monkeypatch):
        """Training should produce model files."""
        from src.ml import trainer

        monkeypatch.setattr(trainer, "MODELS_DIR", tmp_path)
        monkeypatch.setattr(trainer, "REGRESSOR_PATH", tmp_path / "reg.pkl")
        monkeypatch.setattr(trainer, "CLASSIFIER_PATH", tmp_path / "cls.pkl")
        monkeypatch.setattr(trainer, "ENCODER_PATH", tmp_path / "enc.pkl")
        monkeypatch.setattr(trainer, "METRICS_PATH", tmp_path / "metrics.json")

        metrics = trainer.train(n_samples=300, verbose=False)

        assert (tmp_path / "reg.pkl").exists()
        assert (tmp_path / "cls.pkl").exists()
        assert (tmp_path / "enc.pkl").exists()

        assert "regressor" in metrics
        assert "classifier" in metrics

    def test_regressor_metrics_are_reasonable(self, tmp_path, monkeypatch):
        """Regressor should achieve R² > 0.7 on synthetic data."""
        from src.ml import trainer

        monkeypatch.setattr(trainer, "MODELS_DIR", tmp_path)
        monkeypatch.setattr(trainer, "REGRESSOR_PATH", tmp_path / "reg.pkl")
        monkeypatch.setattr(trainer, "CLASSIFIER_PATH", tmp_path / "cls.pkl")
        monkeypatch.setattr(trainer, "ENCODER_PATH", tmp_path / "enc.pkl")
        monkeypatch.setattr(trainer, "METRICS_PATH", tmp_path / "metrics.json")

        metrics = trainer.train(n_samples=1000, verbose=False)

        r2 = metrics["regressor"]["r2"]

        assert r2 > 0.70, f"R² {r2} is lower than expected (0.70)"

    def test_classifier_accuracy_is_reasonable(self, tmp_path, monkeypatch):
        """Classifier should achieve > 70% accuracy on synthetic data."""
        from src.ml import trainer

        monkeypatch.setattr(trainer, "MODELS_DIR", tmp_path)
        monkeypatch.setattr(trainer, "REGRESSOR_PATH", tmp_path / "reg.pkl")
        monkeypatch.setattr(trainer, "CLASSIFIER_PATH", tmp_path / "cls.pkl")
        monkeypatch.setattr(trainer, "ENCODER_PATH", tmp_path / "enc.pkl")
        monkeypatch.setattr(trainer, "METRICS_PATH", tmp_path / "metrics.json")

        metrics = trainer.train(n_samples=1000, verbose=False)

        accuracy = metrics["classifier"]["accuracy"]

        assert accuracy > 0.70, (
            f"Accuracy {accuracy} is lower than expected (0.70)"
        )


# --------------------------------------------------
# AI SUMMARY TESTS
# --------------------------------------------------

class TestAISummary:

    def _make_route(self):
        return {
            "name": "Fastest Route",
            "distance_km": 150.0,
            "duration_minutes": 180.0,
            "has_highway": False,
            "has_toll": False,
        }

    def test_fallback_summary_is_string(self):
        """Fallback summary should always return a non-empty string."""
        from src.ai_summary import _build_fallback_summary

        summary = _build_fallback_summary(
            "Bengaluru",
            "Mysuru",
            2,
            "car",
            self._make_route(),
            None,
        )

        assert isinstance(summary, str)
        assert len(summary) > 50

    def test_generate_trip_summary_returns_dict(self):
        """generate_trip_summary should return a dict with summary key."""
        from src.ai_summary import generate_trip_summary

        result = generate_trip_summary(
            "Bengaluru",
            "Mysuru",
            2,
            "car",
            self._make_route(),
        )

        assert "summary" in result
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 20
        assert result["source"] in ("gemini", "fallback")
