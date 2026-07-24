"""Append-only portfolio snapshots."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from threading import RLock

from pydantic import BaseModel, ConfigDict, Field


class PortfolioSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    verified_equity: Decimal = Field(gt=0)
    cash: Decimal = Field(ge=0)
    buying_power: Decimal = Field(ge=0)
    gross_exposure: Decimal = Field(ge=0)
    equity_exposure: Decimal = Field(ge=0)
    crypto_exposure: Decimal = Field(ge=0)
    source: str


class PortfolioLedger:
    def __init__(self) -> None:
        self._snapshots: list[PortfolioSnapshot] = []
        self._lock = RLock()

    def append(self, snapshot: PortfolioSnapshot) -> None:
        with self._lock:
            if self._snapshots and snapshot.timestamp <= self._snapshots[-1].timestamp:
                raise ValueError("portfolio snapshots must be append-only by time")
            self._snapshots.append(snapshot)

    def latest(self) -> PortfolioSnapshot | None:
        with self._lock:
            return self._snapshots[-1] if self._snapshots else None

    def peak_equity(self) -> Decimal | None:
        with self._lock:
            return (
                max(snapshot.verified_equity for snapshot in self._snapshots)
                if self._snapshots
                else None
            )
