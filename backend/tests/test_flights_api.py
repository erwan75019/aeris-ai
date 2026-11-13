from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.providers.weather import WeatherNotFoundError, WeatherProviderError
from backend.app.schemas.weather import WeatherObservation
from backend.app.services.container import services

client = TestClient(app)


def test_demo_flights_are_explicitly_classified() -> None:
    response = client.get("/api/v1/flights")

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["mode"] == "demo"
    assert payload["meta"]["data_classification"] == "synthetic_demo"
    assert payload["meta"]["count"] >= 3
    assert all(flight["source"] == "aeris_demo" for flight in payload["data"])
    assert all(flight["latitude"] is not None for flight in payload["data"])


def test_flights_support_bbox_filtering() -> None:
    response = client.get(
        "/api/v1/flights",
        params={"west": 2.0, "south": 48.0, "east": 3.0, "north": 49.5},
    )

    assert response.status_code == 200
    for flight in response.json()["data"]:
        assert 2.0 <= flight["longitude"] <= 3.0
        assert 48.0 <= flight["latitude"] <= 49.5


def test_track_and_replay_return_ordered_points() -> None:
    track_response = client.get("/api/v1/flights/ae0001/track")

    assert track_response.status_code == 200
    payload = track_response.json()
    timestamps = [datetime.fromisoformat(point["timestamp"]) for point in payload["points"]]
    assert len(timestamps) >= 30
    assert timestamps == sorted(timestamps)
    assert payload["data_classification"] == "synthetic_demo"

    replay_at = timestamps[len(timestamps) // 2].astimezone(UTC).isoformat()
    replay_response = client.get("/api/v1/replay/snapshot", params={"at": replay_at})
    assert replay_response.status_code == 200
    assert replay_response.json()["meta"]["replay_at"] == replay_at


def test_track_and_prediction_are_truncated_at_replay_time() -> None:
    at = "2025-01-15T12:30:00+00:00"

    track_response = client.get("/api/v1/flights/ae0001/track", params={"at": at})
    prediction_response = client.get("/api/v1/flights/ae0001/prediction", params={"at": at})

    assert track_response.status_code == 200
    assert len(track_response.json()["points"]) == 31
    assert track_response.json()["points"][-1]["timestamp"] == "2025-01-15T12:30:00Z"
    assert prediction_response.status_code == 200
    assert prediction_response.json()["generated_from"] == "2025-01-15T12:30:00Z"


def test_replay_rejects_naive_or_out_of_range_time() -> None:
    naive = client.get("/api/v1/replay/snapshot", params={"at": "2025-01-15T12:30:00"})
    outside = client.get("/api/v1/replay/snapshot", params={"at": "2030-01-01T00:00:00Z"})

    assert naive.status_code == 422
    assert outside.status_code == 422
    assert "outside" in outside.json()["detail"].lower()


def test_bbox_must_be_complete_and_ordered() -> None:
    partial = client.get("/api/v1/flights", params={"west": 2, "south": 48})
    inverted = client.get(
        "/api/v1/flights",
        params={"west": 3, "south": 49, "east": 2, "north": 48},
    )

    assert partial.status_code == 422
    assert inverted.status_code == 422


def test_unknown_flight_returns_404() -> None:
    response = client.get("/api/v1/flights/ffffff/track")

    assert response.status_code == 404
    assert response.json()["detail"] == "Flight not found"


def test_malformed_icao24_is_rejected_before_provider_lookup() -> None:
    response = client.get("/api/v1/flights/not-found/track")

    assert response.status_code == 422


def test_prediction_exposes_trained_model_metrics_and_horizons() -> None:
    response = client.get("/api/v1/flights/ae0001/prediction")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"]["name"] == "transformer"
    assert payload["model"]["trained"] is True
    assert payload["model"]["metrics"]["mean_mae_km"] < 4
    assert [point["horizon_minutes"] for point in payload["points"]] == [5, 10, 15]
    assert payload["disclaimer"]


def test_prediction_falls_back_when_replay_history_is_too_short() -> None:
    response = client.get(
        "/api/v1/flights/ae0001/prediction", params={"at": "2025-01-15T12:10:00Z"}
    )

    assert response.status_code == 200
    assert response.json()["model"]["name"] == "constant_velocity_baseline"
    assert response.json()["model"]["trained"] is False


def test_anomaly_is_statistical_and_not_safety_claim() -> None:
    response = client.get("/api/v1/flights/ae0003/anomaly")

    assert response.status_code == 200
    payload = response.json()
    assert 0 <= payload["score"] <= 1
    assert payload["classification"] == "synthetic_demo"
    assert payload["model"]["name"] == "isolation_forest"
    assert payload["model"]["trained"] is True
    assert payload["model"]["metrics"]["f1"] >= 0.8
    assert "not evidence" in payload["disclaimer"].lower()


def test_trained_model_separates_injected_demo_scenario() -> None:
    nominal = client.get("/api/v1/flights/ae0001/anomaly").json()
    injected = client.get("/api/v1/flights/ae0003/anomaly").json()

    assert nominal["label"] == "nominal"
    assert injected["label"] == "unusual"
    assert injected["score"] > nominal["score"]


def test_digital_twin_keeps_simulated_data_separate() -> None:
    response = client.post(
        "/api/v1/simulations",
        json={
            "icao24": "ae0001",
            "anomaly_type": "heading_deviation",
            "severity": 0.6,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["classification"] == "synthetic_simulation"
    assert payload["scenario_id"].startswith("sim-")
    assert len(payload["baseline"]) == len(payload["simulated"])
    assert payload["baseline"] != payload["simulated"]


def test_simulation_rejects_unknown_fields() -> None:
    response = client.post(
        "/api/v1/simulations",
        json={
            "icao24": "ae0001",
            "anomaly_type": "speed_drop",
            "severity": 0.5,
            "untrusted_extra": "ignored?",
        },
    )

    assert response.status_code == 422


def test_intelligence_report_uses_tools_without_claiming_llm() -> None:
    response = client.post(
        "/api/v1/intelligence/reports",
        json={"icao24": "ae0003", "include_weather": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "deterministic_fallback"
    assert payload["facts"]
    assert payload["predictions"]
    assert payload["tool_log"]
    assert len(payload["agent_findings"]) == 4
    assert payload["llm_configured"] is False
    assert payload["limitations"]


def test_analysis_endpoints_return_not_found_consistently() -> None:
    assert client.get("/api/v1/flights/ffffff/prediction").status_code == 404
    assert client.get("/api/v1/flights/ffffff/anomaly").status_code == 404
    assert (
        client.post(
            "/api/v1/simulations",
            json={"icao24": "ffffff", "anomaly_type": "speed_drop", "severity": 0.5},
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/intelligence/reports", json={"icao24": "ffffff", "include_weather": False}
        ).status_code
        == 404
    )


def test_analytics_summary_is_explicitly_synthetic() -> None:
    response = client.get("/api/v1/analytics/summary")

    assert response.status_code == 200
    assert response.json()["aircraft_count"] == 4
    assert response.json()["unusual_count"] == 1
    assert response.json()["classification"] == "synthetic_demo"


def test_weather_endpoint_returns_typed_provider_observation(monkeypatch: object) -> None:
    observation = WeatherObservation(
        station="LFPG",
        observed_at=datetime(2026, 11, 13, 18, tzinfo=UTC),
        wind_direction_deg=240,
        wind_speed_kt=12,
        source="aviation_weather_center",
        data_classification="live",
    )
    monkeypatch.setattr(services.weather, "metar", lambda _station: observation)  # type: ignore[attr-defined]

    response = client.get("/api/v1/weather/stations/LFPG")

    assert response.status_code == 200
    assert response.json()["source"] == "aviation_weather_center"
    assert response.json()["data_classification"] == "live"


def test_weather_endpoint_maps_not_found_and_provider_errors(monkeypatch: object) -> None:
    def not_found(_station: str) -> WeatherObservation:
        raise WeatherNotFoundError("No recent METAR for LFPG")

    monkeypatch.setattr(services.weather, "metar", not_found)  # type: ignore[attr-defined]
    assert client.get("/api/v1/weather/stations/LFPG").status_code == 404

    def unavailable(_station: str) -> WeatherObservation:
        raise WeatherProviderError("rate limited")

    monkeypatch.setattr(services.weather, "metar", unavailable)  # type: ignore[attr-defined]
    assert client.get("/api/v1/weather/stations/LFPG").status_code == 503
    assert client.get("/api/v1/weather/stations/TOO-LONG").status_code == 422
