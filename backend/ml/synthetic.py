"""Clearly labelled synthetic trajectories for deterministic model evaluation."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import numpy as np

from backend.app.schemas.flight import FlightState
from backend.app.services.geo import destination_point


@dataclass(frozen=True)
class LabeledTrack:
    flight_id: str
    started_at: datetime
    states: list[FlightState]
    is_injected_anomaly: bool
    scenario: str


def generate_labeled_tracks(*, count: int = 180, seed: int = 42) -> list[LabeledTrack]:
    """Create flight-disjoint, time-ordered synthetic experiment data."""

    if count < 30:
        raise ValueError("At least 30 tracks are required for train/validation/test evaluation")
    rng = np.random.default_rng(seed)
    origin = datetime(2024, 1, 1, tzinfo=UTC)
    tracks: list[LabeledTrack] = []
    scenarios = ("heading_deviation", "altitude_spike", "speed_drop")
    for index in range(count):
        anomaly = index % 4 == 0
        scenario = scenarios[(index // 4) % len(scenarios)] if anomaly else "nominal"
        started_at = origin + timedelta(hours=index * 3)
        icao24 = f"{0xB00000 + index:06x}"
        latitude = float(rng.uniform(43.0, 53.0))
        longitude = float(rng.uniform(-4.0, 10.0))
        altitude = float(rng.uniform(18_000, 37_000))
        speed = float(rng.uniform(320, 470))
        heading = float(rng.uniform(0, 360))
        base_vertical_rate = float(rng.normal(0, 180))
        low_variance_nominal = index % 3 == 1
        states: list[FlightState] = []
        for minute in range(61):
            heading += float(rng.normal(0, 0.12 if low_variance_nominal else 0.35))
            speed += 0.0 if low_variance_nominal else float(rng.normal(0, 0.7))
            vertical_rate = (
                base_vertical_rate
                if low_variance_nominal
                else base_vertical_rate + float(rng.normal(0, 45))
            )
            if anomaly and 31 <= minute <= 36:
                if scenario == "heading_deviation":
                    heading += 18.0
                elif scenario == "altitude_spike":
                    vertical_rate = 4_200.0
                else:
                    speed -= 32.0
            heading %= 360
            states.append(
                FlightState(
                    icao24=icao24,
                    callsign=f"SYN{index:03d}",
                    latitude=latitude,
                    longitude=longitude,
                    altitude_ft=altitude,
                    ground_speed_kt=max(80.0, speed),
                    heading_deg=heading,
                    vertical_rate_fpm=vertical_rate,
                    timestamp=started_at + timedelta(minutes=minute),
                    source="aeris_synthetic_training",
                )
            )
            latitude, longitude = destination_point(
                latitude=latitude,
                longitude=longitude,
                heading_degrees=heading,
                speed_knots=max(80.0, speed),
                duration_minutes=1,
            )
            altitude = min(45_000.0, max(0.0, altitude + vertical_rate / 60.0))
        tracks.append(
            LabeledTrack(
                flight_id=icao24,
                started_at=started_at,
                states=states,
                is_injected_anomaly=anomaly,
                scenario=scenario,
            )
        )
    return tracks
