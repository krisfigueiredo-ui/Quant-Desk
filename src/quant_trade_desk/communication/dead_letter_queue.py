"""Dead-letter records for invalid or failed message delivery."""

from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DeadLetter(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reason_code: str
    detail: str
    redacted_message: dict[str, Any]


class InMemoryDeadLetterQueue:
    def __init__(self) -> None:
        self._records: list[DeadLetter] = []
        self._lock = Lock()

    def append(self, record: DeadLetter) -> None:
        with self._lock:
            self._records.append(record)

    def records(self) -> tuple[DeadLetter, ...]:
        with self._lock:
            return tuple(self._records)
