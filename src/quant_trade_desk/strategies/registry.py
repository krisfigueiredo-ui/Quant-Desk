"""Versioned strategy definitions and validation status."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from quant_trade_desk.communication.schemas import AssetClass


class ValidationStatus(StrEnum):
    RESEARCH = "RESEARCH"
    QUARANTINED = "QUARANTINED"
    PAPER_READY = "PAPER_READY"
    SHADOW_READY = "SHADOW_READY"
    RESTRICTED_LIVE_READY = "RESTRICTED_LIVE_READY"


class StrategyDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    strategy_id: str
    version: str
    name: str
    asset_class: AssetClass
    time_horizon: str
    entry_rules: tuple[str, ...]
    exit_rules: tuple[str, ...]
    invalidation_rules: tuple[str, ...]
    maximum_holding_seconds: int = Field(gt=0)
    eligible_sessions: tuple[str, ...]
    expected_regimes: tuple[str, ...]
    validation_status: ValidationStatus = ValidationStatus.RESEARCH
    enabled: bool = False
    maximum_allocation: float = Field(default=0.05, ge=0, le=1)
    disable_conditions: tuple[str, ...]


STRATEGIES: dict[str, StrategyDefinition] = {
    "equity-intraday-trend-pullback-v1": StrategyDefinition(
        strategy_id="equity-intraday-trend-pullback-v1",
        version="1.0.0",
        name="Equity Intraday Trend Pullback",
        asset_class=AssetClass.EQUITY,
        time_horizon="INTRADAY",
        entry_rules=(
            "liquidity and spread pass",
            "multi-timeframe trend aligned",
            "volume confirms pullback recovery",
            "not within first 15 market minutes",
        ),
        exit_rules=("hard invalidation", "time cutoff", "target or trailing exit"),
        invalidation_rules=("trend breaks", "event block", "data becomes stale"),
        maximum_holding_seconds=21_600,
        eligible_sessions=("REGULAR",),
        expected_regimes=("TRENDING",),
        disable_conditions=(
            "negative out-of-sample expectancy",
            "transaction-cost collapse",
            "plateau stage 3",
        ),
    ),
    "crypto-intraday-breakout-v1": StrategyDefinition(
        strategy_id="crypto-intraday-breakout-v1",
        version="1.0.0",
        name="Crypto Intraday Breakout",
        asset_class=AssetClass.CRYPTO,
        time_horizon="INTRADAY",
        entry_rules=(
            "allowlisted supported spot pair",
            "fresh quote and acceptable spread",
            "volume-confirmed volatility expansion",
            "BTC-relative strength confirmed",
        ),
        exit_rules=("hard invalidation", "maximum holding period", "trailing exit"),
        invalidation_rules=("breakout failure", "event block", "venue degradation"),
        maximum_holding_seconds=28_800,
        eligible_sessions=("CRYPTO_24_7",),
        expected_regimes=("TRENDING", "VOLATILITY_EXPANSION"),
        disable_conditions=(
            "negative out-of-sample expectancy",
            "slippage stress failure",
            "plateau stage 3",
        ),
    ),
    "equity-quality-momentum-v1": StrategyDefinition(
        strategy_id="equity-quality-momentum-v1",
        version="1.0.0",
        name="Equity Quality Momentum",
        asset_class=AssetClass.EQUITY,
        time_horizon="LONG_TERM",
        entry_rules=(
            "reported quality facts available",
            "valuation and revisions acceptable",
            "price and sector trends supportive",
            "no event block",
        ),
        exit_rules=("thesis invalidation", "quality deterioration", "scheduled rebalance"),
        invalidation_rules=("material thesis break", "risk veto"),
        maximum_holding_seconds=31_536_000,
        eligible_sessions=("REGULAR",),
        expected_regimes=("TRENDING", "NEUTRAL"),
        disable_conditions=("sample inadequate", "regime instability", "decay detected"),
    ),
}
