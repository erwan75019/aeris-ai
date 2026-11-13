"""Experimental digital-twin scenario generation."""

from hashlib import sha256

from backend.app.schemas.flight import (
    DataClassification,
    FlightState,
    FlightTrackResponse,
    SimulationModelReaction,
    SimulationRequest,
    SimulationResponse,
    SimulationWeather,
)
from backend.app.services.anomalies import AnomalyService
from backend.app.services.flights import FlightService
from backend.app.services.geo import destination_point
from backend.app.services.predictions import PredictionService


class SimulationService:
    def __init__(
        self,
        flights: FlightService,
        anomalies: AnomalyService,
        predictions: PredictionService,
    ) -> None:
        self.flights = flights
        self.anomalies = anomalies
        self.predictions = predictions

    @staticmethod
    def _track(
        points: list[FlightState],
        *,
        classification: DataClassification,
    ) -> FlightTrackResponse:
        first = points[0]
        return FlightTrackResponse(
            icao24=first.icao24,
            callsign=first.callsign,
            points=points,
            source="aeris_digital_twin",
            data_classification=classification,
        )

    def run(self, request: SimulationRequest) -> SimulationResponse:
        track = self.flights.get_track(request.icao24)
        baseline = track.points[-24:]
        simulated: list[FlightState] = []
        for index, point in enumerate(baseline):
            if index < len(baseline) // 2:
                simulated.append(point)
                continue
            injection_index = index - len(baseline) // 2 + 1
            progress = injection_index / (len(baseline) // 2)
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
            simulated_point = point.model_copy(update=updates)
            if request.wind_speed_kt > 0:
                latitude, longitude = destination_point(
                    latitude=simulated_point.latitude,
                    longitude=simulated_point.longitude,
                    # Aviation weather reports the direction wind comes from.
                    heading_degrees=(request.wind_direction_deg + 180) % 360,
                    speed_knots=request.wind_speed_kt,
                    duration_minutes=float(injection_index),
                )
                simulated_point = simulated_point.model_copy(
                    update={"latitude": latitude, "longitude": longitude}
                )
            simulated.append(simulated_point)

        baseline_track = self._track(baseline, classification=track.data_classification)
        simulated_track = self._track(simulated, classification="synthetic_simulation")
        baseline_anomaly = self.anomalies.evaluate_track(baseline_track)
        simulated_anomaly = self.anomalies.evaluate_track(simulated_track)
        baseline_prediction = self.predictions.predict_track(baseline_track)
        simulated_prediction = self.predictions.predict_track(simulated_track)

        digest = sha256(
            (
                f"{request.icao24}:{request.anomaly_type}:{request.severity:.3f}:"
                f"{request.wind_speed_kt:.1f}:{request.wind_direction_deg:.1f}"
            ).encode()
        ).hexdigest()[:12]
        return SimulationResponse(
            scenario_id=f"sim-{digest}",
            classification="synthetic_simulation",
            anomaly_type=request.anomaly_type,
            weather=SimulationWeather(
                wind_speed_kt=request.wind_speed_kt,
                wind_direction_deg=request.wind_direction_deg,
                source="user_defined_synthetic",
            ),
            baseline=baseline,
            simulated=simulated,
            model_reaction=SimulationModelReaction(
                baseline_anomaly_score=baseline_anomaly.score,
                simulated_anomaly_score=simulated_anomaly.score,
                baseline_label=baseline_anomaly.label,
                simulated_label=simulated_anomaly.label,
                anomaly_model=simulated_anomaly.model,
                trajectory_model=simulated_prediction.model,
                baseline_prediction=baseline_prediction.points,
                simulated_prediction=simulated_prediction.points,
            ),
            disclaimer=(
                "Synthetic experimental scenario, isolated from observed data and not a "
                "certified air-traffic simulator."
            ),
        )
