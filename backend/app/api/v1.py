"""Versioned HTTP routes for the AERIS vertical slice."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import AwareDatetime

from backend.app.schemas.flight import (
    AnomalyResponse,
    FlightListResponse,
    FlightTrackResponse,
    IntelligenceRequest,
    IntelligenceResponse,
    PredictionResponse,
    SimulationRequest,
    SimulationResponse,
)
from backend.app.services.container import services
from backend.app.services.flights import FlightNotFoundError, ReplayTimeOutOfRangeError

router = APIRouter(prefix="/api/v1")
Icao24Path = Annotated[str, Path(pattern=r"^[0-9a-fA-F]{6}$")]


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flight not found")


def _replay_error(error: ReplayTimeOutOfRangeError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error))


@router.get("/flights", response_model=FlightListResponse)
def list_flights(
    at: AwareDatetime | None = None,
    west: Annotated[float | None, Query(ge=-180, le=180)] = None,
    south: Annotated[float | None, Query(ge=-90, le=90)] = None,
    east: Annotated[float | None, Query(ge=-180, le=180)] = None,
    north: Annotated[float | None, Query(ge=-90, le=90)] = None,
) -> FlightListResponse:
    bounds = (west, south, east, north)
    has_partial_bounds = any(value is not None for value in bounds) and not all(
        value is not None for value in bounds
    )
    if has_partial_bounds:
        raise HTTPException(status_code=422, detail="All four bounding-box values are required")
    bbox: tuple[float, float, float, float] | None = None
    if all(value is not None for value in bounds):
        bbox = (float(west), float(south), float(east), float(north))  # type: ignore[arg-type]
    if bbox is not None and (bbox[0] >= bbox[2] or bbox[1] >= bbox[3]):
        raise HTTPException(status_code=422, detail="Bounding-box minimums must be below maximums")
    try:
        return services.flights.list_flights(at=at, bbox=bbox)
    except ReplayTimeOutOfRangeError as exc:
        raise _replay_error(exc) from exc


@router.get("/flights/{icao24}/track", response_model=FlightTrackResponse)
def flight_track(icao24: Icao24Path, at: AwareDatetime | None = None) -> FlightTrackResponse:
    try:
        return services.flights.get_track(icao24, at=at)
    except FlightNotFoundError as exc:
        raise _not_found() from exc
    except ReplayTimeOutOfRangeError as exc:
        raise _replay_error(exc) from exc


@router.get("/flights/{icao24}/prediction", response_model=PredictionResponse)
def flight_prediction(icao24: Icao24Path, at: AwareDatetime | None = None) -> PredictionResponse:
    try:
        return services.predictions.predict(icao24, at=at)
    except FlightNotFoundError as exc:
        raise _not_found() from exc
    except ReplayTimeOutOfRangeError as exc:
        raise _replay_error(exc) from exc


@router.get("/flights/{icao24}/anomaly", response_model=AnomalyResponse)
def flight_anomaly(icao24: Icao24Path, at: AwareDatetime | None = None) -> AnomalyResponse:
    try:
        return services.anomalies.evaluate(icao24, at=at)
    except FlightNotFoundError as exc:
        raise _not_found() from exc
    except ReplayTimeOutOfRangeError as exc:
        raise _replay_error(exc) from exc


@router.get("/replay/snapshot", response_model=FlightListResponse)
def replay_snapshot(at: AwareDatetime) -> FlightListResponse:
    try:
        normalized_at = services.flights.normalize_replay_time(at)
        response = services.flights.list_flights(at=normalized_at)
        response.meta.replay_at = normalized_at.isoformat()
        return response
    except ReplayTimeOutOfRangeError as exc:
        raise _replay_error(exc) from exc


@router.post("/simulations", response_model=SimulationResponse)
def create_simulation(payload: SimulationRequest) -> SimulationResponse:
    try:
        return services.simulations.run(payload)
    except FlightNotFoundError as exc:
        raise _not_found() from exc


@router.post("/intelligence/reports", response_model=IntelligenceResponse)
def create_intelligence_report(payload: IntelligenceRequest) -> IntelligenceResponse:
    try:
        return services.intelligence.create_report(payload)
    except FlightNotFoundError as exc:
        raise _not_found() from exc
    except ReplayTimeOutOfRangeError as exc:
        raise _replay_error(exc) from exc


@router.get("/analytics/summary")
def analytics_summary() -> dict[str, object]:
    flights = services.flights.list_flights()
    anomalies = [services.anomalies.evaluate(item.icao24) for item in flights.data]
    altitudes = [item.altitude_ft for item in flights.data if item.altitude_ft is not None]
    return {
        "aircraft_count": len(flights.data),
        "mean_altitude_ft": round(sum(altitudes) / len(altitudes), 1) if altitudes else None,
        "unusual_count": sum(item.label == "unusual" for item in anomalies),
        "classification": "synthetic_demo",
    }
