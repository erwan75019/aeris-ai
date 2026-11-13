"""Public intelligence service backed by specialist-agent orchestration."""

from backend.app.agents.llm import OllamaNarrator
from backend.app.agents.orchestrator import IntelligenceOrchestrator
from backend.app.agents.tools import AerisTools
from backend.app.config import Settings
from backend.app.providers.weather import WeatherService
from backend.app.schemas.flight import IntelligenceRequest, IntelligenceResponse
from backend.app.services.anomalies import AnomalyService
from backend.app.services.flights import FlightService
from backend.app.services.predictions import PredictionService


class IntelligenceService:
    def __init__(
        self,
        flights: FlightService,
        anomalies: AnomalyService,
        predictions: PredictionService,
        weather: WeatherService,
        settings: Settings,
    ) -> None:
        narrator = None
        if settings.llm_provider == "ollama" and settings.llm_model:
            narrator = OllamaNarrator(
                model=settings.llm_model,
                base_url=settings.llm_base_url,
            )
        tools = AerisTools(flights, anomalies, predictions, weather)
        self._orchestrator = IntelligenceOrchestrator(tools, narrator)

    def create_report(self, request: IntelligenceRequest) -> IntelligenceResponse:
        return self._orchestrator.run(request)
