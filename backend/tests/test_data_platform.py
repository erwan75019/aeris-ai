import asyncio
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import DateTime, Table
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import FlightObservationRecord
from backend.app.db.session import create_engine, create_session_factory, session_scope
from backend.app.repositories.flights import PostgresFlightRepository
from backend.app.schemas.flight import FlightState
from backend.app.services.ingestion import batch_key, ingest_states


def observation(icao24: str = "abc123", minute: int = 0) -> FlightState:
    return FlightState(
        icao24=icao24,
        callsign="TEST01",
        latitude=48.5,
        longitude=2.2,
        altitude_ft=30_000,
        ground_speed_kt=420,
        heading_deg=90,
        vertical_rate_fpm=0,
        timestamp=datetime(2026, 1, 1, 12, minute, tzinfo=UTC),
        source="test_fixture",
    )


def test_observation_schema_has_identity_and_spatial_indexes() -> None:
    table = cast(Table, FlightObservationRecord.__table__)
    constraint_names = {constraint.name for constraint in table.constraints}
    index_names = {index.name for index in table.indexes}

    assert "uq_observation_identity" in constraint_names
    assert "ix_observation_aircraft_time" in index_names
    assert "ix_observation_time_brin" in index_names
    assert "ix_observation_position_gist" in index_names
    assert cast(DateTime, table.c.observed_at.type).timezone is True


def test_batch_key_is_stable_across_retry_order() -> None:
    states = [observation(minute=1), observation(minute=2)]

    assert batch_key(states) == batch_key(list(reversed(states)))
    assert batch_key(states) != batch_key([observation(minute=3)])


def test_repository_emits_idempotent_postgres_upsert() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = MagicMock(rowcount=1)
    repository = PostgresFlightRepository(session)

    result = asyncio.run(ingest_states(repository, [observation()]))
    statement = session.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))  # type: ignore[no-untyped-call]

    assert result.input_count == 1
    assert result.persisted_count == 1
    assert "ON CONFLICT ON CONSTRAINT uq_observation_identity DO UPDATE" in sql


def test_empty_repository_batch_does_not_touch_database() -> None:
    session = AsyncMock(spec=AsyncSession)
    repository = PostgresFlightRepository(session)

    assert asyncio.run(repository.upsert_many([])) == 0
    session.execute.assert_not_awaited()


def test_repository_reads_track_rows() -> None:
    session = AsyncMock(spec=AsyncSession)
    row: dict[str, Any] = {
        "icao24": "abc123",
        "callsign": "TEST01",
        "latitude": 48.5,
        "longitude": 2.2,
        "altitude_ft": 30_000.0,
        "ground_speed_kt": 420.0,
        "heading_deg": 90.0,
        "vertical_rate_fpm": 0.0,
        "observed_at": datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        "source": "test_fixture",
        "on_ground": False,
    }
    result = MagicMock()
    result.mappings.return_value.all.return_value = [row]
    session.execute.return_value = result

    states = asyncio.run(
        PostgresFlightRepository(session).track(
            "ABC123", start=row["observed_at"], end=row["observed_at"], limit=1
        )
    )

    assert states == [observation()]


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeSessionContext:
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    async def __aenter__(self) -> FakeSession:
        return self.session

    async def __aexit__(self, *_args: object) -> None:
        return None


class FakeSessionFactory:
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    def __call__(self) -> FakeSessionContext:
        return FakeSessionContext(self.session)


def test_session_helpers_commit_and_rollback() -> None:
    engine = create_engine("postgresql+asyncpg://aeris:aeris@localhost/aeris")
    assert create_session_factory(engine).kw["expire_on_commit"] is False
    asyncio.run(engine.dispose())

    committed = FakeSession()

    async def successful_scope() -> None:
        async with session_scope(cast(Any, FakeSessionFactory(committed))):
            pass

    asyncio.run(successful_scope())
    assert committed.committed is True

    rolled_back = FakeSession()

    async def failing_scope() -> None:
        async with session_scope(cast(Any, FakeSessionFactory(rolled_back))):
            raise RuntimeError("expected")

    try:
        asyncio.run(failing_scope())
    except RuntimeError as error:
        assert str(error) == "expected"
    assert rolled_back.rolled_back is True
