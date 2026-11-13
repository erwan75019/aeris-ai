"""Tool-driven intelligence orchestration with an offline fallback."""

from datetime import UTC, datetime

from backend.app.config import Settings
from backend.app.schemas.flight import (
    IntelligenceRequest,
    IntelligenceResponse,
    ToolLogEntry,
)
from backend.app.services.anomalies import AnomalyService
from backend.app.services.flights import FlightService
from backend.app.services.predictions import PredictionService


class IntelligenceService:
    """Coordinate real application tools and separate evidence from hypotheses."""

    def __init__(
        self,
        flights: FlightService,
        anomalies: AnomalyService,
        predictions: PredictionService,
        settings: Settings,
    ) -> None:
        self.flights = flights
        self.anomalies = anomalies
        self.predictions = predictions
        self.settings = settings

    def create_report(self, request: IntelligenceRequest) -> IntelligenceResponse:
        track = self.flights.get_track(request.icao24, at=request.at)
        anomaly = self.anomalies.evaluate(request.icao24, at=request.at)
        prediction = self.predictions.predict(request.icao24, at=request.at)
        latest = track.points[-1]
        tools = [
            ToolLogEntry(tool="flight_history", status="ok", detail=f"{len(track.points)} points"),
            ToolLogEntry(tool="anomaly_baseline", status="ok", detail=f"score={anomaly.score:.3f}"),
            ToolLogEntry(
                tool="trajectory_prediction",
                status="ok",
                detail=f"{prediction.model.name}: {len(prediction.points)} horizons",
            ),
        ]
        if request.include_weather:
            tools.append(
                ToolLogEntry(
                    tool="aviation_weather",
                    status="unavailable",
                    detail="No station or network observation was requested in offline demo mode.",
                )
            )
        altitude_fact = (
            f"Latest altitude is {latest.altitude_ft:.0f} ft."
            if latest.altitude_ft is not None
            else "Latest altitude is unavailable."
        )
        facts = [
            f"Track contains {len(track.points)} {track.data_classification} states.",
            altitude_fact,
            f"Transparent anomaly score is {anomaly.score:.3f} ({anomaly.label}).",
        ]
        predictions = [
            (
                f"{prediction.model.name.replace('_', ' ').title()} projects the 15-minute "
                f"point to {prediction.points[-1].latitude:.3f}, "
                f"{prediction.points[-1].longitude:.3f}."
            )
        ]
        return IntelligenceResponse(
            icao24=track.icao24,
            mode="deterministic_fallback",
            llm_configured=False,
            facts=facts,
            predictions=predictions,
            hypotheses=[
                "The unusual pattern may be caused by the documented synthetic injection; "
                "no operational cause can be inferred from this dataset."
            ],
            limitations=[
                "Demo data are synthetic and cannot support claims about real aircraft.",
                (
                    "The trajectory predictor is trained only on synthetic maneuvers."
                    if prediction.model.trained
                    else "The current trajectory result uses the kinematic fallback."
                ),
            ],
            tool_log=tools,
            generated_at=datetime.now(UTC),
        )
