"""Flight-query application service."""

from datetime import UTC, datetime

from backend.app.providers.base import FlightDataProvider
from backend.app.schemas.flight import FlightListMeta, FlightListResponse, FlightTrackResponse


class FlightNotFoundError(LookupError):
    """Raised when a provider has no track for an identifier."""


class ReplayTimeOutOfRangeError(ValueError):
    """Raised when a replay query is outside the provider's declared window."""


class FlightService:
    def __init__(self, provider: FlightDataProvider) -> None:
        self.provider = provider

    def normalize_replay_time(self, at: datetime) -> datetime:
        """Normalize an aware timestamp to UTC and enforce provider bounds."""

        if at.tzinfo is None or at.utcoffset() is None:
            raise ReplayTimeOutOfRangeError("Replay timestamp must include a timezone")
        normalized = at.astimezone(UTC)
        if not self.provider.replay_start <= normalized <= self.provider.replay_end:
            raise ReplayTimeOutOfRangeError(
                "Replay timestamp is outside the available scenario range"
            )
        return normalized

    def list_flights(
        self,
        *,
        at: datetime | None = None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> FlightListResponse:
        normalized_at = self.normalize_replay_time(at) if at is not None else None
        states = self.provider.snapshot(at=normalized_at, bbox=bbox)
        generated_at = normalized_at or (
            max(state.timestamp for state in states) if states else datetime.now(UTC)
        )
        return FlightListResponse(
            data=states,
            meta=FlightListMeta(
                mode=self.provider.mode,
                data_classification=self.provider.data_classification,
                source=self.provider.name,
                count=len(states),
                generated_at=generated_at,
            ),
        )

    def get_track(self, icao24: str, *, at: datetime | None = None) -> FlightTrackResponse:
        points = self.provider.track(icao24)
        if not points:
            raise FlightNotFoundError(icao24)
        if at is not None:
            normalized_at = self.normalize_replay_time(at)
            points = [point for point in points if point.timestamp <= normalized_at]
        return FlightTrackResponse(
            icao24=icao24.lower(),
            callsign=points[0].callsign,
            points=points,
            source=self.provider.name,
            data_classification=self.provider.data_classification,
        )
