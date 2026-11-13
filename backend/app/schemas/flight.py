"""Canonical aviation schemas and explicit unit conventions."""

from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

DataClassification = Literal["synthetic_demo", "historical", "live", "synthetic_simulation"]


class FlightState(BaseModel):
    """Normalized aircraft state.

    Altitude is expressed in feet, ground speed in knots and vertical rate in
    feet per minute. Timestamps are timezone-aware UTC values.
    """

    model_config = ConfigDict(frozen=True)

    icao24: str = Field(pattern=r"^[0-9a-f]{6}$")
    callsign: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    altitude_ft: float | None = Field(default=None, ge=-2000, le=100000)
    ground_speed_kt: float | None = Field(default=None, ge=0, le=2000)
    heading_deg: float | None = Field(default=None, ge=0, lt=360)
    vertical_rate_fpm: float | None = Field(default=None, ge=-20000, le=20000)
    timestamp: datetime
    source: str
    on_ground: bool = False


class FlightListMeta(BaseModel):
    mode: Literal["demo", "historical", "live"]
    data_classification: DataClassification
    source: str
    count: int = Field(ge=0)
    generated_at: datetime
    replay_at: str | None = None


class FlightListResponse(BaseModel):
    data: list[FlightState]
    meta: FlightListMeta


class FlightTrackResponse(BaseModel):
    icao24: str
    callsign: str | None
    points: list[FlightState]
    source: str
    data_classification: DataClassification


class PredictionPoint(BaseModel):
    horizon_minutes: int
    latitude: float
    longitude: float
    altitude_ft: float | None
    timestamp: datetime
    uncertainty_km: float | None = None


class ModelDescriptor(BaseModel):
    name: str
    version: str
    trained: bool
    metrics: dict[str, float] | None = None


class PredictionResponse(BaseModel):
    icao24: str
    generated_from: datetime
    model: ModelDescriptor
    points: list[PredictionPoint]
    disclaimer: str


class AnomalyResponse(BaseModel):
    icao24: str
    score: float = Field(ge=0, le=1)
    label: Literal["nominal", "unusual"]
    classification: DataClassification
    factors: dict[str, float]
    model: ModelDescriptor
    disclaimer: str


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    icao24: str = Field(pattern=r"^[0-9a-fA-F]{6}$")
    anomaly_type: Literal["altitude_spike", "heading_deviation", "speed_drop"]
    severity: float = Field(default=0.5, ge=0.1, le=1)
    wind_speed_kt: float = Field(default=0, ge=0, le=150)
    wind_direction_deg: float = Field(default=0, ge=0, lt=360)


class SimulationWeather(BaseModel):
    wind_speed_kt: float
    wind_direction_deg: float
    source: Literal["user_defined_synthetic"]


class SimulationModelReaction(BaseModel):
    baseline_anomaly_score: float = Field(ge=0, le=1)
    simulated_anomaly_score: float = Field(ge=0, le=1)
    baseline_label: Literal["nominal", "unusual"]
    simulated_label: Literal["nominal", "unusual"]
    anomaly_model: ModelDescriptor
    trajectory_model: ModelDescriptor
    baseline_prediction: list[PredictionPoint]
    simulated_prediction: list[PredictionPoint]


class SimulationResponse(BaseModel):
    scenario_id: str
    classification: Literal["synthetic_simulation"]
    anomaly_type: str
    weather: SimulationWeather
    baseline: list[FlightState]
    simulated: list[FlightState]
    model_reaction: SimulationModelReaction
    disclaimer: str


class IntelligenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    icao24: str = Field(pattern=r"^[0-9a-fA-F]{6}$")
    include_weather: bool = True
    at: AwareDatetime | None = None


class ToolLogEntry(BaseModel):
    agent: str | None = None
    tool: str
    status: Literal["ok", "unavailable", "error"]
    detail: str


class AgentFinding(BaseModel):
    agent: str
    status: Literal["complete", "limited", "failed"]
    facts: list[str] = Field(default_factory=list)
    predictions: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class IntelligenceResponse(BaseModel):
    icao24: str
    mode: Literal["deterministic_fallback", "llm_orchestrated"]
    llm_configured: bool
    facts: list[str]
    predictions: list[str]
    hypotheses: list[str]
    limitations: list[str]
    tool_log: list[ToolLogEntry]
    agent_findings: list[AgentFinding]
    narrative: str | None = None
    generated_at: datetime
