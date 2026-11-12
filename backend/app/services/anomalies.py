"""Transparent statistical anomaly baseline."""

from datetime import datetime

from backend.app.schemas.flight import AnomalyResponse, ModelDescriptor
from backend.app.services.flights import FlightService
from backend.app.services.geo import smallest_heading_delta


class AnomalyService:
    def __init__(self, flights: FlightService) -> None:
        self.flights = flights

    def evaluate(self, icao24: str, *, at: datetime | None = None) -> AnomalyResponse:
        track = self.flights.get_track(icao24, at=at)
        recent = track.points[-40:]
        heading_changes = [
            abs(smallest_heading_delta(previous.heading_deg, current.heading_deg))
            for previous, current in zip(recent, recent[1:], strict=False)
            if previous.heading_deg is not None and current.heading_deg is not None
        ]
        speed_changes = [
            abs(current.ground_speed_kt - previous.ground_speed_kt)
            for previous, current in zip(recent, recent[1:], strict=False)
            if previous.ground_speed_kt is not None and current.ground_speed_kt is not None
        ]
        vertical_rates = [
            abs(point.vertical_rate_fpm) for point in recent if point.vertical_rate_fpm is not None
        ]
        factors = {
            "max_heading_change_deg": round(max(heading_changes, default=0), 3),
            "max_speed_change_kt": round(max(speed_changes, default=0), 3),
            "max_vertical_rate_fpm": round(max(vertical_rates, default=0), 3),
        }
        score = min(
            1.0,
            factors["max_heading_change_deg"] / 90 * 0.65
            + factors["max_speed_change_kt"] / 150 * 0.10
            + factors["max_vertical_rate_fpm"] / 4000 * 0.25,
        )
        return AnomalyResponse(
            icao24=track.icao24,
            score=round(score, 4),
            label="unusual" if score >= 0.45 else "nominal",
            classification=track.data_classification,
            factors=factors,
            model=ModelDescriptor(
                name="transparent_rules_baseline", version="1.0.0", trained=False
            ),
            disclaimer=(
                "A statistical anomaly is not evidence of an incident, unsafe operation, "
                "or causality. This demo includes intentionally injected synthetic behavior."
            ),
        )
