"""Typed analytics and experimental density-forecast contracts."""

from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.schemas.flight import DataClassification, ModelDescriptor


class AnalyticsSummary(BaseModel):
    aircraft_count: int = Field(ge=0)
    mean_altitude_ft: float | None
    unusual_count: int = Field(ge=0)
    classification: DataClassification


class DensityForecastPoint(BaseModel):
    horizon_minutes: int = Field(gt=0)
    timestamp: datetime
    predicted_aircraft: float = Field(ge=0)
    persistence_baseline_aircraft: float = Field(ge=0)
    test_mae_aircraft: float | None = Field(default=None, ge=0)


class DensityForecastResponse(BaseModel):
    generated_at: datetime
    current_aircraft: int = Field(ge=0)
    points: list[DensityForecastPoint]
    model: ModelDescriptor
    classification: DataClassification
    disclaimer: str
