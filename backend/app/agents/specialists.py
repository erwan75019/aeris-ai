"""Deterministic specialist agents that execute real application tools."""

from dataclasses import dataclass
from datetime import datetime

from backend.app.agents.tools import AerisTools
from backend.app.schemas.flight import AgentFinding, ToolLogEntry


@dataclass(frozen=True)
class AgentRun:
    finding: AgentFinding
    tool_log: list[ToolLogEntry]


class FlightAnalyst:
    name = "flight_analyst"

    def run(self, tools: AerisTools, icao24: str, at: datetime | None) -> AgentRun:
        track = tools.flight_history(icao24, at)
        latest = track.points[-1]
        altitude = (
            f"Latest altitude is {latest.altitude_ft:.0f} ft."
            if latest.altitude_ft is not None
            else "Latest altitude is unavailable."
        )
        finding = AgentFinding(
            agent=self.name,
            status="complete",
            facts=[
                f"Track contains {len(track.points)} {track.data_classification} states.",
                altitude,
                f"Latest state source is {latest.source} at {latest.timestamp.isoformat()}.",
            ],
            limitations=["Track completeness is limited by the active data provider."],
        )
        return AgentRun(
            finding,
            [
                ToolLogEntry(
                    agent=self.name,
                    tool="flight_history",
                    status="ok",
                    detail=f"{len(track.points)} points from {track.source}",
                )
            ],
        )


class AnomalyInvestigator:
    name = "anomaly_investigator"

    def run(self, tools: AerisTools, icao24: str, at: datetime | None) -> AgentRun:
        anomaly = tools.anomaly(icao24, at)
        hypotheses = []
        if anomaly.label == "unusual":
            hypotheses.append(
                "The unusual geometry may match the documented synthetic injection; the score "
                "does not identify an operational cause."
            )
        finding = AgentFinding(
            agent=self.name,
            status="complete",
            facts=[
                f"Anomaly model {anomaly.model.name} returned {anomaly.score:.3f} "
                f"({anomaly.label}).",
                f"Evidence factors: {', '.join(sorted(anomaly.factors))}.",
            ],
            hypotheses=hypotheses,
            limitations=[anomaly.disclaimer],
        )
        return AgentRun(
            finding,
            [
                ToolLogEntry(
                    agent=self.name,
                    tool="anomaly_model",
                    status="ok",
                    detail=(
                        f"{anomaly.model.name}@{anomaly.model.version}; score={anomaly.score:.3f}"
                    ),
                )
            ],
        )


class PredictionAnalyst:
    name = "prediction_analyst"

    def run(self, tools: AerisTools, icao24: str, at: datetime | None) -> AgentRun:
        prediction = tools.prediction(icao24, at)
        final = prediction.points[-1]
        finding = AgentFinding(
            agent=self.name,
            status="complete",
            predictions=[
                f"{prediction.model.name.replace('_', ' ').title()} projects the "
                f"{final.horizon_minutes}-minute point to {final.latitude:.3f}, "
                f"{final.longitude:.3f} with {final.uncertainty_km:.2f} km empirical uncertainty."
            ],
            limitations=[prediction.disclaimer],
        )
        return AgentRun(
            finding,
            [
                ToolLogEntry(
                    agent=self.name,
                    tool="trajectory_prediction",
                    status="ok",
                    detail=f"{prediction.model.name}@{prediction.model.version}",
                )
            ],
        )


class WeatherAnalyst:
    name = "weather_analyst"

    def run(
        self,
        tools: AerisTools,
        icao24: str,
        at: datetime | None,
        *,
        enabled: bool,
    ) -> AgentRun:
        if not enabled:
            return AgentRun(
                AgentFinding(
                    agent=self.name,
                    status="limited",
                    limitations=["Weather analysis was disabled by the request."],
                ),
                [
                    ToolLogEntry(
                        agent=self.name,
                        tool="weather_context",
                        status="unavailable",
                        detail="disabled by request",
                    )
                ],
            )
        track = tools.flight_history(icao24, at)
        weather = tools.weather_context(track.points[-1])
        finding = AgentFinding(
            agent=self.name,
            status="limited",
            facts=[
                f"Synthetic weather context reports wind {weather.wind_direction_deg:.0f}° "
                f"at {weather.wind_speed_kt:.0f} kt."
            ],
            limitations=[
                "Weather context is a synthetic offline grid, not an observed METAR; no causal "
                "relationship with the trajectory can be inferred."
            ],
        )
        return AgentRun(
            finding,
            [
                ToolLogEntry(
                    agent=self.name,
                    tool="weather_context",
                    status="ok",
                    detail=f"{weather.source}; classification={weather.data_classification}",
                )
            ],
        )
