"""Integrity-checked PyTorch trajectory inference."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from backend.app.schemas.flight import FlightState
from backend.dl.data import (
    HORIZONS,
    INPUT_LENGTH,
    POSITION_SCALE_KM,
    apply_local_offset,
    encode_history,
)
from backend.dl.models import ModelKind, create_model


class TrajectoryArtifactError(RuntimeError):
    """Raised when a checkpoint or manifest is incompatible or untrusted."""


@dataclass(frozen=True)
class ForecastPoint:
    horizon_minutes: int
    latitude: float
    longitude: float
    altitude_ft: float | None
    uncertainty_km: float


@dataclass(frozen=True)
class TrajectoryForecast:
    model_name: str
    model_version: str
    metrics: dict[str, float]
    points: list[ForecastPoint]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TrajectoryArtifact:
    """Serve the validation-selected checkpoint on CPU with safe state loading."""

    def __init__(self, directory: Path) -> None:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("promotion_status") != "promoted_for_synthetic_demo":
            raise TrajectoryArtifactError("Trajectory model did not pass promotion gate")
        if tuple(manifest["horizons_minutes"]) != HORIZONS:
            raise TrajectoryArtifactError("Trajectory horizon contract is incompatible")
        if int(manifest["input_length"]) != INPUT_LENGTH:
            raise TrajectoryArtifactError("Trajectory input contract is incompatible")
        selected_value = str(manifest["selected_model"])
        if selected_value not in ("lstm", "gru", "transformer"):
            raise TrajectoryArtifactError("Trajectory model kind is unsupported")
        selected: ModelKind = selected_value  # type: ignore[assignment]
        checkpoint_path = directory / f"{selected}.pt"
        if _sha256(checkpoint_path) != manifest["checkpoint_sha256"][selected]:
            raise TrajectoryArtifactError("Trajectory checkpoint checksum does not match manifest")
        bundle: dict[str, Any] = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        if bundle["model_kind"] != selected:
            raise TrajectoryArtifactError("Trajectory checkpoint kind does not match manifest")
        self.model = create_model(
            selected,
            input_size=int(bundle["input_size"]),
            hidden_size=int(bundle["hidden_size"]),
            output_size=int(bundle["output_size"]),
            dropout=float(bundle["dropout"]),
            sequence_length=int(bundle["sequence_length"]),
        )
        self.model.load_state_dict(bundle["model_state_dict"])
        self.model.eval()
        self.model_name = selected
        self.model_version = str(manifest["model_version"])
        metrics = manifest["models"][selected]["test_metrics"]
        self.metrics = {name: float(value) for name, value in metrics.items()}

    @torch.inference_mode()
    def predict(self, track: list[FlightState]) -> TrajectoryForecast:
        if len(track) < INPUT_LENGTH:
            raise ValueError(f"At least {INPUT_LENGTH} observations are required")
        current = track[-1]
        encoded = torch.from_numpy(encode_history(track)).unsqueeze(0)
        output = self.model(encoded).squeeze(0).numpy().reshape(len(HORIZONS), 2)
        points: list[ForecastPoint] = []
        for index, horizon in enumerate(HORIZONS):
            east, north = output[index] * POSITION_SCALE_KM
            latitude, longitude = apply_local_offset(current, float(east), float(north))
            altitude = current.altitude_ft
            if altitude is not None and current.vertical_rate_fpm is not None:
                altitude = max(0.0, altitude + current.vertical_rate_fpm * horizon)
            points.append(
                ForecastPoint(
                    horizon_minutes=horizon,
                    latitude=latitude,
                    longitude=longitude,
                    altitude_ft=altitude,
                    uncertainty_km=round(self.metrics[f"p90_km_{horizon}m"], 2),
                )
            )
        return TrajectoryForecast(
            model_name=self.model_name,
            model_version=self.model_version,
            metrics=self.metrics,
            points=points,
        )
