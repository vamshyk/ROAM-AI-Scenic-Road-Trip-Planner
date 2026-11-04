"""
ROAM - ML Model Trainer

Trains experimental models using synthetic OSM-like feature data.

IMPORTANT:
The generated target is a synthetic proxy, not human-rated scenic quality.
Reported metrics describe performance on synthetic data only.
"""

from __future__ import annotations

import argparse
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    mean_squared_error,
    mean_absolute_error,
    r2_score,
    accuracy_score,
    f1_score,
    confusion_matrix,
    classification_report,
)
from sklearn.preprocessing import LabelEncoder

from .features import (
    generate_synthetic_dataset,
    FEATURE_NAMES,
    FEATURE_SCHEMA_VERSION,
    ENVIRONMENT_CLASSES,
    N_FEATURES,
)

MODELS_DIR = Path(__file__).parent.parent.parent / "data" / "models"

REGRESSOR_PATH = MODELS_DIR / "scenic_score_predictor.pkl"
CLASSIFIER_PATH = MODELS_DIR / "environment_classifier.pkl"
ENCODER_PATH = MODELS_DIR / "label_encoder.pkl"
METRICS_PATH = MODELS_DIR / "training_metrics.json"
METADATA_PATH = MODELS_DIR / "model_metadata.json"


def build_regressor() -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=200,
        max_depth=12,
        min_samples_split=10,
        min_samples_leaf=5,
        max_features="sqrt",
        bootstrap=True,
        random_state=42,
        n_jobs=-1,
    )


def build_classifier() -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_split=8,
        min_samples_leaf=4,
        max_features="sqrt",
        class_weight="balanced",
        bootstrap=True,
        random_state=42,
        n_jobs=-1,
    )


