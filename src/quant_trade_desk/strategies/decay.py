"""Strategy-decay detection using sample, cost, and regime stability."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class StrategyPerformance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    strategy_id: str
    net_return: Decimal
    excess_return: Decimal
    sharpe: Decimal
    sortino: Decimal
    maximum_drawdown: Decimal
    calmar: Decimal | None
    information_ratio: Decimal | None
    hit_rate: Decimal
    profit_factor: Decimal | None
    average_gain: Decimal
    average_loss: Decimal
    turnover: Decimal
    slippage_bps: Decimal
    observations: int = Field(ge=0)
    positive_regimes: int = Field(ge=0)
    tested_regimes: int = Field(ge=0)
    expectancy: Decimal


class DecayState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    detected: bool
    suspended: bool
    allocation_multiplier: Decimal = Field(ge=0, le=1)
    reason_codes: tuple[str, ...]


def evaluate_decay(
    performance: StrategyPerformance,
    *,
    minimum_observations: int = 30,
) -> DecayState:
    reasons: list[str] = []
    if performance.observations < minimum_observations:
        reasons.append("INADEQUATE_SAMPLE")
    if performance.expectancy <= 0:
        reasons.append("NON_POSITIVE_EXPECTANCY")
    if performance.excess_return <= 0:
        reasons.append("NON_POSITIVE_EXCESS_RETURN")
    if performance.sharpe <= 0:
        reasons.append("NON_POSITIVE_SHARPE")
    if performance.tested_regimes and (
        performance.positive_regimes / performance.tested_regimes < 0.5
    ):
        reasons.append("REGIME_INSTABILITY")
    detected = len(reasons) >= 3
    return DecayState(
        detected=detected,
        suspended=detected and performance.observations >= minimum_observations,
        allocation_multiplier=Decimal("0") if detected else Decimal("1"),
        reason_codes=tuple(reasons),
    )
