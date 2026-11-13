"""Small thread-safe TTL cache for rate-limited provider reads."""

from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class CacheEntry(Generic[T]):
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: float, *, clock: Callable[[], float] = monotonic) -> None:
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: dict[str, CacheEntry[T]] = {}
        self._lock = Lock()

    def get(self, key: str) -> T | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= self._clock():
                self._entries.pop(key, None)
                return None
            return entry.value

    def put(self, key: str, value: T) -> None:
        with self._lock:
            self._entries[key] = CacheEntry(value, self._clock() + self._ttl_seconds)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
