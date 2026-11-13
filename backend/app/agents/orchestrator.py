"""Coordinate specialists, preserve tool evidence, and optionally ask Ollama to narrate."""

import json
from datetime import UTC, datetime

from backend.app.agents.llm import LLMError, OllamaNarrator
from backend.app.agents.specialists import (
    AnomalyInvestigator,
    FlightAnalyst,
    PredictionAnalyst,
    WeatherAnalyst,
)
from backend.app.agents.tools import AerisTools
from backend.app.schemas.flight import IntelligenceRequest, IntelligenceResponse, ToolLogEntry


class IntelligenceOrchestrator:
    def __init__(self, tools: AerisTools, narrator: OllamaNarrator | None = None) -> None:
        self._tools = tools
        self._narrator = narrator
        self._flight = FlightAnalyst()
        self._anomaly = AnomalyInvestigator()
        self._prediction = PredictionAnalyst()
        self._weather = WeatherAnalyst()

    def run(self, request: IntelligenceRequest) -> IntelligenceResponse:
        runs = [
            self._flight.run(self._tools, request.icao24, request.at),
            self._anomaly.run(self._tools, request.icao24, request.at),
            self._prediction.run(self._tools, request.icao24, request.at),
            self._weather.run(
                self._tools,
                request.icao24,
                request.at,
                enabled=request.include_weather,
            ),
        ]
        findings = [run.finding for run in runs]
        tool_log = [entry for run in runs for entry in run.tool_log]
        facts = [value for finding in findings for value in finding.facts]
        predictions = [value for finding in findings for value in finding.predictions]
        hypotheses = [value for finding in findings for value in finding.hypotheses]
        limitations = list(
            dict.fromkeys(value for finding in findings for value in finding.limitations)
        )
        narrative: str | None = None
        mode = "deterministic_fallback"
        if self._narrator is not None:
            try:
                evidence = json.dumps(
                    [finding.model_dump(mode="json") for finding in findings], sort_keys=True
                )
                narrative = self._narrator.narrate(evidence)
                mode = "llm_orchestrated"
                tool_log.append(
                    ToolLogEntry(
                        agent="report_generator",
                        tool="ollama_narrative",
                        status="ok",
                        detail="Narrative generated from structured specialist evidence.",
                    )
                )
            except LLMError as exc:
                tool_log.append(
                    ToolLogEntry(
                        agent="report_generator",
                        tool="ollama_narrative",
                        status="error",
                        detail=str(exc),
                    )
                )
                limitations.append("Configured LLM was unavailable; structured evidence is intact.")
        return IntelligenceResponse(
            icao24=request.icao24.lower(),
            mode=mode,
            llm_configured=self._narrator is not None,
            facts=facts,
            predictions=predictions,
            hypotheses=hypotheses,
            limitations=limitations,
            tool_log=tool_log,
            agent_findings=findings,
            narrative=narrative,
            generated_at=datetime.now(UTC),
        )
