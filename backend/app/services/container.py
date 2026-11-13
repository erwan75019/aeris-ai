"""Composition root for provider and application services."""

from dataclasses import dataclass

from backend.app.config import get_settings
from backend.app.providers.demo import DemoFlightProvider
from backend.app.services.anomalies import AnomalyService
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


def build_services() -> ServiceContainer:
    settings = get_settings()
    provider = DemoFlightProvider()
    flights = FlightService(provider)
    predictions = PredictionService(flights, settings.trajectory_artifact_dir)
    anomalies = AnomalyService(flights, settings.anomaly_artifact_dir)
    return ServiceContainer(
        flights=flights,
        predictions=predictions,
        anomalies=anomalies,
        simulations=SimulationService(flights),
        intelligence=IntelligenceService(flights, anomalies, predictions, settings),
    )


services = build_services()
