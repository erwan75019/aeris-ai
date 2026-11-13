"""Deterministic, clearly synthetic flights for offline demonstrations."""

from datetime import UTC, datetime, timedelta
from math import sin

from backend.app.schemas.flight import FlightState
from backend.app.services.geo import destination_point


class DemoFlightProvider:
    """Generate repeatable traffic without implying that it is observed data."""

    name = "aeris_demo"
    mode = "demo"
    data_classification = "synthetic_demo"
    _start = datetime(2025, 1, 15, 12, 0, tzinfo=UTC)

    def __init__(self) -> None:
        self._tracks = {
            "ae0001": self._make_track(
                icao24="ae0001",
                callsign="AER101",
                latitude=48.48,
                longitude=1.35,
                altitude_ft=16500,
                speed_kt=285,
                heading_deg=72,
                vertical_rate_fpm=350,
                turn_bias=0.08,
            ),
            "ae0002": self._make_track(
                icao24="ae0002",
                callsign="AER204",
                latitude=49.22,
                longitude=3.72,
                altitude_ft=31000,
                speed_kt=430,
                heading_deg=238,
                vertical_rate_fpm=-120,
                turn_bias=-0.05,
            ),
            "ae0003": self._make_track(
                icao24="ae0003",
                callsign="AER903",
                latitude=47.95,
                longitude=1.86,
                altitude_ft=22000,
                speed_kt=360,
                heading_deg=35,
                vertical_rate_fpm=80,
                turn_bias=0.1,
                injected_turn=True,
            ),
            "ae0004": self._make_track(
                icao24="ae0004",
                callsign="AER418",
                latitude=50.05,
                longitude=1.10,
                altitude_ft=28000,
                speed_kt=405,
                heading_deg=112,
                vertical_rate_fpm=-40,
                turn_bias=0.03,
            ),
        }

    def _make_track(
        self,
        *,
        icao24: str,
        callsign: str,
        latitude: float,
        longitude: float,
        altitude_ft: float,
        speed_kt: float,
        heading_deg: float,
        vertical_rate_fpm: float,
        turn_bias: float,
        injected_turn: bool = False,
    ) -> list[FlightState]:
        points: list[FlightState] = []
        for minute in range(61):
            synthetic_turn = 62.0 if injected_turn and 28 <= minute <= 35 else 0.0
            heading = (
                heading_deg + turn_bias * minute + 2.2 * sin(minute / 9) + synthetic_turn
            ) % 360
            vertical_rate = vertical_rate_fpm
            if injected_turn and 30 <= minute <= 34:
                vertical_rate = 2450.0
            points.append(
                FlightState(
                    icao24=icao24,
                    callsign=callsign,
                    latitude=round(latitude, 6),
                    longitude=round(longitude, 6),
                    altitude_ft=round(max(0, min(41000, altitude_ft)), 1),
                    ground_speed_kt=round(speed_kt, 1),
                    heading_deg=round(heading, 2),
                    vertical_rate_fpm=vertical_rate,
                    timestamp=self._start + timedelta(minutes=minute),
                    source=self.name,
                )
            )
            latitude, longitude = destination_point(
                latitude=latitude,
                longitude=longitude,
                heading_degrees=heading,
                speed_knots=speed_kt,
                duration_minutes=1,
            )
            altitude_ft += vertical_rate / 60.0
        return points

    def snapshot(
        self,
        *,
        at: datetime | None = None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> list[FlightState]:
        states: list[FlightState] = []
        for track in self._tracks.values():
            if at is None:
                state = track[-1]
            else:
                state = min(track, key=lambda point: abs((point.timestamp - at).total_seconds()))
            if bbox is not None:
                west, south, east, north = bbox
                if not (west <= state.longitude <= east and south <= state.latitude <= north):
                    continue
            states.append(state)
        return sorted(states, key=lambda item: item.icao24)

    def track(self, icao24: str) -> list[FlightState]:
        return list(self._tracks.get(icao24.lower(), []))

    @property
    def replay_start(self) -> datetime:
        return self._start

    @property
    def replay_end(self) -> datetime:
        return self._start + timedelta(minutes=60)
