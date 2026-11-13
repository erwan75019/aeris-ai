import json
from pathlib import Path

import pytest

from backend.app.providers.demo import DemoFlightProvider
from backend.app.services.anomalies import AnomalyService
from backend.app.services.flights import FlightService
from backend.ml.artifacts import ArtifactIntegrityError, IsolationForestArtifact
from backend.ml.features import FEATURE_NAMES, track_feature_map, track_feature_vector
from backend.ml.synthetic import generate_labeled_tracks
from backend.ml.train_anomaly import TrainingConfig, train


def test_feature_contract_is_finite_and_stable() -> None:
    track = DemoFlightProvider().track("ae0001")

    mapping = track_feature_map(track)
    vector = track_feature_vector(track)

    assert tuple(mapping) == FEATURE_NAMES
    assert vector.shape == (len(FEATURE_NAMES),)
    assert all(value >= 0 for value in vector)


def test_synthetic_dataset_is_time_ordered_and_explicitly_labelled() -> None:
    tracks = generate_labeled_tracks(count=30, seed=7)

    assert [item.started_at for item in tracks] == sorted(item.started_at for item in tracks)
    assert len({item.flight_id for item in tracks}) == len(tracks)
    assert any(item.is_injected_anomaly for item in tracks)
    assert all(
        state.source == "aeris_synthetic_training" for item in tracks for state in item.states
    )


def test_training_produces_promoted_integrity_checked_artifact(tmp_path: Path) -> None:
    manifest = train(tmp_path, TrainingConfig())
    detector = IsolationForestArtifact(tmp_path)
    demo = DemoFlightProvider()

    assert manifest["promotion_status"] == "promoted_for_synthetic_demo"
    assert manifest["split_counts"] == {"train": 108, "validation": 36, "test": 36}
    assert detector.predict(demo.track("ae0003")).label == "unusual"
    assert detector.predict(demo.track("ae0001")).label == "nominal"


def test_artifact_checksum_prevents_untrusted_loading(tmp_path: Path) -> None:
    train(tmp_path, TrainingConfig(track_count=60, estimators=40))
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match="checksum"):
        IsolationForestArtifact(tmp_path)


def test_missing_artifact_falls_back_to_transparent_rules(tmp_path: Path) -> None:
    flights = FlightService(DemoFlightProvider())
    response = AnomalyService(flights, tmp_path / "missing").evaluate("ae0003")

    assert response.model.name == "transparent_rules_baseline"
    assert response.model.trained is False


def test_synthetic_dataset_rejects_too_few_tracks() -> None:
    with pytest.raises(ValueError, match="At least 30"):
        generate_labeled_tracks(count=10)