def train(n_samples: int = 5000, verbose: bool = True) -> dict:
    if n_samples < 100:
        raise ValueError("Use at least 100 samples for training.")

    if verbose:
        print("=" * 60)
        print("ROAM - Experimental ML Training")
        print("=" * 60)
        print("[DATA] Generating synthetic OSM-like features...")
        print("[WARNING] Targets are synthetic proxies, not real scenic ratings.")

    X, y_score, y_class = generate_synthetic_dataset(
        n_samples=n_samples
    )

    if X.shape[1] != N_FEATURES:
        raise ValueError("Generated feature count does not match schema.")

    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y_class)

    unique_classes, class_counts = np.unique(
        y_encoded, return_counts=True
    )

    stratify_values = (
        y_encoded if class_counts.min() >= 2 else None
    )

    (
        X_train,
        X_test,
        score_train,
        score_test,
        class_train,
        class_test,
    ) = train_test_split(
        X,
        y_score,
        y_encoded,
        test_size=0.20,
        random_state=42,
        stratify=stratify_values,
    )

    if verbose:
        print(f"[DATA] Training rows: {len(X_train)}")
        print(f"[DATA] Test rows: {len(X_test)}")
        print(f"[DATA] Features: {N_FEATURES}")
        print(f"[DATA] Classes: {list(label_encoder.classes_)}")

    # --------------------------------------------------
    # REGRESSION
    # --------------------------------------------------

    if verbose:
        print("\n[TRAIN] Training experimental proxy regressor...")

    regressor = build_regressor()
    regressor.fit(X_train, score_train)

    score_predictions = regressor.predict(X_test)

    rmse = float(np.sqrt(
        mean_squared_error(score_test, score_predictions)
    ))
    mae = float(mean_absolute_error(score_test, score_predictions))
    r2 = float(r2_score(score_test, score_predictions))

    cv_folds = min(5, len(X_train))

    cv_scores = cross_val_score(
        build_regressor(),
        X_train,
        score_train,
        cv=cv_folds,
        scoring="r2",
        n_jobs=1,
    )

    regressor_metrics = {
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "r2": round(r2, 4),
        "cv_r2_mean": round(float(cv_scores.mean()), 4),
        "cv_r2_std": round(float(cv_scores.std()), 4),
        "n_estimators": regressor.n_estimators,
        "feature_importances": {
            name: round(float(importance), 4)
            for name, importance in zip(
                FEATURE_NAMES,
                regressor.feature_importances_,
            )
        },
    }

    if verbose:
        print(f"  RMSE: {rmse:.4f}")
        print(f"  MAE:  {mae:.4f}")
        print(f"  R2:   {r2:.4f}")
        print(
            f"  CV R2: {cv_scores.mean():.4f} "
            f"+/- {cv_scores.std():.4f}"
        )

    # --------------------------------------------------
    # CLASSIFICATION
    # --------------------------------------------------

    if verbose:
        print("\n[TRAIN] Training experimental environment classifier...")

    classifier = build_classifier()
    classifier.fit(X_train, class_train)

    class_predictions = classifier.predict(X_test)

    accuracy = float(
        accuracy_score(class_test, class_predictions)
    )
    f1_macro = float(
        f1_score(
            class_test,
            class_predictions,
            average="macro",
            zero_division=0,
        )
    )
    f1_weighted = float(
        f1_score(
            class_test,
            class_predictions,
            average="weighted",
            zero_division=0,
        )
    )

    class_names = label_encoder.classes_.tolist()

    matrix = confusion_matrix(
        class_test,
        class_predictions,
        labels=np.arange(len(class_names)),
    ).tolist()

    classifier_metrics = {
        "accuracy": round(accuracy, 4),
        "f1_macro": round(f1_macro, 4),
        "f1_weighted": round(f1_weighted, 4),
        "classes": class_names,
        "confusion_matrix": matrix,
        "n_estimators": classifier.n_estimators,
    }

    if verbose:
        print(f"  Accuracy: {accuracy:.4f}")
        print(f"  Macro F1: {f1_macro:.4f}")
        print("\n[REPORT]")
        print(classification_report(
            class_test,
            class_predictions,
            labels=np.arange(len(class_names)),
            target_names=class_names,
            zero_division=0,
        ))

    # --------------------------------------------------
    # SAVE MODELS AND METADATA
    # --------------------------------------------------

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    with open(REGRESSOR_PATH, "wb") as file:
        pickle.dump(regressor, file)

    with open(CLASSIFIER_PATH, "wb") as file:
        pickle.dump(classifier, file)

    with open(ENCODER_PATH, "wb") as file:
        pickle.dump(label_encoder, file)

    metadata = {
        "project": "ROAM",
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "feature_names": FEATURE_NAMES,
        "n_features": N_FEATURES,
        "training_data_source": "synthetic_osm_like_data",
        "target_type": "synthetic_proxy",
        "real_world_validated": False,
        "scenic_quality_ground_truth_available": False,
        "environment_classes": class_names,
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_samples": int(n_samples),
        "random_state": 42,
    }

    with open(METADATA_PATH, "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2)

    metrics = {
        "model_type": "experimental_synthetic_proxy",
        "warning": (
            "Metrics measure performance on synthetic proxy labels only. "
            "They are not real-world scenic quality accuracy."
        ),
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "feature_names": FEATURE_NAMES,
        "n_features": N_FEATURES,
        "regressor": regressor_metrics,
        "classifier": classifier_metrics,
        "training_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "total_samples": int(n_samples),
        "real_world_validated": False,
    }

    with open(METRICS_PATH, "w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2)

    if verbose:
        print("\n[SAVE] Models saved.")
        print(f"[SAVE] Metadata: {METADATA_PATH}")
        print(f"[SAVE] Metrics: {METRICS_PATH}")
        print("\n[DONE] Experimental training completed.")

    return metrics


def plot_feature_importance(metrics: dict):
    importances = (
        metrics.get("regressor", {}).get("feature_importances", {})
    )

    if not importances:
        print("[PLOT] No feature importance data available.")
        return

    sorted_pairs = sorted(
        importances.items(),
        key=lambda item: item[1],
    )

    names = [item[0] for item in sorted_pairs]
    values = [item[1] for item in sorted_pairs]

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.barh(
        names,
        values,
        color="#d6a46b",
        edgecolor="#101411",
    )

    ax.set_xlabel("Feature Importance")
    ax.set_title(
        "ROAM - Experimental Synthetic Proxy Model Feature Importance"
    )

    fig.tight_layout()

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    output_path = MODELS_DIR / "feature_importance.png"

    fig.savefig(
        output_path,
        dpi=120,
        bbox_inches="tight",
        facecolor="#191e19",
        edgecolor="none",
    )

    plt.close(fig)

    print(f"[PLOT] Saved: {output_path}")


def evaluate_existing_models():
    if not METRICS_PATH.exists():
        print("No training metrics found. Train the models first.")
        return

    with open(METRICS_PATH, "r", encoding="utf-8") as file:
        metrics = json.load(file)

    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ROAM experimental ML trainer"
    )

    parser.add_argument(
        "--samples",
        type=int,
        default=5000,
        help="Number of synthetic training samples",
    )

    parser.add_argument(
        "--eval",
        action="store_true",
        help="Display saved training metrics",
    )

    args = parser.parse_args()

    if args.eval:
        evaluate_existing_models()
    else:
        results = train(n_samples=args.samples)
        plot_feature_importance(results)