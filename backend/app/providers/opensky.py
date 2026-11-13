"""OpenSky live state adapter with OAuth, quota-aware caching, and normalization."""

from collections import defaultdict, deque
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from time import monotonic, sleep
from typing import Any

import httpx

from backend.app.providers.cache import TTLCache
from backend.app.schemas.flight import FlightState

METERS_TO_FEET = 3.280839895
MPS_TO_KNOTS = 1.943844492
MPS_TO_FPM = 196.8503937


class OpenSkyError(RuntimeError):
    """Provider failure with a safe diagnostic message."""


class OpenSkyClient:
    api_base_url = "https://opensky-network.org/api"
    token_url = (
        "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
    )

    def __init__(
        self,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        http_client: httpx.Client | None = None,
        cache_seconds: float = 8.0,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        if bool(client_id) != bool(client_secret):
            raise ValueError("OpenSky client ID and secret must be configured together")
        self._client_id = client_id
        self._client_secret = client_secret
        self._client = http_client or httpx.Client(
            timeout=httpx.Timeout(10.0, connect=5.0),
            headers={"User-Agent": "AERIS-AI/0.1 (+https://github.com/erwan75019/aeris-ai)"},
        )
        self._cache = TTLCache[dict[str, Any]](cache_seconds)
        self._token: str | None = None
        self._token_expires_at = 0.0
        self._sleeper = sleeper

    def _authorization(self) -> dict[str, str]:
        if self._client_id is None or self._client_secret is None:
            return {}
        if self._token is not None and monotonic() < self._token_expires_at:
            return {"Authorization": f"Bearer {self._token}"}
        try:
            response = self._client.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )
            response.raise_for_status()
            payload = response.json()
            self._token = str(payload["access_token"])
            expires_in = max(int(payload.get("expires_in", 1800)), 60)
            self._token_expires_at = monotonic() + expires_in - 30
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise OpenSkyError("OpenSky OAuth token exchange failed") from exc
        return {"Authorization": f"Bearer {self._token}"}

    def states(
        self,
        *,
        at: datetime | None = None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, str | int | float] = {}
        if at is not None:
            params["time"] = int(at.timestamp())
        if bbox is not None:
            west, south, east, north = bbox
            params.update({"lomin": west, "lamin": south, "lomax": east, "lamax": north})
        key = repr(sorted(params.items()))
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        headers = self._authorization()
        for attempt in range(3):
            try:
                response = self._client.get(
                    f"{self.api_base_url}/states/all", params=params, headers=headers
                )
                if response.status_code == 401 and headers and attempt == 0:
                    self._token = None
                    headers = self._authorization()
                    continue
                if response.status_code in {502, 503, 504} and attempt < 2:
                    self._sleeper(0.2 * (attempt + 1))
                    continue
                if response.status_code == 429:
                    retry_after = response.headers.get(
                        "X-Rate-Limit-Retry-After-Seconds", "unknown"
                    )
                    raise OpenSkyError(f"OpenSky quota exhausted; retry after {retry_after}s")
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict) or "states" not in payload:
                    raise OpenSkyError("OpenSky returned an invalid state-vector payload")
                self._cache.put(key, payload)
                return payload
            except OpenSkyError:
                raise
            except (httpx.HTTPError, ValueError) as exc:
                if attempt == 2:
                    raise OpenSkyError("OpenSky state request failed") from exc
                self._sleeper(0.2 * (attempt + 1))
        raise OpenSkyError("OpenSky state request failed")


class OpenSkyFlightProvider:
    """Normalize live OpenSky vectors and retain a bounded in-process track cache."""

    name = "opensky_live"
    mode = "live"
    data_classification = "live"

    def __init__(self, client: OpenSkyClient) -> None:
        self._client = client
        self._history: defaultdict[str, deque[FlightState]] = defaultdict(lambda: deque(maxlen=720))

    @property
    def replay_start(self) -> datetime:
        return datetime.now(UTC) - timedelta(hours=1)

    @property
    def replay_end(self) -> datetime:
        return datetime.now(UTC)

    def snapshot(
        self,
        *,
        at: datetime | None = None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> list[FlightState]:
        payload = self._client.states(at=at, bbox=bbox)
        states = [state for row in payload.get("states") or [] if (state := self._normalize(row))]
        for state in states:
            history = self._history[state.icao24]
            if not history or history[-1].timestamp != state.timestamp:
                history.append(state)
        return sorted(states, key=lambda item: item.icao24)

    def track(self, icao24: str) -> list[FlightState]:
        return list(self._history.get(icao24.lower(), ()))

    def _normalize(self, row: list[Any]) -> FlightState | None:
        if len(row) < 17 or row[5] is None or row[6] is None:
            return None
        timestamp = row[3] or row[4]
        if timestamp is None:
            return None
        altitude_m = row[7] if row[7] is not None else row[13]
        return FlightState(
            icao24=str(row[0]).lower(),
            callsign=str(row[1]).strip() or None if row[1] is not None else None,
            latitude=float(row[6]),
            longitude=float(row[5]),
            altitude_ft=float(altitude_m) * METERS_TO_FEET if altitude_m is not None else None,
            ground_speed_kt=float(row[9]) * MPS_TO_KNOTS if row[9] is not None else None,
            heading_deg=float(row[10]) if row[10] is not None else None,
            vertical_rate_fpm=float(row[11]) * MPS_TO_FPM if row[11] is not None else None,
            timestamp=datetime.fromtimestamp(float(timestamp), tz=UTC),
            source=self.name,
            on_ground=bool(row[8]),
        )
