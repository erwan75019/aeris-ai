"""PostgreSQL/PostGIS persistence model definitions."""

from datetime import datetime

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKBElement
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class FlightObservationRecord(Base):
    """One normalized point-in-time aircraft observation."""

    __tablename__ = "flight_observations"
    __table_args__ = (
        UniqueConstraint("icao24", "observed_at", "source", name="uq_observation_identity"),
        CheckConstraint("icao24 ~ '^[0-9a-f]{6}$'", name="ck_observation_icao24"),
        CheckConstraint(
            "altitude_ft IS NULL OR altitude_ft BETWEEN -2000 AND 100000",
            name="ck_observation_altitude",
        ),
        CheckConstraint(
            "ground_speed_kt IS NULL OR ground_speed_kt BETWEEN 0 AND 2000",
            name="ck_observation_speed",
        ),
        CheckConstraint(
            "heading_deg IS NULL OR heading_deg >= 0 AND heading_deg < 360",
            name="ck_observation_heading",
        ),
        Index("ix_observation_aircraft_time", "icao24", "observed_at"),
        Index("ix_observation_time_brin", "observed_at", postgresql_using="brin"),
        Index("ix_observation_position_gist", "position", postgresql_using="gist"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    icao24: Mapped[str] = mapped_column(String(6), nullable=False)
    callsign: Mapped[str | None] = mapped_column(Text)
    position: Mapped[WKBElement] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    altitude_ft: Mapped[float | None] = mapped_column(Float)
    ground_speed_kt: Mapped[float | None] = mapped_column(Float)
    heading_deg: Mapped[float | None] = mapped_column(Float)
    vertical_rate_fpm: Mapped[float | None] = mapped_column(Float)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    on_ground: Mapped[bool] = mapped_column(nullable=False, default=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class IngestionBatchRecord(Base):
    """Audit record for one idempotent ingestion attempt."""

    __tablename__ = "ingestion_batches"
    __table_args__ = (
        CheckConstraint("status IN ('running', 'succeeded', 'failed')", name="ck_batch_status"),
        CheckConstraint("input_count >= 0 AND persisted_count >= 0", name="ck_batch_counts"),
        Index("ix_ingestion_batch_started", "started_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    batch_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    input_count: Mapped[int] = mapped_column(nullable=False, default=0)
    persisted_count: Mapped[int] = mapped_column(nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
