"""Trajectory forecasting services with an honest kinematic baseline."""

from datetime import datetime, timedelta

from backend.app.schemas.flight import (
    ModelDescriptor,
    PredictionPoint,
    PredictionResponse,
)
from backend.app.services.flights import FlightService
from backend.app.services.geo import destination_point


class PredictionService:
    def __init__(self, flights: FlightService) -> None:
        self.flights = flights

    def predict(
        self,
        icao24: str,
        horizons: tuple[int, ...] = (5, 10, 15),
        *,
        at: datetime | None = None,
    ) -> PredictionResponse:
        track = self.flights.get_track(icao24, at=at)
        current = track.points[-1]
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
                "for navigation or air-traffic control."
            ),
        )
