"""Train, compare, and package LSTM, GRU, and Transformer forecasters."""

import argparse
import copy
import hashlib
import json
import random
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from backend.app.services.geo import destination_point
from backend.dl.data import (
    HORIZONS,
    INPUT_FEATURES,
    INPUT_LENGTH,
    POSITION_SCALE_KM,
    SequenceArrays,
    build_sequences,
    generate_trajectory_tracks,
    local_offset_km,
)
from backend.dl.models import ModelKind, create_model


@dataclass(frozen=True)
class TrainingConfig:
    seed: int = 73
    track_count: int = 180
    hidden_size: int = 48
    dropout: float = 0.08
    learning_rate: float = 0.0025
    weight_decay: float = 0.0001
    batch_size: int = 64
    max_epochs: int = 35
    patience: int = 6
    model_version: str = "1.0.0"
    dataset_id: str = "synthetic-trajectory-v1"


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def resolve_device(requested: str) -> torch.device:
    if requested != "auto":
        return torch.device(requested)
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def _loader(
    data: SequenceArrays, *, batch_size: int, shuffle: bool, seed: int
) -> DataLoader[tuple[torch.Tensor, torch.Tensor]]:
    dataset = TensorDataset(torch.from_numpy(data.inputs), torch.from_numpy(data.targets))
    generator = torch.Generator().manual_seed(seed)
    return DataLoader(
        dataset,  # type: ignore[arg-type]
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=0,
        generator=generator,
    )


@torch.no_grad()
def _loss(
    model: nn.Module,
    loader: DataLoader[tuple[torch.Tensor, torch.Tensor]],
    device: torch.device,
) -> float:
    model.eval()
    criterion = nn.MSELoss(reduction="sum")
    total = 0.0
    samples = 0
    for inputs, targets in loader:
        inputs = inputs.to(device)
        targets = targets.to(device)
        total += float(criterion(model(inputs), targets).item())
        samples += targets.shape[0]
    return total / max(samples, 1)


def _train_one(
    kind: ModelKind,
    training: SequenceArrays,
    validation: SequenceArrays,
    config: TrainingConfig,
    device: torch.device,
) -> tuple[nn.Module, list[dict[str, float]], int]:
    set_seed(config.seed)
    model = create_model(
        kind,
        input_size=INPUT_FEATURES,
        hidden_size=config.hidden_size,
        output_size=len(HORIZONS) * 2,
        dropout=config.dropout,
        sequence_length=INPUT_LENGTH,
    ).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay
    )
    criterion = nn.MSELoss()
    training_loader = _loader(
        training, batch_size=config.batch_size, shuffle=True, seed=config.seed
    )
    validation_loader = _loader(
        validation, batch_size=config.batch_size, shuffle=False, seed=config.seed
    )
    best_loss = float("inf")
    best_state: dict[str, torch.Tensor] | None = None
    stale_epochs = 0
    history: list[dict[str, float]] = []
    best_epoch = 0
    for epoch in range(1, config.max_epochs + 1):
        model.train()
        running_loss = 0.0
        batches = 0
        for inputs, targets in training_loader:
            inputs = inputs.to(device)
            targets = targets.to(device)
            optimizer.zero_grad(set_to_none=True)
            predictions = model(inputs)
            loss = criterion(predictions, targets)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            running_loss += float(loss.item())
            batches += 1
        validation_loss = _loss(model, validation_loader, device)
        history.append(
            {
                "epoch": float(epoch),
                "train_loss": running_loss / max(batches, 1),
                "validation_loss": validation_loss,
            }
        )
        if validation_loss < best_loss - 1e-6:
            best_loss = validation_loss
            best_state = copy.deepcopy(
                {key: value.detach().cpu() for key, value in model.state_dict().items()}
            )
            best_epoch = epoch
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= config.patience:
                break
    if best_state is None:
        raise RuntimeError("Training did not produce a checkpoint")
    model.load_state_dict(best_state)
    return model.to(device), history, best_epoch


@torch.no_grad()
def _predict(model: nn.Module, data: SequenceArrays, device: torch.device) -> np.ndarray:
    model.eval()
    values = torch.from_numpy(data.inputs).to(device)
    batches = [model(batch).cpu().numpy() for batch in torch.split(values, 256)]
    return np.concatenate(batches)


def _metrics(predictions: np.ndarray, targets: np.ndarray) -> dict[str, float]:
    predicted = predictions.reshape(-1, len(HORIZONS), 2) * POSITION_SCALE_KM
    expected = targets.reshape(-1, len(HORIZONS), 2) * POSITION_SCALE_KM
    distances = np.linalg.norm(predicted - expected, axis=2)
    metrics: dict[str, float] = {}
    for index, horizon in enumerate(HORIZONS):
        errors = distances[:, index]
        metrics[f"mae_km_{horizon}m"] = float(errors.mean())
        metrics[f"rmse_km_{horizon}m"] = float(np.sqrt(np.mean(np.square(errors))))
        metrics[f"p90_km_{horizon}m"] = float(np.quantile(errors, 0.90))
    metrics["mean_mae_km"] = float(np.mean([metrics[f"mae_km_{horizon}m"] for horizon in HORIZONS]))
    return metrics


