"""Trajectory forecasting services with an honest kinematic baseline."""

from datetime import datetime, timedelta
from pathlib import Path

from backend.app.schemas.flight import (
    ModelDescriptor,
    PredictionPoint,
    PredictionResponse,
)
from backend.app.services.flights import FlightService
from backend.app.services.geo import destination_point
from backend.dl.artifacts import TrajectoryArtifact, TrajectoryArtifactError
from backend.dl.data import HORIZONS, INPUT_LENGTH


class PredictionService:
    def __init__(self, flights: FlightService, artifact_dir: Path | None = None) -> None:
        self.flights = flights
        self.artifact: TrajectoryArtifact | None = None
        if artifact_dir is not None:
            try:
                self.artifact = TrajectoryArtifact(artifact_dir)
            except (FileNotFoundError, KeyError, ValueError, TrajectoryArtifactError):
                self.artifact = None

    def predict(
        self,
        icao24: str,
        horizons: tuple[int, ...] = (5, 10, 15),
        *,
        at: datetime | None = None,
    ) -> PredictionResponse:
        track = self.flights.get_track(icao24, at=at)
        current = track.points[-1]
        if self.artifact is not None and horizons == HORIZONS and len(track.points) >= INPUT_LENGTH:
            forecast = self.artifact.predict(track.points)
            return PredictionResponse(
                icao24=track.icao24,
                generated_from=current.timestamp,
                model=ModelDescriptor(
                    name=forecast.model_name,
                    version=forecast.model_version,
                    trained=True,
                    metrics=forecast.metrics,
                ),
                points=[
                    PredictionPoint(
                        horizon_minutes=point.horizon_minutes,
                        latitude=point.latitude,
                        longitude=point.longitude,
                        altitude_ft=point.altitude_ft,
                        timestamp=current.timestamp + timedelta(minutes=point.horizon_minutes),
                        uncertainty_km=point.uncertainty_km,
                    )
                    for point in forecast.points
                ],
                disclaimer=(
                    "Transformer trained and evaluated only on synthetic trajectories. "
                    "Predictions and empirical uncertainty are experimental and not suitable "
                    "for navigation or air-traffic control."
                ),
            )
        if current.ground_speed_kt is None or current.heading_deg is None:
            raise ValueError("Ground speed and heading are required for trajectory projection")
        speed = current.ground_speed_kt
        heading = current.heading_deg
        points: list[PredictionPoint] = []
        for horizon in horizons:
            latitude, longitude = destination_point(
                latitude=current.latitude,
                longitude=current.longitude,
                heading_degrees=heading,
                speed_knots=speed,
                duration_minutes=horizon,
            )
            altitude = current.altitude_ft
            if altitude is not None and current.vertical_rate_fpm is not None:
                altitude = max(0.0, altitude + current.vertical_rate_fpm * horizon)
            points.append(
                PredictionPoint(
                    horizon_minutes=horizon,
                    latitude=latitude,
                    longitude=longitude,
                    altitude_ft=altitude,
                    timestamp=current.timestamp + timedelta(minutes=horizon),
                    uncertainty_km=round(0.8 + horizon * 0.32, 2),
                )
            )
        return PredictionResponse(
            icao24=track.icao24,
            generated_from=current.timestamp,
            model=ModelDescriptor(
                name="constant_velocity_baseline",
                version="1.0.0",
                trained=False,
            ),
            points=points,
            disclaimer=(
                "Experimental kinematic projection, not a trained model and not suitable "
                "for navigation or air-traffic control. Used when history is too short or "
                "the trained artifact is unavailable."
            ),
        )
