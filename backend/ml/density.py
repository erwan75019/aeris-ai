"""Leakage-safe synthetic traffic-density data and serving features."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import cos, pi, sin

import numpy as np

HORIZONS_MINUTES = (15, 30, 60)
STEP_MINUTES = 15
FEATURE_NAMES = (
    "hour_sin",
    "hour_cos",
    "weekday_sin",
    "weekday_cos",
    "current_aircraft",
    "lag_15m_aircraft",
    "lag_30m_aircraft",
    "rolling_60m_aircraft",
)


@dataclass(frozen=True)
class DensityDataset:
    timestamps: list[datetime]
    inputs: np.ndarray
    targets: np.ndarray


def density_feature_vector(
    timestamp: datetime,
    *,
    current_aircraft: float,
    lag_15m_aircraft: float,
    lag_30m_aircraft: float,
    rolling_60m_aircraft: float,
) -> np.ndarray:
    """Encode only values available at forecast time."""

    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("Density timestamp must be timezone-aware")
    utc = timestamp.astimezone(UTC)
    minute_of_day = utc.hour * 60 + utc.minute
    day_angle = 2 * pi * minute_of_day / (24 * 60)
    week_angle = 2 * pi * utc.weekday() / 7
    return np.asarray(
        [
            sin(day_angle),
            cos(day_angle),
            sin(week_angle),
            cos(week_angle),
            current_aircraft,
            lag_15m_aircraft,
            lag_30m_aircraft,
            rolling_60m_aircraft,
        ],
        dtype=np.float64,
    )


def generate_density_dataset(*, days: int = 120, seed: int = 91) -> DensityDataset:
    """Create a labelled synthetic traffic series with daily and weekly demand cycles."""

    if days < 21:
        raise ValueError("At least 21 days are required for temporal evaluation")
    rng = np.random.default_rng(seed)
    start = datetime(2024, 1, 1, tzinfo=UTC)
    steps = days * 24 * 60 // STEP_MINUTES
    timestamps = [start + timedelta(minutes=STEP_MINUTES * index) for index in range(steps)]
    counts: list[int] = []
    for index, timestamp in enumerate(timestamps):
        hour = timestamp.hour + timestamp.minute / 60
        morning_peak = 5.5 * np.exp(-0.5 * ((hour - 8.0) / 2.0) ** 2)
        evening_peak = 7.0 * np.exp(-0.5 * ((hour - 18.0) / 2.6) ** 2)
        weekend_factor = 0.78 if timestamp.weekday() >= 5 else 1.0
        slow_wave = 1.4 * sin(2 * pi * index / (7 * 24 * 4) + 0.4)
        rate = max(0.8, weekend_factor * (3.0 + morning_peak + evening_peak) + slow_wave)
        counts.append(int(rng.poisson(rate)))

    max_offset = max(HORIZONS_MINUTES) // STEP_MINUTES
    inputs: list[np.ndarray] = []
    targets: list[list[float]] = []
    sample_timestamps: list[datetime] = []
    for index in range(4, len(counts) - max_offset):
        inputs.append(
            density_feature_vector(
                timestamps[index],
                current_aircraft=counts[index],
                lag_15m_aircraft=counts[index - 1],
                lag_30m_aircraft=counts[index - 2],
                rolling_60m_aircraft=float(np.mean(counts[index - 3 : index + 1])),
            )
        )
        targets.append(
            [float(counts[index + horizon // STEP_MINUTES]) for horizon in HORIZONS_MINUTES]
        )
        sample_timestamps.append(timestamps[index])
    return DensityDataset(
        timestamps=sample_timestamps,
        inputs=np.vstack(inputs),
        targets=np.asarray(targets, dtype=np.float64),
    )
