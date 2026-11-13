from datetime import UTC, datetime

import httpx
import pytest

from backend.app.providers.opensky import OpenSkyClient, OpenSkyError, OpenSkyFlightProvider
from backend.app.providers.weather import (
    AviationWeatherClient,
    WeatherNotFoundError,
)


def opensky_row() -> list[object | None]:
    return [
        "abc123",
        " TEST01 ",
        "France",
        1_800_000_000,
        1_800_000_001,
        2.2,
        48.5,
        10_000.0,
        False,
        200.0,
        91.0,
        2.0,
        None,
        10_200.0,
        None,
        False,
        0,
    ]


def test_opensky_normalizes_units_and_caches_identical_reads() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.url.params["lamin"] == "48.0"
        return httpx.Response(200, json={"time": 1_800_000_001, "states": [opensky_row()]})

    client = OpenSkyClient(
        http_client=httpx.Client(transport=httpx.MockTransport(handler)), cache_seconds=60
    )
    provider = OpenSkyFlightProvider(client)
    bounds = (1.0, 48.0, 3.0, 49.0)

    first = provider.snapshot(bbox=bounds)
    second = provider.snapshot(bbox=bounds)

    assert calls == 1
    assert first == second
    assert first[0].callsign == "TEST01"
    assert first[0].altitude_ft == pytest.approx(32_808.4, rel=1e-4)
    assert first[0].ground_speed_kt == pytest.approx(388.77, rel=1e-4)
    assert first[0].vertical_rate_fpm == pytest.approx(393.70, rel=1e-4)
    assert provider.track("ABC123") == first


def test_opensky_oauth_uses_bearer_token() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "auth.opensky-network.org":
            return httpx.Response(200, json={"access_token": "trusted-token", "expires_in": 1800})
        seen.append(request.headers.get("Authorization", ""))
        return httpx.Response(200, json={"time": 1, "states": []})

    client = OpenSkyClient(
        client_id="client",
        client_secret="secret",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.states()["states"] == []
    assert seen == ["Bearer trusted-token"]


def test_opensky_surfaces_quota_without_retry_storm() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, headers={"X-Rate-Limit-Retry-After-Seconds": "120"}, json={})

    client = OpenSkyClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(OpenSkyError, match="120"):
        client.states()
    assert calls == 1


def test_aviation_weather_parses_and_caches_metar() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.url.params["ids"] == "LFPG"
        return httpx.Response(
            200,
            json=[
                {
                    "icaoId": "LFPG",
                    "obsTime": "2026-11-13T18:00:00Z",
                    "lat": 49.01,
                    "lon": 2.55,
                    "temp": 11,
                    "dewp": 7,
                    "wdir": 240,
                    "wspd": 12,
                    "visib": 10,
                    "fltCat": "VFR",
                    "rawOb": "LFPG synthetic test fixture",
                }
            ],
        )

    client = AviationWeatherClient(
        http_client=httpx.Client(transport=httpx.MockTransport(handler)), cache_seconds=60
    )

    first = client.metar("lfpg")
    second = client.metar("LFPG")

    assert calls == 1
    assert first == second
    assert first.observed_at == datetime(2026, 11, 13, 18, tzinfo=UTC)
    assert first.data_classification == "live"
    assert first.source == "aviation_weather_center"


def test_aviation_weather_handles_no_content() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(204))
    client = AviationWeatherClient(http_client=httpx.Client(transport=transport))

    with pytest.raises(WeatherNotFoundError, match="LFPO"):
        client.metar("LFPO")
