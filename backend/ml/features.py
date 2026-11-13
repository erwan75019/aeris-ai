"""Shared train/serve anomaly features with explicit aviation units."""

from collections.abc import Sequence

import numpy as np

from backend.app.schemas.flight import FlightState
from backend.app.services.geo import haversine_km, smallest_heading_delta

FEATURE_NAMES = (
    "max_heading_change_deg",
    "mean_heading_change_deg",
    "max_speed_change_kt",
    "mean_speed_change_kt",
    "max_vertical_rate_fpm",
    "altitude_range_ft",
    "speed_std_kt",
    "path_efficiency",
)


def _finite(values: Sequence[float | None]) -> np.ndarray:
    return np.asarray([value for value in values if value is not None], dtype=np.float64)


def track_feature_map(track: Sequence[FlightState]) -> dict[str, float]:
    """Aggregate only information available at the final observation time."""

    heading_changes = np.asarray(
        [
            abs(smallest_heading_delta(previous.heading_deg, current.heading_deg))
            for previous, current in zip(track, track[1:], strict=False)
            if previous.heading_deg is not None and current.heading_deg is not None
        ],
        dtype=np.float64,
    )
    speed_changes = np.asarray(
        [
            abs(current.ground_speed_kt - previous.ground_speed_kt)
            for previous, current in zip(track, track[1:], strict=False)
            if previous.ground_speed_kt is not None and current.ground_speed_kt is not None
        ],
        dtype=np.float64,
    )
    vertical_rates = np.abs(_finite([point.vertical_rate_fpm for point in track]))
    altitudes = _finite([point.altitude_ft for point in track])
    speeds = _finite([point.ground_speed_kt for point in track])
    path_distance = sum(
        haversine_km(
            previous.latitude,
            previous.longitude,
            current.latitude,
            current.longitude,
        )
        for previous, current in zip(track, track[1:], strict=False)
    )
    direct_distance = (
        haversine_km(
            track[0].latitude,
            track[0].longitude,
            track[-1].latitude,
            track[-1].longitude,
        )
        if len(track) >= 2
        else 0.0
    )
    return {
        "max_heading_change_deg": float(heading_changes.max()) if heading_changes.size else 0.0,
        "mean_heading_change_deg": float(heading_changes.mean()) if heading_changes.size else 0.0,
        "max_speed_change_kt": float(speed_changes.max()) if speed_changes.size else 0.0,
        "mean_speed_change_kt": float(speed_changes.mean()) if speed_changes.size else 0.0,
        "max_vertical_rate_fpm": float(vertical_rates.max()) if vertical_rates.size else 0.0,
        "altitude_range_ft": float(np.ptp(altitudes)) if altitudes.size else 0.0,
        "speed_std_kt": float(speeds.std()) if speeds.size else 0.0,
        "path_efficiency": float(direct_distance / path_distance) if path_distance > 0 else 1.0,
    }


def track_feature_vector(track: Sequence[FlightState]) -> np.ndarray:
    """Return features in the canonical artifact order."""

    values = track_feature_map(track)
    return np.asarray([values[name] for name in FEATURE_NAMES], dtype=np.float64)
