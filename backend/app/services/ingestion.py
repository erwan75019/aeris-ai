"""Idempotent database ingestion use case."""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass

from backend.app.repositories.flights import PostgresFlightRepository
from backend.app.schemas.flight import FlightState


@dataclass(frozen=True)
class IngestionResult:
    batch_key: str
    input_count: int
    persisted_count: int


def batch_key(states: Sequence[FlightState]) -> str:
    """Build a stable content key independent of input ordering."""

    identities = sorted(f"{s.icao24}:{s.timestamp.isoformat()}:{s.source}" for s in states)
    return hashlib.sha256("\n".join(identities).encode()).hexdigest()


async def ingest_states(
    repository: PostgresFlightRepository, states: Sequence[FlightState]
) -> IngestionResult:
    """Normalize ordering and upsert an observation batch safely."""

    ordered = sorted(states, key=lambda state: (state.timestamp, state.icao24, state.source))
    persisted = await repository.upsert_many(ordered)
    return IngestionResult(
        batch_key=batch_key(ordered), input_count=len(ordered), persisted_count=persisted
    )
