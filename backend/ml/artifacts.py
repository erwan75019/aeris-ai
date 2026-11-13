"""Versioned anomaly model artifacts with integrity verification."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib  # type: ignore[import-untyped]
import numpy as np
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]

from backend.app.schemas.flight import FlightState
from backend.ml.features import FEATURE_NAMES, track_feature_map, track_feature_vector


class ArtifactIntegrityError(RuntimeError):
    """Raised when an artifact does not match its trusted manifest."""


@dataclass(frozen=True)
class AnomalyPrediction:
    score: float
    raw_score: float
    label: str
    factors: dict[str, float]
    model_name: str
    model_version: str
    metrics: dict[str, float]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class IsolationForestArtifact:
    """Load and score a repository-owned, checksum-verified sklearn bundle."""

    def __init__(self, directory: Path) -> None:
        manifest_path = directory / "manifest.json"
        model_path = directory / "model.joblib"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["artifact_sha256"] != sha256_file(model_path):
            raise ArtifactIntegrityError("Anomaly model checksum does not match manifest")
        if tuple(manifest["feature_names"]) != FEATURE_NAMES:
            raise ArtifactIntegrityError("Anomaly model feature contract is incompatible")
        if manifest.get("promotion_status") != "promoted_for_synthetic_demo":
            raise ArtifactIntegrityError(
                "Anomaly model did not pass synthetic-demo promotion gates"
            )
        bundle: dict[str, Any] = joblib.load(model_path)
        self.pipeline: Pipeline = bundle["pipeline"]
        self.threshold = float(bundle["threshold"])
        self.score_scale = max(float(bundle["score_scale"]), 1e-6)
        self.model_name = str(manifest["model_name"])
        self.model_version = str(manifest["model_version"])
        self.metrics = {key: float(value) for key, value in manifest["test_metrics"].items()}

    def predict(self, track: list[FlightState]) -> AnomalyPrediction:
        vector = track_feature_vector(track).reshape(1, -1)
        raw_score = float(-self.pipeline.decision_function(vector)[0])
        logit = np.clip((raw_score - self.threshold) / self.score_scale, -20, 20)
        score = float(1.0 / (1.0 + np.exp(-logit)))
        factors = {name: round(value, 4) for name, value in track_feature_map(track).items()}
        factors["model_raw_anomaly_score"] = round(raw_score, 6)
        return AnomalyPrediction(
            score=round(score, 4),
            raw_score=raw_score,
            label="unusual" if raw_score >= self.threshold else "nominal",
            factors=factors,
            model_name=self.model_name,
            model_version=self.model_version,
            metrics=self.metrics,
        )
