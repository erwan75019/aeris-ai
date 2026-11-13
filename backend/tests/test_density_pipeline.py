import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.app.providers.demo import DemoFlightProvider
from backend.app.services.density import DensityService
from backend.app.services.flights import FlightService
from backend.ml.artifacts import ArtifactIntegrityError
from backend.ml.density import (
    FEATURE_NAMES,
    HORIZONS_MINUTES,
    density_feature_vector,
    generate_density_dataset,
)
from backend.ml.density_artifacts import DensityArtifact
from backend.ml.train_density import DensityTrainingConfig, train_density


def test_density_dataset_is_time_ordered_and_feature_safe() -> None:
    dataset = generate_density_dataset(days=21, seed=4)

    assert dataset.timestamps == sorted(dataset.timestamps)
    assert dataset.inputs.shape[1] == len(FEATURE_NAMES)
    assert dataset.targets.shape[1] == len(HORIZONS_MINUTES)
    assert len(dataset.timestamps) == len(dataset.inputs) == len(dataset.targets)


def test_density_features_require_aware_time() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        density_feature_vector(
            datetime(2025, 1, 1),
            current_aircraft=4,
            lag_15m_aircraft=3,
            lag_30m_aircraft=5,
            rolling_60m_aircraft=4,
        )


def test_density_training_promotes_integrity_checked_model(tmp_path: Path) -> None:
    manifest = train_density(
        tmp_path,
        DensityTrainingConfig(days=30, estimators=40, max_depth=10),
    )
    artifact = DensityArtifact(tmp_path)
    forecast = artifact.predict(
        datetime(2025, 1, 15, 13, tzinfo=UTC),
        current_aircraft=4,
        lag_15m_aircraft=4,
        lag_30m_aircraft=4,
        rolling_60m_aircraft=4,
    )

    assert manifest["promotion_status"] == "promoted_for_synthetic_demo"
    assert len(forecast.predictions) == len(HORIZONS_MINUTES)
    assert all(value >= 0 for value in forecast.predictions)
    assert forecast.metrics["mean_mae_aircraft"] > 0


def test_density_artifact_rejects_checksum_mismatch(tmp_path: Path) -> None:
    train_density(tmp_path, DensityTrainingConfig(days=30, estimators=20, max_depth=8))
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match="checksum"):
        DensityArtifact(tmp_path)


def test_density_service_has_explicit_persistence_fallback(tmp_path: Path) -> None:
    service = DensityService(FlightService(DemoFlightProvider()), tmp_path / "missing")

    response = service.forecast()

    assert response.current_aircraft == 4
    assert response.model.name == "persistence_baseline"
    assert response.model.trained is False
    assert all(point.predicted_aircraft == 4 for point in response.points)
    assert "not a trained" in response.disclaimer


def test_density_dataset_rejects_short_periods() -> None:
    with pytest.raises(ValueError, match="At least 21 days"):
        generate_density_dataset(days=10)
