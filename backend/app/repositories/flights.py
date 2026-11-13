"""PostGIS-backed flight observation persistence."""

from collections.abc import Sequence
from datetime import datetime

from geoalchemy2 import WKTElement
from sqlalchemy import RowMapping, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import FlightObservationRecord
from backend.app.schemas.flight import FlightState


class PostgresFlightRepository:
    """Store normalized observations with idempotent PostgreSQL upserts."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_many(self, states: Sequence[FlightState]) -> int:
        """Insert or correct observations using their natural identity."""

        if not states:
            return 0
        values = [
            {
                "icao24": state.icao24.lower(),
                "callsign": state.callsign,
                "position": WKTElement(
                    f"POINT({state.longitude:.8f} {state.latitude:.8f})", srid=4326
                ),
                "altitude_ft": state.altitude_ft,
                "ground_speed_kt": state.ground_speed_kt,
                "heading_deg": state.heading_deg,
                "vertical_rate_fpm": state.vertical_rate_fpm,
                "observed_at": state.timestamp,
                "source": state.source,
                "on_ground": state.on_ground,
            }
            for state in states
        ]
        statement = insert(FlightObservationRecord).values(values)
        excluded = statement.excluded
        statement = statement.on_conflict_do_update(
            constraint="uq_observation_identity",
            set_={
                "callsign": excluded.callsign,
                "position": excluded.position,
                "altitude_ft": excluded.altitude_ft,
                "ground_speed_kt": excluded.ground_speed_kt,
                "heading_deg": excluded.heading_deg,
                "vertical_rate_fpm": excluded.vertical_rate_fpm,
                "on_ground": excluded.on_ground,
            },
        )
        result = await self._session.execute(statement)
        return int(result.rowcount or 0)  # type: ignore[attr-defined]

    async def track(
        self,
        icao24: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 10_000,
    ) -> list[FlightState]:
        """Return one aircraft track in chronological order."""

        latitude = func.ST_Y(FlightObservationRecord.position).label("latitude")
        longitude = func.ST_X(FlightObservationRecord.position).label("longitude")
        statement = (
            select(
                FlightObservationRecord.icao24,
                FlightObservationRecord.callsign,
                latitude,
                longitude,
                FlightObservationRecord.altitude_ft,
                FlightObservationRecord.ground_speed_kt,
                FlightObservationRecord.heading_deg,
                FlightObservationRecord.vertical_rate_fpm,
                FlightObservationRecord.observed_at,
                FlightObservationRecord.source,
                FlightObservationRecord.on_ground,
            )
            .where(FlightObservationRecord.icao24 == icao24.lower())
            .order_by(FlightObservationRecord.observed_at)
            .limit(limit)
        )
        if start is not None:
            statement = statement.where(FlightObservationRecord.observed_at >= start)
        if end is not None:
            statement = statement.where(FlightObservationRecord.observed_at <= end)
        rows = (await self._session.execute(statement)).mappings().all()
        return [self._to_state(row) for row in rows]

    @staticmethod
    def _to_state(row: RowMapping) -> FlightState:
        return FlightState(
            icao24=row["icao24"],
            callsign=row["callsign"],
            latitude=row["latitude"],
            longitude=row["longitude"],
            altitude_ft=row["altitude_ft"],
            ground_speed_kt=row["ground_speed_kt"],
            heading_deg=row["heading_deg"],
            vertical_rate_fpm=row["vertical_rate_fpm"],
            timestamp=row["observed_at"],
            source=row["source"],
            on_ground=row["on_ground"],
        )