def _baseline_predictions(data: SequenceArrays) -> np.ndarray:
    outputs: list[list[float]] = []
    for current in data.current_states:
        if current.ground_speed_kt is None or current.heading_deg is None:
            raise ValueError("Synthetic trajectory baseline requires speed and heading")
        values: list[float] = []
        for horizon in HORIZONS:
            latitude, longitude = destination_point(
                latitude=current.latitude,
                longitude=current.longitude,
                heading_degrees=current.heading_deg,
                speed_knots=current.ground_speed_kt,
                duration_minutes=horizon,
            )
            projected = current.model_copy(update={"latitude": latitude, "longitude": longitude})
            east, north = local_offset_km(current, projected)
            values.extend((east / POSITION_SCALE_KM, north / POSITION_SCALE_KM))
        outputs.append(values)
    return np.asarray(outputs, dtype=np.float32)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def train(
    output_dir: Path,
    config: TrainingConfig = TrainingConfig(),
    *,
    requested_device: str = "cpu",
) -> dict[str, Any]:
    """Train on earlier flights, select on validation, and report held-out test metrics."""

    set_seed(config.seed)
    device = resolve_device(requested_device)
    tracks = generate_trajectory_tracks(count=config.track_count, seed=config.seed)
    train_end = int(len(tracks) * 0.60)
    validation_end = int(len(tracks) * 0.80)
    training = build_sequences(tracks[:train_end])
    validation = build_sequences(tracks[train_end:validation_end])
    testing = build_sequences(tracks[validation_end:])
    output_dir.mkdir(parents=True, exist_ok=True)
    model_results: dict[str, Any] = {}
    trained_models: dict[ModelKind, nn.Module] = {}
    for kind in ("lstm", "gru", "transformer"):
        typed_kind: ModelKind = kind
        model, history, best_epoch = _train_one(typed_kind, training, validation, config, device)
        validation_metrics = _metrics(_predict(model, validation, device), validation.targets)
        test_metrics = _metrics(_predict(model, testing, device), testing.targets)
        trained_models[typed_kind] = model
        model_results[kind] = {
            "best_epoch": best_epoch,
            "history": history,
            "validation_metrics": validation_metrics,
            "test_metrics": test_metrics,
        }
    selected_kind = min(
        model_results,
        key=lambda name: model_results[name]["validation_metrics"]["mean_mae_km"],
    )
    checkpoint_hashes: dict[str, str] = {}
    for kind, model in trained_models.items():
        checkpoint = output_dir / f"{kind}.pt"
        torch.save(
            {
                "model_kind": kind,
                "model_state_dict": {key: value.cpu() for key, value in model.state_dict().items()},
                "input_size": INPUT_FEATURES,
                "hidden_size": config.hidden_size,
                "output_size": len(HORIZONS) * 2,
                "dropout": config.dropout,
                "sequence_length": INPUT_LENGTH,
            },
            checkpoint,
        )
        checkpoint_hashes[kind] = _sha256(checkpoint)
    baseline_metrics = _metrics(_baseline_predictions(testing), testing.targets)
    selected_metrics = model_results[selected_kind]["test_metrics"]
    promoted = selected_metrics["mean_mae_km"] < baseline_metrics["mean_mae_km"]
    manifest: dict[str, Any] = {
        "model_name": selected_kind,
        "model_version": config.model_version,
        "trained": True,
        "trained_at": datetime.now(UTC).isoformat(),
        "dataset_id": config.dataset_id,
        "data_classification": "synthetic_simulation",
        "config": asdict(config),
        "device": str(device),
        "horizons_minutes": list(HORIZONS),
        "input_length": INPUT_LENGTH,
        "input_features": INPUT_FEATURES,
        "split_policy": "chronological 60/20/20 with flight-disjoint tracks",
        "track_split_counts": {
            "train": train_end,
            "validation": validation_end - train_end,
            "test": len(tracks) - validation_end,
        },
        "sequence_counts": {
            "train": len(training.inputs),
            "validation": len(validation.inputs),
            "test": len(testing.inputs),
        },
        "selected_model": selected_kind,
        "checkpoint_sha256": checkpoint_hashes,
        "baseline_test_metrics": baseline_metrics,
        "models": model_results,
        "promotion_status": "promoted_for_synthetic_demo" if promoted else "rejected",
        "limitations": [
            "Training and evaluation trajectories are synthetic and procedurally generated.",
            "Empirical uncertainty is a held-out synthetic error, not a calibrated safety bound.",
            "Predictions are not suitable for navigation or air-traffic control.",
        ],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/models/trajectory"))
    parser.add_argument("--device", choices=("auto", "cpu", "mps", "cuda"), default="auto")
    args = parser.parse_args()
    print(
        json.dumps(train(args.output_dir, requested_device=args.device), indent=2, sort_keys=True)
    )


if __name__ == "__main__":
    main()
