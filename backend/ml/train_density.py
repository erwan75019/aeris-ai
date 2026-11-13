"""Train and evaluate a deterministic traffic-density Random Forest."""

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import joblib  # type: ignore[import-untyped]
import numpy as np
from sklearn.ensemble import RandomForestRegressor  # type: ignore[import-untyped]
from sklearn.metrics import mean_absolute_error, mean_squared_error  # type: ignore[import-untyped]

from backend.ml.artifacts import sha256_file
from backend.ml.density import FEATURE_NAMES, HORIZONS_MINUTES, generate_density_dataset


@dataclass(frozen=True)
class DensityTrainingConfig:
    seed: int = 91
    days: int = 120
    estimators: int = 120
    max_depth: int = 12
    model_version: str = "1.0.0"
    dataset_id: str = "synthetic-density-v1"


def _metrics(targets: np.ndarray, predictions: np.ndarray) -> dict[str, float]:
    values: dict[str, float] = {}
    for index, horizon in enumerate(HORIZONS_MINUTES):
        values[f"mae_aircraft_{horizon}m"] = float(
            mean_absolute_error(targets[:, index], predictions[:, index])
        )
        values[f"rmse_aircraft_{horizon}m"] = float(
            np.sqrt(mean_squared_error(targets[:, index], predictions[:, index]))
        )
    values["mean_mae_aircraft"] = float(
        np.mean([values[f"mae_aircraft_{horizon}m"] for horizon in HORIZONS_MINUTES])
    )
    return values


def train_density(
    output_dir: Path,
    config: DensityTrainingConfig = DensityTrainingConfig(),
) -> dict[str, object]:
    """Train chronologically, validate promotion, then evaluate once on the latest window."""

    dataset = generate_density_dataset(days=config.days, seed=config.seed)
    train_end = int(len(dataset.inputs) * 0.60)
    validation_end = int(len(dataset.inputs) * 0.80)
    train_x, train_y = dataset.inputs[:train_end], dataset.targets[:train_end]
    validation_x, validation_y = (
        dataset.inputs[train_end:validation_end],
        dataset.targets[train_end:validation_end],
    )
    test_x, test_y = dataset.inputs[validation_end:], dataset.targets[validation_end:]
    model = RandomForestRegressor(
        n_estimators=config.estimators,
        max_depth=config.max_depth,
        min_samples_leaf=3,
        random_state=config.seed,
        n_jobs=1,
    )
    model.fit(train_x, train_y)
    validation_metrics = _metrics(validation_y, model.predict(validation_x))
    validation_persistence = np.repeat(validation_x[:, 4:5], len(HORIZONS_MINUTES), axis=1)
    validation_baseline_metrics = _metrics(validation_y, validation_persistence)
    test_predictions = model.predict(test_x)
    test_metrics = _metrics(test_y, test_predictions)
    persistence_predictions = np.repeat(test_x[:, 4:5], len(HORIZONS_MINUTES), axis=1)
    baseline_metrics = _metrics(test_y, persistence_predictions)
    promoted = (
        validation_metrics["mean_mae_aircraft"] < validation_baseline_metrics["mean_mae_aircraft"]
        and test_metrics["mean_mae_aircraft"] < baseline_metrics["mean_mae_aircraft"]
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "model.joblib"
    joblib.dump(model, model_path, compress=3)
    manifest: dict[str, object] = {
        "model_name": "random_forest_density",
        "model_version": config.model_version,
        "trained": True,
        "trained_at": datetime.now(UTC).isoformat(),
        "artifact_sha256": sha256_file(model_path),
        "feature_names": list(FEATURE_NAMES),
        "horizons_minutes": list(HORIZONS_MINUTES),
        "dataset_id": config.dataset_id,
        "data_classification": "synthetic_simulation",
        "config": asdict(config),
        "split_policy": "chronological 60/20/20 over one synthetic regional time series",
        "split_counts": {
            "train": len(train_x),
            "validation": len(validation_x),
            "test": len(test_x),
        },
        "validation_metrics": validation_metrics,
        "persistence_baseline_validation_metrics": validation_baseline_metrics,
        "test_metrics": test_metrics,
        "persistence_baseline_test_metrics": baseline_metrics,
        "promotion_status": "promoted_for_synthetic_demo" if promoted else "rejected",
        "limitations": [
            "Training and evaluation counts are synthetic, not measured sector demand.",
            "The prediction is an experimental regional count, not a capacity or safety limit.",
            "Test MAE is not calibrated uncertainty for live operations.",
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
        default=Path("artifacts/models/density"),
        help="Artifact directory",
    )
    args = parser.parse_args()
    print(json.dumps(train_density(args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
