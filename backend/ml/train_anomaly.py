"""Train and evaluate a deterministic Isolation Forest anomaly model."""

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import joblib  # type: ignore[import-untyped]
import numpy as np
from sklearn.ensemble import IsolationForest  # type: ignore[import-untyped]
from sklearn.metrics import (  # type: ignore[import-untyped]
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

from backend.ml.artifacts import sha256_file
from backend.ml.features import FEATURE_NAMES, track_feature_vector
from backend.ml.synthetic import LabeledTrack, generate_labeled_tracks


@dataclass(frozen=True)
class TrainingConfig:
    seed: int = 42
    track_count: int = 180
    estimators: int = 240
    model_version: str = "1.0.0"
    dataset_id: str = "synthetic-injected-v1"


def _matrix(tracks: list[LabeledTrack]) -> tuple[np.ndarray, np.ndarray]:
    return (
        np.vstack([track_feature_vector(item.states) for item in tracks]),
        np.asarray([item.is_injected_anomaly for item in tracks], dtype=np.int64),
    )


def _best_threshold(scores: np.ndarray, labels: np.ndarray) -> float:
    candidates = np.unique(scores)
    ranked = sorted(
        (
            (f1_score(labels, scores >= threshold, zero_division=0), threshold)
            for threshold in candidates
        ),
        key=lambda item: (item[0], item[1]),
    )
    return float(ranked[-1][1])


def _metrics(labels: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, float]:
    predictions = scores >= threshold
    tn, fp, _fn, _tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    return {
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "false_positive_rate": float(fp / (fp + tn)) if fp + tn else 0.0,
        "roc_auc": float(roc_auc_score(labels, scores)),
        "pr_auc": float(average_precision_score(labels, scores)),
    }


def train(output_dir: Path, config: TrainingConfig = TrainingConfig()) -> dict[str, object]:
    """Train on past flights, tune on later flights, and evaluate once on the latest flights."""

    tracks = generate_labeled_tracks(count=config.track_count, seed=config.seed)
    train_end = int(len(tracks) * 0.60)
    validation_end = int(len(tracks) * 0.80)
    training, validation, testing = (
        tracks[:train_end],
        tracks[train_end:validation_end],
        tracks[validation_end:],
    )
    train_x, train_y = _matrix(training)
    validation_x, validation_y = _matrix(validation)
    test_x, test_y = _matrix(testing)
    pipeline = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                IsolationForest(
                    n_estimators=config.estimators,
                    contamination="auto",
                    random_state=config.seed,
                    n_jobs=1,
                ),
            ),
        ]
    )
    pipeline.fit(train_x[train_y == 0])
    validation_scores = -pipeline.decision_function(validation_x)
    threshold = _best_threshold(validation_scores, validation_y)
    test_scores = -pipeline.decision_function(test_x)
    metrics = _metrics(test_y, test_scores, threshold)
    promoted = (
        metrics["f1"] >= 0.80
        and metrics["roc_auc"] >= 0.90
        and metrics["false_positive_rate"] <= 0.15
    )
    score_scale = float(max(np.std(validation_scores), 0.01))

    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "model.joblib"
    joblib.dump(
        {"pipeline": pipeline, "threshold": threshold, "score_scale": score_scale},
        model_path,
        compress=3,
    )
    manifest: dict[str, object] = {
        "model_name": "isolation_forest",
        "model_version": config.model_version,
        "trained": True,
        "trained_at": datetime.now(UTC).isoformat(),
        "artifact_sha256": sha256_file(model_path),
        "feature_names": list(FEATURE_NAMES),
        "dataset_id": config.dataset_id,
        "data_classification": "synthetic_simulation",
        "config": asdict(config),
        "split_policy": "chronological 60/20/20 with flight-disjoint tracks",
        "split_counts": {
            "train": len(training),
            "validation": len(validation),
            "test": len(testing),
        },
        "threshold": threshold,
        "test_metrics": metrics,
        "promotion_status": "promoted_for_synthetic_demo" if promoted else "rejected",
        "limitations": [
            "Evaluation labels are injected synthetic scenarios, not documented incidents.",
            "The model is not calibrated for operational or safety-critical decisions.",
            "A statistical outlier does not establish danger, intent, or causality.",
        ],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/models/anomaly"),
        help="Artifact directory",
    )
    args = parser.parse_args()
    print(json.dumps(train(args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
