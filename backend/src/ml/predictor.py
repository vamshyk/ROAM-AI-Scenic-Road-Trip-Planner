"""
ROAM - ML Model Predictor

Loads only models trained with the current feature schema.
ML predictions remain experimental and never replace the primary OSM score.
"""

from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Optional

import numpy as np

from .features import (
    extract_features,
    FEATURE_NAMES,
    FEATURE_SCHEMA_VERSION,
    N_FEATURES,
)

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent.parent.parent / "data" / "models"

REGRESSOR_PATH = MODELS_DIR / "scenic_score_predictor.pkl"
CLASSIFIER_PATH = MODELS_DIR / "environment_classifier.pkl"
ENCODER_PATH = MODELS_DIR / "label_encoder.pkl"
METADATA_PATH = MODELS_DIR / "model_metadata.json"

_regressor = None
_classifier = None
_label_encoder = None
_models_loaded = False
_models_valid = False


def _load_models() -> bool:
    global _regressor, _classifier, _label_encoder
    global _models_loaded, _models_valid

    if _models_loaded:
        return _models_valid

    _models_loaded = True
    _models_valid = False

    required_files = [
        REGRESSOR_PATH,
        CLASSIFIER_PATH,
        ENCODER_PATH,
        METADATA_PATH,
    ]

    if not all(path.exists() for path in required_files):
        logger.info(
            "ROAM ML models are unavailable or have no version metadata."
        )
        return False

    try:
        with open(METADATA_PATH, "r", encoding="utf-8") as file:
            metadata = json.load(file)

        if metadata.get("feature_schema_version") != FEATURE_SCHEMA_VERSION:
            logger.warning("ROAM ML feature schema version mismatch.")
            return False

        if metadata.get("feature_names") != FEATURE_NAMES:
            logger.warning("ROAM ML feature names do not match current schema.")
            return False

        if metadata.get("n_features") != N_FEATURES:
            logger.warning("ROAM ML feature count mismatch.")
            return False

        with open(REGRESSOR_PATH, "rb") as file:
            regressor = pickle.load(file)

        with open(CLASSIFIER_PATH, "rb") as file:
            classifier = pickle.load(file)

        with open(ENCODER_PATH, "rb") as file:
            label_encoder = pickle.load(file)

        if getattr(regressor, "n_features_in_", None) != N_FEATURES:
            logger.warning("Regressor input feature count is incompatible.")
            return False

        if getattr(classifier, "n_features_in_", None) != N_FEATURES:
            logger.warning("Classifier input feature count is incompatible.")
            return False

        _regressor = regressor
        _classifier = classifier
        _label_encoder = label_encoder
        _models_valid = True

        logger.info("ROAM ML models loaded with schema %s.", FEATURE_SCHEMA_VERSION)
        return True

    except Exception:
        logger.exception("Could not load ROAM ML models.")
        _regressor = None
        _classifier = None
        _label_encoder = None
        return False


def models_available() -> bool:
    """Return True only when current-schema models load successfully."""
    return _load_models()


def _get_feature_vector(route: dict, scenic_data: Optional[dict]):
    try:
        features = extract_features(route, scenic_data)

        if features.shape != (N_FEATURES,):
            raise ValueError("Unexpected feature vector shape.")

        return features.reshape(1, -1)

    except Exception:
        logger.exception("ROAM could not extract ML features.")
        return None


def predict_scenic_score(
    route: dict,
    scenic_data: Optional[dict] = None,
) -> Optional[float]:

    if not _load_models() or _regressor is None:
        return None

    features = _get_feature_vector(route, scenic_data)
    if features is None:
        return None

    try:
        prediction = float(_regressor.predict(features)[0])
        return round(float(np.clip(prediction, 0.5, 10.0)), 1)
    except Exception:
        logger.exception("ROAM scenic score prediction failed.")
        return None


def predict_environment(
    route: dict,
    scenic_data: Optional[dict] = None,
) -> Optional[str]:

    if not _load_models() or _classifier is None or _label_encoder is None:
        return None

    features = _get_feature_vector(route, scenic_data)
    if features is None:
        return None

    try:
        class_index = _classifier.predict(features)[0]
        return str(_label_encoder.inverse_transform([class_index])[0])
    except Exception:
        logger.exception("ROAM environment prediction failed.")
        return None


def predict_environment_probabilities(
    route: dict,
    scenic_data: Optional[dict] = None,
) -> Optional[dict[str, float]]:

    if not _load_models() or _classifier is None or _label_encoder is None:
        return None

    features = _get_feature_vector(route, scenic_data)
    if features is None:
        return None

    try:
        probabilities = _classifier.predict_proba(features)[0]
        classes = _label_encoder.classes_

        return {
            str(label): round(float(probability), 3)
            for label, probability in sorted(
                zip(classes, probabilities),
                key=lambda item: item[1],
                reverse=True,
            )
        }

    except Exception:
        logger.exception("ROAM environment probability prediction failed.")
        return None


def enhance_route_with_ml(route: dict) -> dict:
    """
    Add experimental ML outputs without changing the primary OSM score.
    """

    scenic_data = route.get("scenic_features") or {}

    ml_score = predict_scenic_score(route, scenic_data)
    ml_environment = predict_environment(route, scenic_data)
    ml_probabilities = predict_environment_probabilities(
        route, scenic_data
    )

    route["ml_scenic_score"] = ml_score
    route["ml_environment"] = ml_environment
    route["ml_env_probs"] = ml_probabilities
    route["ml_status"] = (
        "experimental_prediction"
        if ml_score is not None or ml_environment is not None
        else "unavailable"
    )

    # Deliberately do not overwrite route["scenic_score"].
    return route