"""Deterministic equity scanner."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from quant_trade_desk.data.quality import MarketSnapshot


class RankedEquity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    score: Decimal
    rank: int
    eligible: bool
    reason_codes: tuple[str, ...]
    metrics: dict[str, Decimal]


class EquityMarketScanner:
    agent_id = "equity-market-scanner"
    version = "1.0.0"

    def __init__(
        self,
        *,
        minimum_dollar_volume: Decimal = Decimal("20000000"),
        maximum_spread_bps: Decimal = Decimal("35"),
    ) -> None:
        self.minimum_dollar_volume = minimum_dollar_volume
        self.maximum_spread_bps = maximum_spread_bps

    def scan(self, snapshots: list[MarketSnapshot]) -> tuple[RankedEquity, ...]:
        provisional: list[tuple[MarketSnapshot, Decimal, tuple[str, ...]]] = []
        for snapshot in snapshots:
            reasons: list[str] = []
            if snapshot.asset_class.value != "EQUITY":
                reasons.append("WRONG_ASSET_CLASS")
            if not snapshot.is_fresh(timedelta(minutes=2)):
                reasons.append("STALE_DATA")
            if snapshot.average_dollar_volume < self.minimum_dollar_volume:
                reasons.append("INSUFFICIENT_LIQUIDITY")
            if snapshot.spread_bps is None:
                reasons.append("MISSING_QUOTE")
            elif snapshot.spread_bps > self.maximum_spread_bps:
                reasons.append("SPREAD_TOO_WIDE")
            score = (
                snapshot.metrics.get("relative_strength", Decimal("0")) * Decimal("0.35")
                + snapshot.metrics.get("momentum", Decimal("0")) * Decimal("0.25")
                + snapshot.metrics.get("trend", Decimal("0")) * Decimal("0.20")
                + snapshot.metrics.get("breakout_proximity", Decimal("0")) * Decimal("0.10")
                - snapshot.metrics.get("realized_volatility", Decimal("0")) * Decimal("0.10")
            )
            provisional.append((snapshot, score, tuple(reasons)))
        provisional.sort(key=lambda row: (-row[1], row[0].symbol))
        return tuple(
            RankedEquity(
                symbol=snapshot.symbol,
                score=score,
                rank=index,
                eligible=not reasons,
                reason_codes=reasons,
                metrics=snapshot.metrics,
            )
            for index, (snapshot, score, reasons) in enumerate(provisional, start=1)
        )
