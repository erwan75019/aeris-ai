"""Aviation weather response contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WeatherObservation(BaseModel):
    station: str
    observed_at: datetime
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    temperature_c: float | None = None
    dewpoint_c: float | None = None
    wind_direction_deg: float | None = Field(default=None, ge=0, le=360)
    wind_speed_kt: float | None = Field(default=None, ge=0)
    visibility_sm: float | None = Field(default=None, ge=0)
    flight_category: str | None = None
    raw_report: str | None = None
    source: str
    data_classification: Literal["live", "synthetic_demo"]
