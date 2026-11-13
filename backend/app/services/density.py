"""Traffic-density forecasts with an honest persistence fallback."""

from datetime import datetime, timedelta
from pathlib import Path

from backend.app.schemas.analytics import DensityForecastPoint, DensityForecastResponse
from backend.app.schemas.flight import ModelDescriptor
from backend.app.services.flights import FlightService, ReplayTimeOutOfRangeError
from backend.ml.artifacts import ArtifactIntegrityError
from backend.ml.density import HORIZONS_MINUTES
from backend.ml.density_artifacts import DensityArtifact


class DensityService:
    def __init__(self, flights: FlightService, artifact_dir: Path | None = None) -> None:
        self.flights = flights
        self.artifact: DensityArtifact | None = None
        if artifact_dir is not None:
            try:
                self.artifact = DensityArtifact(artifact_dir)
            except (FileNotFoundError, KeyError, ValueError, ArtifactIntegrityError):
                self.artifact = None

    def _historical_count(self, generated_at: datetime, minutes_ago: int, fallback: int) -> int:
        try:
            return len(
                self.flights.list_flights(at=generated_at - timedelta(minutes=minutes_ago)).data
            )
        except ReplayTimeOutOfRangeError:
            return fallback

    def forecast(self) -> DensityForecastResponse:
        current = self.flights.list_flights()
        current_count = len(current.data)
        lag_15 = self._historical_count(current.meta.generated_at, 15, current_count)
        lag_30 = self._historical_count(current.meta.generated_at, 30, current_count)
        lag_45 = self._historical_count(current.meta.generated_at, 45, current_count)
        rolling = (current_count + lag_15 + lag_30 + lag_45) / 4
        if self.artifact is not None:
            forecast = self.artifact.predict(
                current.meta.generated_at,
                current_aircraft=current_count,
                lag_15m_aircraft=lag_15,
                lag_30m_aircraft=lag_30,
                rolling_60m_aircraft=rolling,
            )
            model = ModelDescriptor(
                name=forecast.model_name,
                version=forecast.model_version,
                trained=True,
                metrics=forecast.metrics,
            )
            predictions = forecast.predictions
        else:
            model = ModelDescriptor(name="persistence_baseline", version="1.0.0", trained=False)
            predictions = tuple(float(current_count) for _ in HORIZONS_MINUTES)
        return DensityForecastResponse(
            generated_at=current.meta.generated_at,
            current_aircraft=current_count,
            points=[
                DensityForecastPoint(
                    horizon_minutes=horizon,
                    timestamp=current.meta.generated_at + timedelta(minutes=horizon),
                    predicted_aircraft=round(predictions[index], 2),
                    persistence_baseline_aircraft=float(current_count),
                    test_mae_aircraft=(
                        round(model.metrics[f"mae_aircraft_{horizon}m"], 2)
                        if model.metrics is not None
                        else None
                    ),
                )
                for index, horizon in enumerate(HORIZONS_MINUTES)
            ],
            model=model,
            classification=current.meta.data_classification,
            disclaimer=(
                "Regional count forecast trained and evaluated only on a synthetic demand "
                "series. It is experimental, not a sector-capacity or safety prediction."
                if model.trained
                else "Persistence fallback; this is not a trained density forecast or a "
                "sector-capacity prediction."
            ),
        )
