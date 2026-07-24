"""Deterministic market-regime classification."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum


class MarketRegime(StrEnum):
    TRENDING = "TRENDING"
    MEAN_REVERTING = "MEAN_REVERTING"
    VOLATILITY_EXPANSION = "VOLATILITY_EXPANSION"
    RISK_OFF = "RISK_OFF"
    UNCERTAIN = "UNCERTAIN"


def classify_regime(
    *,
    trend_strength: Decimal,
    realized_volatility_z: Decimal,
    benchmark_above_long_average: bool,
) -> MarketRegime:
    if not benchmark_above_long_average:
        return MarketRegime.RISK_OFF
    if realized_volatility_z >= Decimal("2"):
        return MarketRegime.VOLATILITY_EXPANSION
    if abs(trend_strength) >= Decimal("0.6"):
        return MarketRegime.TRENDING
    if abs(trend_strength) <= Decimal("0.2"):
        return MarketRegime.MEAN_REVERTING
    return MarketRegime.UNCERTAIN
