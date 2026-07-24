from __future__ import annotations

from decimal import Decimal

import pytest

from quant_trade_desk.risk.drawdown import DrawdownStage, calculate_drawdown
from quant_trade_desk.strategies.decay import (
    StrategyPerformance,
    evaluate_decay,
)
from quant_trade_desk.strategies.plateau import PlateauEvidence, evaluate_plateau


@pytest.mark.parametrize(
    ("equity", "stage", "multiplier"),
    [
        ("96000", DrawdownStage.NORMAL, "1"),
        ("95000", DrawdownStage.NOTIFY_REDUCE_25, "0.75"),
        ("90000", DrawdownStage.INCIDENT_REDUCE_50, "0.50"),
        ("85000", DrawdownStage.RISK_REDUCING_ONLY, "0"),
        ("80000", DrawdownStage.SUSPEND_AUTONOMY, "0"),
        ("75000", DrawdownStage.CAPITAL_PRESERVATION, "0"),
        ("63000", DrawdownStage.HARD_KILL, "0"),
    ],
)
def test_drawdown_stages(equity: str, stage: DrawdownStage, multiplier: str) -> None:
    state = calculate_drawdown(
        verified_current_equity=Decimal(equity),
        verified_peak_equity=Decimal("100000"),
    )
    assert state.stage == stage
    assert state.size_multiplier == Decimal(multiplier)


def test_plateau_requires_multiple_confirmations() -> None:
    weak = PlateauEvidence(
        days_since_meaningful_high=90,
        benchmark_relative_return=Decimal("-0.02"),
        sharpe_change=Decimal("-0.3"),
        expectancy=Decimal("-0.01"),
        observations=100,
        confirmation_windows=1,
    )
    assert evaluate_plateau(weak).stage == 0
    confirmed = weak.model_copy(update={"confirmation_windows": 4})
    assert evaluate_plateau(confirmed).stage == 3
    assert evaluate_plateau(confirmed).move_to_shadow


def test_decay_suspends_only_with_adequate_sample() -> None:
    performance = StrategyPerformance(
        strategy_id="fixture",
        net_return=Decimal("-0.02"),
        excess_return=Decimal("-0.03"),
        sharpe=Decimal("-0.5"),
        sortino=Decimal("-0.4"),
        maximum_drawdown=Decimal("-0.15"),
        calmar=None,
        information_ratio=None,
        hit_rate=Decimal("0.4"),
        profit_factor=Decimal("0.8"),
        average_gain=Decimal("0.01"),
        average_loss=Decimal("-0.02"),
        turnover=Decimal("1.2"),
        slippage_bps=Decimal("30"),
        observations=40,
        positive_regimes=0,
        tested_regimes=3,
        expectancy=Decimal("-0.001"),
    )
    state = evaluate_decay(performance)
    assert state.detected
    assert state.suspended
