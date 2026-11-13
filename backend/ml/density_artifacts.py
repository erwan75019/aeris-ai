"""Integrity-checked traffic-density model inference."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib  # type: ignore[import-untyped]
import numpy as np
from sklearn.ensemble import RandomForestRegressor  # type: ignore[import-untyped]

from backend.ml.artifacts import ArtifactIntegrityError, sha256_file
from backend.ml.density import FEATURE_NAMES, HORIZONS_MINUTES, density_feature_vector


@dataclass(frozen=True)
class DensityForecast:
    predictions: tuple[float, ...]
    model_name: str
    model_version: str
    metrics: dict[str, float]


class DensityArtifact:
    """Load and serve a checksum-verified, promotion-gated density model."""

    def __init__(self, directory: Path) -> None:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        model_path = directory / "model.joblib"
        if manifest["artifact_sha256"] != sha256_file(model_path):
            raise ArtifactIntegrityError("Density model checksum does not match manifest")
        if tuple(manifest["feature_names"]) != FEATURE_NAMES:
            raise ArtifactIntegrityError("Density feature contract is incompatible")
        if tuple(manifest["horizons_minutes"]) != HORIZONS_MINUTES:
            raise ArtifactIntegrityError("Density horizon contract is incompatible")
        if manifest.get("promotion_status") != "promoted_for_synthetic_demo":
            raise ArtifactIntegrityError(
                "Density model did not pass synthetic-demo promotion gates"
            )
        self.model: RandomForestRegressor = joblib.load(model_path)
        self.model_name = str(manifest["model_name"])
        self.model_version = str(manifest["model_version"])
        metrics: dict[str, Any] = manifest["test_metrics"]
        self.metrics = {name: float(value) for name, value in metrics.items()}

    def predict(
        self,
        timestamp: datetime,
        *,
        current_aircraft: int,
        lag_15m_aircraft: int,
        lag_30m_aircraft: int,
        rolling_60m_aircraft: float,
    ) -> DensityForecast:
        features = density_feature_vector(
            timestamp,
            current_aircraft=current_aircraft,
            lag_15m_aircraft=lag_15m_aircraft,
            lag_30m_aircraft=lag_30m_aircraft,
            rolling_60m_aircraft=rolling_60m_aircraft,
        )
        values = np.maximum(0.0, self.model.predict(features.reshape(1, -1))[0])
        return DensityForecast(
            predictions=tuple(float(value) for value in values),
            model_name=self.model_name,
            model_version=self.model_version,
            metrics=self.metrics,
        )
