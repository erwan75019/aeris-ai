"""Create PostGIS observation and ingestion audit tables.

Revision ID: 20261112_0001
Revises: None
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "20261112_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "flight_observations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("icao24", sa.String(length=6), nullable=False),
        sa.Column("callsign", sa.Text(), nullable=True),
        sa.Column(
            "position",
            geoalchemy2.Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("altitude_ft", sa.Float(), nullable=True),
        sa.Column("ground_speed_kt", sa.Float(), nullable=True),
        sa.Column("heading_deg", sa.Float(), nullable=True),
        sa.Column("vertical_rate_fpm", sa.Float(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("on_ground", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("icao24 ~ '^[0-9a-f]{6}$'", name="ck_observation_icao24"),
        sa.CheckConstraint(
            "altitude_ft IS NULL OR altitude_ft BETWEEN -2000 AND 100000",
            name="ck_observation_altitude",
        ),
        sa.CheckConstraint(
            "ground_speed_kt IS NULL OR ground_speed_kt BETWEEN 0 AND 2000",
            name="ck_observation_speed",
        ),
        sa.CheckConstraint(
            "heading_deg IS NULL OR heading_deg >= 0 AND heading_deg < 360",
            name="ck_observation_heading",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("icao24", "observed_at", "source", name="uq_observation_identity"),
    )
    op.create_index(
        "ix_observation_aircraft_time",
        "flight_observations",
        ["icao24", "observed_at"],
    )
    op.create_index(
        "ix_observation_time_brin",
        "flight_observations",
        ["observed_at"],
        postgresql_using="brin",
    )
    op.create_index(
        "ix_observation_position_gist",
        "flight_observations",
        ["position"],
        postgresql_using="gist",
    )
    op.create_table(
        "ingestion_batches",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("batch_key", sa.String(length=64), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("input_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("persisted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('running', 'succeeded', 'failed')", name="ck_batch_status"),
        sa.CheckConstraint("input_count >= 0 AND persisted_count >= 0", name="ck_batch_counts"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_key"),
    )
    op.create_index("ix_ingestion_batch_started", "ingestion_batches", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_ingestion_batch_started", table_name="ingestion_batches")
    op.drop_table("ingestion_batches")
    op.drop_index("ix_observation_position_gist", table_name="flight_observations")
    op.drop_index("ix_observation_time_brin", table_name="flight_observations")
    op.drop_index("ix_observation_aircraft_time", table_name="flight_observations")
    op.drop_table("flight_observations")
