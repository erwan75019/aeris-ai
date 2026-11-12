"""Experimental digital-twin scenario generation."""

from hashlib import sha256

from backend.app.schemas.flight import (
    FlightState,
    SimulationRequest,
    SimulationResponse,
)
from backend.app.services.flights import FlightService
from backend.app.services.geo import destination_point


class SimulationService:
    def __init__(self, flights: FlightService) -> None:
        self.flights = flights

    def run(self, request: SimulationRequest) -> SimulationResponse:
        track = self.flights.get_track(request.icao24)
        baseline = track.points[-24:]
        simulated: list[FlightState] = []
        for index, point in enumerate(baseline):
            if index < len(baseline) // 2:
                simulated.append(point)
                continue
            progress = (index - len(baseline) // 2 + 1) / (len(baseline) // 2)
            updates: dict[str, float] = {}
            if request.anomaly_type == "altitude_spike":
                altitude_delta = 5000 * request.severity * progress
                updates["altitude_ft"] = (point.altitude_ft or 0) + altitude_delta
                updates["vertical_rate_fpm"] = 3000 * request.severity
            elif request.anomaly_type == "speed_drop":
                updates["ground_speed_kt"] = max(
                    0, (point.ground_speed_kt or 0) * (1 - 0.65 * request.severity * progress)
                )
            else:
                new_heading = ((point.heading_deg or 0) + 75 * request.severity * progress) % 360
                latitude, longitude = destination_point(
                    latitude=point.latitude,
                    longitude=point.longitude,
                    heading_degrees=new_heading,
                    speed_knots=point.ground_speed_kt or 0,
                    duration_minutes=progress * 2,
                )
                updates.update(
                    heading_deg=new_heading,
                    latitude=latitude,
                    longitude=longitude,
                )
            simulated.append(point.model_copy(update=updates))

        digest = sha256(
            f"{request.icao24}:{request.anomaly_type}:{request.severity:.3f}".encode()
        ).hexdigest()[:12]
        return SimulationResponse(
            scenario_id=f"sim-{digest}",
            classification="synthetic_simulation",
            anomaly_type=request.anomaly_type,
            baseline=baseline,
            simulated=simulated,
            disclaimer=(
                "Synthetic experimental scenario, isolated from observed data and not a "
                "certified air-traffic simulator."
            ),
        )
