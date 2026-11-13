"""Leakage-safe synthetic trajectory sequences shared by train and serve."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import cos, degrees, radians

import numpy as np

from backend.app.schemas.flight import FlightState
from backend.app.services.geo import destination_point

EARTH_RADIUS_KM = 6371.0088
INPUT_LENGTH = 20
HORIZONS = (5, 10, 15)
INPUT_FEATURES = 7
POSITION_SCALE_KM = 100.0


@dataclass(frozen=True)
class TrajectoryTrack:
    flight_id: str
    started_at: datetime
    states: list[FlightState]


@dataclass(frozen=True)
class SequenceArrays:
    inputs: np.ndarray
    targets: np.ndarray
    current_states: list[FlightState]


def local_offset_km(origin: FlightState, point: FlightState) -> tuple[float, float]:
    """Return equirectangular east/north offsets for regional trajectories."""

    latitude_delta = radians(point.latitude - origin.latitude)
    longitude_delta = radians((point.longitude - origin.longitude + 180) % 360 - 180)
    mean_latitude = radians((point.latitude + origin.latitude) / 2)
    east = EARTH_RADIUS_KM * longitude_delta * cos(mean_latitude)
    north = EARTH_RADIUS_KM * latitude_delta
    return east, north


def apply_local_offset(origin: FlightState, east_km: float, north_km: float) -> tuple[float, float]:
    """Convert a local east/north displacement back to latitude/longitude."""

    latitude = origin.latitude + degrees(north_km / EARTH_RADIUS_KM)
    longitude_scale = max(cos(radians((origin.latitude + latitude) / 2)), 1e-6)
    longitude = origin.longitude + degrees(east_km / (EARTH_RADIUS_KM * longitude_scale))
    return latitude, (longitude + 180) % 360 - 180


def encode_history(states: list[FlightState], *, input_length: int = INPUT_LENGTH) -> np.ndarray:
    """Encode the latest history with fixed physical normalization constants."""

    if len(states) < input_length:
        raise ValueError(f"At least {input_length} states are required")
    history = states[-input_length:]
    origin = history[-1]
    altitude_origin = origin.altitude_ft or 0.0
    rows: list[list[float]] = []
    for point in history:
        east, north = local_offset_km(origin, point)
        heading = radians(point.heading_deg or 0.0)
        rows.append(
            [
                east / POSITION_SCALE_KM,
                north / POSITION_SCALE_KM,
                ((point.altitude_ft or altitude_origin) - altitude_origin) / 10_000.0,
                (point.ground_speed_kt or 0.0) / 500.0,
                np.sin(heading),
                np.cos(heading),
                (point.vertical_rate_fpm or 0.0) / 5_000.0,
            ]
        )
    return np.asarray(rows, dtype=np.float32)


def encode_targets(origin: FlightState, future: list[FlightState]) -> np.ndarray:
    values: list[float] = []
    for point in future:
        east, north = local_offset_km(origin, point)
        values.extend((east / POSITION_SCALE_KM, north / POSITION_SCALE_KM))
    return np.asarray(values, dtype=np.float32)


def generate_trajectory_tracks(*, count: int = 180, seed: int = 73) -> list[TrajectoryTrack]:
    """Generate predictable turns/accelerations, clearly marked as synthetic."""

    if count < 30:
        raise ValueError("At least 30 tracks are required")
    rng = np.random.default_rng(seed)
    origin_time = datetime(2024, 6, 1, tzinfo=UTC)
    tracks: list[TrajectoryTrack] = []
    turn_rates = (-1.2, -0.65, -0.25, 0.0, 0.25, 0.65, 1.2)
    accelerations = (-0.15, 0.0, 0.15)
    for index in range(count):
        latitude = float(rng.uniform(43, 53))
        longitude = float(rng.uniform(-4, 10))
        altitude = float(rng.uniform(18_000, 38_000))
        speed = float(rng.uniform(300, 470))
        heading = float(rng.uniform(0, 360))
        turn_rate = turn_rates[index % len(turn_rates)]
        acceleration = accelerations[(index // len(turn_rates)) % len(accelerations)]
        vertical_rate = float(rng.uniform(-500, 500))
        started_at = origin_time + timedelta(hours=index * 4)
        icao24 = f"{0xC00000 + index:06x}"
        states: list[FlightState] = []
        for minute in range(81):
            states.append(
                FlightState(
                    icao24=icao24,
                    callsign=f"TRN{index:03d}",
                    latitude=latitude,
                    longitude=longitude,
                    altitude_ft=altitude,
                    ground_speed_kt=speed,
                    heading_deg=heading % 360,
                    vertical_rate_fpm=vertical_rate,
                    timestamp=started_at + timedelta(minutes=minute),
                    source="aeris_synthetic_trajectory_training",
                )
            )
            latitude, longitude = destination_point(
                latitude=latitude,
                longitude=longitude,
                heading_degrees=heading,
                speed_knots=speed,
                duration_minutes=1,
            )
            phase = 0.08 * minute + index * 0.03
            heading = (heading + turn_rate + 0.08 * np.sin(phase)) % 360
            speed = min(520.0, max(180.0, speed + acceleration))
            altitude = min(45_000.0, max(0.0, altitude + vertical_rate / 60.0))
        tracks.append(TrajectoryTrack(icao24, started_at, states))
    return tracks


def build_sequences(tracks: list[TrajectoryTrack], *, stride: int = 4) -> SequenceArrays:
    """Create windows without ever crossing a flight boundary."""

    inputs: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    current_states: list[FlightState] = []
    max_horizon = max(HORIZONS)
    for track in tracks:
        last_endpoint = len(track.states) - max_horizon - 1
        for endpoint in range(INPUT_LENGTH - 1, last_endpoint + 1, stride):
            history = track.states[endpoint - INPUT_LENGTH + 1 : endpoint + 1]
            future = [track.states[endpoint + horizon] for horizon in HORIZONS]
            origin = history[-1]
            inputs.append(encode_history(history))
            targets.append(encode_targets(origin, future))
            current_states.append(origin)
    return SequenceArrays(
        inputs=np.stack(inputs),
        targets=np.stack(targets),
        current_states=current_states,
    )
