"""Market-data quality validation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from quant_trade_desk.communication.schemas import AssetClass


class MarketSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    asset_class: AssetClass
    symbol: str
    timestamp: datetime
    last: Decimal = Field(gt=0)
    bid: Decimal | None = Field(default=None, gt=0)
    ask: Decimal | None = Field(default=None, gt=0)
    volume: Decimal = Field(default=Decimal("0"), ge=0)
    average_dollar_volume: Decimal = Field(default=Decimal("0"), ge=0)
    metrics: dict[str, Decimal] = Field(default_factory=dict)
    market_open: bool = True
    source_id: str

    @model_validator(mode="after")
    def valid_snapshot(self) -> MarketSnapshot:
        if self.timestamp.tzinfo is None:
            raise ValueError("market timestamp must be timezone-aware")
        if self.bid is not None and self.ask is not None and self.bid > self.ask:
            raise ValueError("crossed market")
        return self

    @property
    def spread_bps(self) -> Decimal | None:
        if self.bid is None or self.ask is None:
            return None
        midpoint = (self.bid + self.ask) / Decimal("2")
        return (self.ask - self.bid) / midpoint * Decimal("10000")

    def is_fresh(
        self,
        maximum_age: timedelta,
        *,
        now: datetime | None = None,
    ) -> bool:
        instant = (now or datetime.now(UTC)).astimezone(UTC)
        return timedelta(0) <= instant - self.timestamp.astimezone(UTC) <= maximum_age
