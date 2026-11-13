"""Aviation Weather Center METAR adapter and offline weather context."""

from datetime import UTC, datetime
from typing import Any

import httpx

from backend.app.providers.cache import TTLCache
from backend.app.schemas.flight import FlightState
from backend.app.schemas.weather import WeatherObservation


class WeatherProviderError(RuntimeError):
    pass


class WeatherNotFoundError(WeatherProviderError):
    pass


class AviationWeatherClient:
    def __init__(
        self,
        *,
        base_url: str = "https://aviationweather.gov/api/data",
        http_client: httpx.Client | None = None,
        cache_seconds: float = 900,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = http_client or httpx.Client(
            timeout=httpx.Timeout(10.0, connect=5.0),
            headers={"User-Agent": "AERIS-AI/0.1 (+https://github.com/erwan75019/aeris-ai)"},
        )
        self._cache = TTLCache[WeatherObservation](cache_seconds)

    def metar(self, station: str, *, hours: int = 2) -> WeatherObservation:
        normalized = station.upper()
        key = f"{normalized}:{hours}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        try:
            response = self._client.get(
                f"{self._base_url}/metar",
                params={"ids": normalized, "format": "json", "hours": hours},
            )
            if response.status_code == 204:
                raise WeatherNotFoundError(f"No recent METAR for {normalized}")
            if response.status_code == 429:
                raise WeatherProviderError("Aviation Weather Center rate limit reached")
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list) or not payload:
                raise WeatherNotFoundError(f"No recent METAR for {normalized}")
            observation = self._normalize(normalized, payload[0])
        except WeatherProviderError:
            raise
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise WeatherProviderError("Aviation Weather Center request failed") from exc
        self._cache.put(key, observation)
        return observation

    @staticmethod
    def _normalize(station: str, payload: dict[str, Any]) -> WeatherObservation:
        observed = payload.get("obsTime")
        if isinstance(observed, int | float):
            observed_at = datetime.fromtimestamp(observed, tz=UTC)
        elif isinstance(observed, str):
            observed_at = datetime.fromisoformat(observed.replace("Z", "+00:00"))
        else:
            raise WeatherProviderError("METAR observation time is missing")
        return WeatherObservation(
            station=str(payload.get("icaoId") or station).upper(),
            observed_at=observed_at,
            latitude=payload.get("lat"),
            longitude=payload.get("lon"),
            temperature_c=payload.get("temp"),
            dewpoint_c=payload.get("dewp"),
            wind_direction_deg=payload.get("wdir"),
            wind_speed_kt=payload.get("wspd"),
            visibility_sm=payload.get("visib"),
            flight_category=payload.get("fltCat"),
            raw_report=payload.get("rawOb"),
            source="aviation_weather_center",
            data_classification="live",
        )


class WeatherService:
    def __init__(self, client: AviationWeatherClient) -> None:
        self._client = client

    def metar(self, station: str) -> WeatherObservation:
        return self._client.metar(station)

    def synthetic_context(self, state: FlightState) -> WeatherObservation:
        """Return explicit synthetic context for a deterministic offline report."""

        minute = state.timestamp.minute
        return WeatherObservation(
            station="SYNTHETIC-GRID",
            observed_at=state.timestamp,
            latitude=state.latitude,
            longitude=state.longitude,
            temperature_c=round(8.0 - (state.altitude_ft or 0) / 1000 * 1.8, 1),
            dewpoint_c=None,
            wind_direction_deg=float((state.heading_deg or 0) + 40) % 360,
            wind_speed_kt=float(15 + minute % 12),
            visibility_sm=10.0,
            flight_category="SYNTHETIC",
            raw_report=None,
            source="aeris_synthetic_weather",
            data_classification="synthetic_demo",
        )
