"""Thread-safe idempotency primitives."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from threading import Lock


class IdempotencyStore:
    def __init__(self) -> None:
        self._entries: dict[str, datetime] = {}
        self._lock = Lock()

    def claim(
        self,
        key: str,
        *,
        ttl: timedelta = timedelta(days=7),
        now: datetime | None = None,
    ) -> bool:
        instant = (now or datetime.now(UTC)).astimezone(UTC)
        with self._lock:
            self._entries = {
                existing: expires
                for existing, expires in self._entries.items()
                if expires > instant
            }
            if key in self._entries:
                return False
            self._entries[key] = instant + ttl
            return True

    def contains(self, key: str, now: datetime | None = None) -> bool:
        instant = (now or datetime.now(UTC)).astimezone(UTC)
        with self._lock:
            expiry = self._entries.get(key)
            return expiry is not None and expiry > instant
