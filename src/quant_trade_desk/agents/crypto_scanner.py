"""Allowlist-first deterministic crypto scanner."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from quant_trade_desk.data.quality import MarketSnapshot


class RankedCrypto(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    score: Decimal
    rank: int
    eligible: bool
    reason_codes: tuple[str, ...]
    metrics: dict[str, Decimal]


class CryptoMarketScanner:
    agent_id = "crypto-market-scanner"
    version = "1.0.0"

    def __init__(
        self,
        *,
        allowlist: frozenset[str] = frozenset({"BTC-USD", "ETH-USD"}),
        supported_symbols: frozenset[str] = frozenset(),
        maximum_spread_bps: Decimal = Decimal("60"),
    ) -> None:
        self.allowlist = frozenset(symbol.upper() for symbol in allowlist)
        self.supported_symbols = frozenset(symbol.upper() for symbol in supported_symbols)
        self.maximum_spread_bps = maximum_spread_bps

    def scan(self, snapshots: list[MarketSnapshot]) -> tuple[RankedCrypto, ...]:
        rows: list[tuple[MarketSnapshot, Decimal, tuple[str, ...]]] = []
        for snapshot in snapshots:
            reasons: list[str] = []
            symbol = snapshot.symbol.upper()
            if snapshot.asset_class.value != "CRYPTO":
                reasons.append("WRONG_ASSET_CLASS")
            if symbol not in self.allowlist:
                reasons.append("NOT_ALLOWLISTED")
            if symbol not in self.supported_symbols:
                reasons.append("VENUE_CAPABILITY_UNCONFIRMED")
            if not snapshot.is_fresh(timedelta(seconds=30)):
                reasons.append("STALE_DATA")
            if snapshot.spread_bps is None:
                reasons.append("MISSING_QUOTE")
            elif snapshot.spread_bps > self.maximum_spread_bps:
                reasons.append("SPREAD_TOO_WIDE")
            score = (
                snapshot.metrics.get("multi_timeframe_trend", Decimal("0")) * Decimal("0.30")
                + snapshot.metrics.get("momentum", Decimal("0")) * Decimal("0.25")
                + snapshot.metrics.get("relative_strength_btc", Decimal("0")) * Decimal("0.20")
                + snapshot.metrics.get("volume_score", Decimal("0")) * Decimal("0.15")
                - snapshot.metrics.get("realized_volatility", Decimal("0")) * Decimal("0.10")
            )
            rows.append((snapshot, score, tuple(reasons)))
        rows.sort(key=lambda row: (-row[1], row[0].symbol))
        return tuple(
            RankedCrypto(
                symbol=snapshot.symbol,
                score=score,
                rank=index,
                eligible=not reasons,
                reason_codes=reasons,
                metrics=snapshot.metrics,
            )
            for index, (snapshot, score, reasons) in enumerate(rows, start=1)
        )
