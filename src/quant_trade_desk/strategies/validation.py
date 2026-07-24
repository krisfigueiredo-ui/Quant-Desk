"""Honest, dependency-light strategy validation primitives.

This module evaluates supplied return observations. It never downloads data,
invents fills, or promotes a strategy automatically.
"""

from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DatasetSplit(StrEnum):
    TRAIN = "TRAIN"
    VALIDATION = "VALIDATION"
    TEST = "TEST"


class ReturnObservation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: datetime
    split: DatasetSplit
    strategy_return: Decimal
    benchmark_return: Decimal
    turnover: Decimal = Field(default=Decimal("0"), ge=0)

    @model_validator(mode="after")
    def timestamp_is_aware(self) -> ReturnObservation:
        if self.timestamp.tzinfo is None:
            raise ValueError("validation timestamps must be timezone-aware")
        return self


class CostAssumptions(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    commissions_bps: Decimal = Field(default=Decimal("2"), ge=0)
    spread_bps: Decimal = Field(default=Decimal("4"), ge=0)
    slippage_bps: Decimal = Field(default=Decimal("5"), ge=0)
    latency_bps: Decimal = Field(default=Decimal("1"), ge=0)
    stress_multiplier: Decimal = Field(default=Decimal("2"), ge=1)

    @property
    def round_trip_bps(self) -> Decimal:
        return self.commissions_bps + self.spread_bps + self.slippage_bps + self.latency_bps


class PerformanceMetrics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    observations: int
    total_return: Decimal
    benchmark_return: Decimal
    excess_return: Decimal
    annualized_return: Decimal
    volatility: Decimal
    sharpe: Decimal | None
    maximum_drawdown: Decimal
    turnover: Decimal


class ValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    strategy_id: str
    status: str
    test_metrics: PerformanceMetrics
    stressed_test_metrics: PerformanceMetrics
    reason_codes: tuple[str, ...]
    automatic_promotion_permitted: bool = False


def _net_returns(
    rows: list[ReturnObservation],
    assumptions: CostAssumptions,
    *,
    stress: bool,
) -> list[Decimal]:
    multiplier = assumptions.stress_multiplier if stress else Decimal("1")
    cost_rate = assumptions.round_trip_bps * multiplier / Decimal("10000")
    return [row.strategy_return - row.turnover * cost_rate for row in rows]


def _metrics(
    rows: list[ReturnObservation],
    assumptions: CostAssumptions,
    *,
    stress: bool,
) -> PerformanceMetrics:
    returns = _net_returns(rows, assumptions, stress=stress)
    benchmark = [row.benchmark_return for row in rows]
    equity = Decimal("1")
    peak = Decimal("1")
    maximum_drawdown = Decimal("0")
    for period_return in returns:
        equity *= Decimal("1") + period_return
        peak = max(peak, equity)
        maximum_drawdown = min(maximum_drawdown, (equity - peak) / peak)
    benchmark_equity = Decimal("1")
    for period_return in benchmark:
        benchmark_equity *= Decimal("1") + period_return
    total_return = equity - Decimal("1")
    benchmark_return = benchmark_equity - Decimal("1")
    float_returns = [float(value) for value in returns]
    mean = sum(float_returns) / len(float_returns)
    variance = sum((value - mean) ** 2 for value in float_returns) / max(len(float_returns) - 1, 1)
    daily_volatility = math.sqrt(variance)
    volatility = daily_volatility * math.sqrt(252)
    sharpe = mean / daily_volatility * math.sqrt(252) if daily_volatility > 0 else None
    annualized = (float(equity) ** (252 / len(rows))) - 1 if equity > 0 else -1
    return PerformanceMetrics(
        observations=len(rows),
        total_return=Decimal(str(total_return)),
        benchmark_return=Decimal(str(benchmark_return)),
        excess_return=Decimal(str(total_return - benchmark_return)),
        annualized_return=Decimal(str(annualized)),
        volatility=Decimal(str(volatility)),
        sharpe=Decimal(str(sharpe)) if sharpe is not None else None,
        maximum_drawdown=maximum_drawdown,
        turnover=sum((row.turnover for row in rows), Decimal("0")),
    )


def validate_strategy(
    strategy_id: str,
    observations: list[ReturnObservation],
    assumptions: CostAssumptions | None = None,
    *,
    minimum_test_observations: int = 30,
) -> ValidationResult:
    """Validate a chronological train/validation/test dataset.

    The untouched test split must occur strictly after train and validation.
    The result remains non-promotable even when metrics pass.
    """

    if not observations:
        raise ValueError("EMPTY_DATASET")
    ordered = sorted(observations, key=lambda row: row.timestamp)
    if len({row.timestamp for row in ordered}) != len(ordered):
        raise ValueError("DUPLICATE_TIMESTAMP")
    by_split = {split: [row for row in ordered if row.split == split] for split in DatasetSplit}
    if any(not rows for rows in by_split.values()):
        raise ValueError("ALL_SPLITS_REQUIRED")
    if not (
        max(row.timestamp for row in by_split[DatasetSplit.TRAIN])
        < min(row.timestamp for row in by_split[DatasetSplit.VALIDATION])
        <= max(row.timestamp for row in by_split[DatasetSplit.VALIDATION])
        < min(row.timestamp for row in by_split[DatasetSplit.TEST])
    ):
        raise ValueError("NON_CHRONOLOGICAL_OR_OVERLAPPING_SPLITS")

    configured = assumptions or CostAssumptions()
    test_rows = by_split[DatasetSplit.TEST]
    test_metrics = _metrics(test_rows, configured, stress=False)
    stressed_metrics = _metrics(test_rows, configured, stress=True)
    reasons: list[str] = []
    if test_metrics.observations < minimum_test_observations:
        reasons.append("INADEQUATE_TEST_SAMPLE")
    if test_metrics.excess_return <= 0:
        reasons.append("NON_POSITIVE_TEST_EXCESS_RETURN")
    if test_metrics.sharpe is None or test_metrics.sharpe <= 0:
        reasons.append("NON_POSITIVE_TEST_SHARPE")
    if test_metrics.maximum_drawdown <= Decimal("-0.25"):
        reasons.append("TEST_DRAWDOWN_LIMIT")
    if stressed_metrics.excess_return <= 0:
        reasons.append("TRANSACTION_COST_STRESS_FAILURE")
    return ValidationResult(
        strategy_id=strategy_id,
        status="QUARANTINED" if reasons else "RESEARCH_REVIEW_REQUIRED",
        test_metrics=test_metrics,
        stressed_test_metrics=stressed_metrics,
        reason_codes=tuple(reasons) or ("MINIMUM_STATISTICAL_CHECKS_PASSED",),
    )
