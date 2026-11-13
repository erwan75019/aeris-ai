"""Provider contracts shared by demo, historical and live adapters."""

from datetime import datetime
from typing import Protocol

from backend.app.schemas.flight import FlightState


class FlightDataProvider(Protocol):
    name: str
    mode: str
    data_classification: str

    @property
    def replay_start(self) -> datetime: ...

    @property
    def replay_end(self) -> datetime: ...

    def snapshot(
        self,
        *,
        at: datetime | None = None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> list[FlightState]: ...

    def track(self, icao24: str) -> list[FlightState]: ...
