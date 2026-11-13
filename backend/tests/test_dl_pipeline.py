import json
import shutil
from pathlib import Path

import numpy as np
import pytest
import torch

from backend.app.providers.demo import DemoFlightProvider
from backend.dl.artifacts import TrajectoryArtifact, TrajectoryArtifactError
from backend.dl.data import (
    HORIZONS,
    INPUT_FEATURES,
    INPUT_LENGTH,
    apply_local_offset,
    build_sequences,
    generate_trajectory_tracks,
    local_offset_km,
)
from backend.dl.models import create_model
from backend.dl.train import TrainingConfig, train


def test_local_coordinate_round_trip() -> None:
    origin, point = DemoFlightProvider().track("ae0001")[:2]
    east, north = local_offset_km(origin, point)
    latitude, longitude = apply_local_offset(origin, east, north)

    assert latitude == pytest.approx(point.latitude, abs=1e-8)
    assert longitude == pytest.approx(point.longitude, abs=1e-8)


def test_sequence_builder_keeps_flights_disjoint() -> None:
    tracks = generate_trajectory_tracks(count=30, seed=5)
    sequences = build_sequences(tracks[:2])

    assert sequences.inputs.shape[1:] == (INPUT_LENGTH, INPUT_FEATURES)
    assert sequences.targets.shape[1] == len(HORIZONS) * 2
    assert np.isfinite(sequences.inputs).all()
    assert {state.icao24 for state in sequences.current_states} == {
        tracks[0].flight_id,
        tracks[1].flight_id,
    }


@pytest.mark.parametrize("kind", ["lstm", "gru", "transformer"])
def test_trajectory_model_shapes(kind: str) -> None:
    model = create_model(
        kind,  # type: ignore[arg-type]
        input_size=INPUT_FEATURES,
        hidden_size=16,
        output_size=len(HORIZONS) * 2,
        dropout=0.0,
        sequence_length=INPUT_LENGTH,
    )

    output = model(torch.zeros((3, INPUT_LENGTH, INPUT_FEATURES)))

    assert output.shape == (3, len(HORIZONS) * 2)


def test_committed_trajectory_artifact_serves_trained_forecast() -> None:
    artifact = TrajectoryArtifact(Path("artifacts/models/trajectory"))
    forecast = artifact.predict(DemoFlightProvider().track("ae0001"))

    assert forecast.model_name == "transformer"
    assert forecast.metrics["mean_mae_km"] < 4
    assert [point.horizon_minutes for point in forecast.points] == list(HORIZONS)
    assert all(point.uncertainty_km > 0 for point in forecast.points)


def test_trajectory_artifact_rejects_checksum_mismatch(tmp_path: Path) -> None:
    source = Path("artifacts/models/trajectory")
    destination = tmp_path / "trajectory"
    shutil.copytree(source, destination)
    manifest_path = destination / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["checkpoint_sha256"][manifest["selected_model"]] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(TrajectoryArtifactError, match="checksum"):
        TrajectoryArtifact(destination)


def test_training_smoke_compares_all_architectures(tmp_path: Path) -> None:
    manifest = train(
        tmp_path,
        TrainingConfig(
            track_count=30,
            hidden_size=16,
            max_epochs=1,
            patience=1,
            batch_size=64,
        ),
    )

    assert set(manifest["models"]) == {"lstm", "gru", "transformer"}
    assert set(manifest["checkpoint_sha256"]) == {"lstm", "gru", "transformer"}
    assert manifest["split_policy"].startswith("chronological")
