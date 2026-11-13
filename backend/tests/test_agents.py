import json

import httpx

from backend.app.agents.llm import OllamaNarrator
from backend.app.agents.orchestrator import IntelligenceOrchestrator
from backend.app.agents.tools import AerisTools
from backend.app.schemas.flight import IntelligenceRequest
from backend.app.services.container import services


def test_specialists_execute_distinct_tools_and_preserve_provenance() -> None:
    report = services.intelligence.create_report(
        IntelligenceRequest(icao24="ae0003", include_weather=True)
    )

    assert [finding.agent for finding in report.agent_findings] == [
        "flight_analyst",
        "anomaly_investigator",
        "prediction_analyst",
        "weather_analyst",
    ]
    assert {entry.agent for entry in report.tool_log} == {
        "flight_analyst",
        "anomaly_investigator",
        "prediction_analyst",
        "weather_analyst",
    }
    assert any("synthetic weather" in fact.lower() for fact in report.facts)
    assert report.mode == "deterministic_fallback"
    assert report.narrative is None


def test_weather_agent_records_disabled_tool() -> None:
    report = services.intelligence.create_report(
        IntelligenceRequest(icao24="ae0001", include_weather=False)
    )

    weather_log = next(entry for entry in report.tool_log if entry.agent == "weather_analyst")
    assert weather_log.status == "unavailable"
    assert "disabled" in weather_log.detail


def test_ollama_narrates_only_structured_agent_evidence() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == "qwen3:4b"
        assert "flight_analyst" in payload["messages"][0]["content"]
        return httpx.Response(200, json={"message": {"content": "Evidence-only summary."}})

    narrator = OllamaNarrator(
        model="qwen3:4b",
        base_url="http://ollama.test",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    tools = AerisTools(services.flights, services.anomalies, services.predictions, services.weather)
    report = IntelligenceOrchestrator(tools, narrator).run(
        IntelligenceRequest(icao24="ae0001", include_weather=False)
    )

    assert report.mode == "llm_orchestrated"
    assert report.llm_configured is True
    assert report.narrative == "Evidence-only summary."
    assert report.tool_log[-1].tool == "ollama_narrative"
