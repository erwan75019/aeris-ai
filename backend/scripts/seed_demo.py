"""Idempotently persist the deterministic demo dataset into PostGIS."""

import asyncio

from backend.app.config import get_settings
from backend.app.db.session import create_engine, create_session_factory
from backend.app.providers.demo import DemoFlightProvider
from backend.app.repositories.flights import PostgresFlightRepository
from backend.app.services.ingestion import ingest_states


async def seed() -> None:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("AERIS_DATABASE_URL is required")
    engine = create_engine(settings.database_url)
    factory = create_session_factory(engine)
    provider = DemoFlightProvider()
    states = [point for flight in provider.snapshot() for point in provider.track(flight.icao24)]
    async with factory.begin() as session:
        result = await ingest_states(PostgresFlightRepository(session), states)
    await engine.dispose()
    print(
        f"Seeded {result.persisted_count}/{result.input_count} observations "
        f"(batch {result.batch_key[:12]})."
    )


if __name__ == "__main__":
    asyncio.run(seed())
