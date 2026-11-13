"""Typed tools exposed to AERIS specialist agents."""

from datetime import datetime

from backend.app.providers.weather import WeatherService
from backend.app.schemas.flight import (
    AnomalyResponse,
    FlightState,
    FlightTrackResponse,
    PredictionResponse,
)
from backend.app.schemas.weather import WeatherObservation
from backend.app.services.anomalies import AnomalyService
from backend.app.services.flights import FlightService
from backend.app.services.predictions import PredictionService


class AerisTools:
    def __init__(
        self,
        flights: FlightService,
        anomalies: AnomalyService,
        predictions: PredictionService,
        weather: WeatherService,
    ) -> None:
        self._flights = flights
        self._anomalies = anomalies
        self._predictions = predictions
        self._weather = weather

    def flight_history(self, icao24: str, at: datetime | None) -> FlightTrackResponse:
        return self._flights.get_track(icao24, at=at)

    def anomaly(self, icao24: str, at: datetime | None) -> AnomalyResponse:
        return self._anomalies.evaluate(icao24, at=at)

    def prediction(self, icao24: str, at: datetime | None) -> PredictionResponse:
        return self._predictions.predict(icao24, at=at)

    def weather_context(self, state: FlightState) -> WeatherObservation:
        return self._weather.synthetic_context(state)
