"""Composition root for provider and application services."""

from dataclasses import dataclass

from backend.app.config import get_settings
from backend.app.providers.base import FlightDataProvider
from backend.app.providers.demo import DemoFlightProvider
from backend.app.providers.opensky import OpenSkyClient, OpenSkyFlightProvider
from backend.app.providers.weather import AviationWeatherClient, WeatherService
from backend.app.services.anomalies import AnomalyService
from backend.app.services.density import DensityService
from backend.app.services.flights import FlightService
from backend.app.services.intelligence import IntelligenceService
from backend.app.services.predictions import PredictionService
from backend.app.services.simulations import SimulationService


@dataclass(frozen=True)
class ServiceContainer:
    flights: FlightService
    predictions: PredictionService
    anomalies: AnomalyService
    simulations: SimulationService
    intelligence: IntelligenceService
    weather: WeatherService
    density: DensityService


def build_services() -> ServiceContainer:
    settings = get_settings()
    provider: FlightDataProvider
    if settings.data_provider == "opensky":
        provider = OpenSkyFlightProvider(
            OpenSkyClient(
                client_id=settings.opensky_client_id,
                client_secret=settings.opensky_client_secret,
            )
        )
    else:
        provider = DemoFlightProvider()
    flights = FlightService(provider)
    predictions = PredictionService(flights, settings.trajectory_artifact_dir)
    anomalies = AnomalyService(flights, settings.anomaly_artifact_dir)
    weather = WeatherService(AviationWeatherClient(base_url=settings.aviation_weather_base_url))
    return ServiceContainer(
        flights=flights,
        predictions=predictions,
        anomalies=anomalies,
        simulations=SimulationService(flights, anomalies, predictions),
        intelligence=IntelligenceService(flights, anomalies, predictions, weather, settings),
        weather=weather,
        density=DensityService(flights, settings.density_artifact_dir),
    )


services = build_services()
