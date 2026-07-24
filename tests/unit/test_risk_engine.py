from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from quant_trade_desk.communication.schemas import (
    AssetClass,
    RiskOutcome,
    TimeInForce,
    TradingHorizon,
)
from quant_trade_desk.risk.engine import RiskContext, RiskEngine
from quant_trade_desk.risk.kill_switch import KillSwitchState


def test_clean_paper_order_is_approved(
    proposed_order: object,
    risk_context: RiskContext,
) -> None:
    decision = RiskEngine().evaluate(proposed_order, risk_context)  # type: ignore[arg-type]
    assert decision.outcome == RiskOutcome.APPROVED
    assert decision.approved_quantity == Decimal("1")


@pytest.mark.parametrize(
    ("dependency", "reason"),
    [
        ("database", "DATABASE_UNAVAILABLE"),
        ("queue", "QUEUE_UNAVAILABLE"),
        ("audit", "AUDIT_UNAVAILABLE"),
        ("broker", "BROKER_UNAVAILABLE"),
        ("time_synchronized", "TIME_SYNCHRONIZED_UNAVAILABLE"),
    ],
)
def test_dependency_failures_block_orders(
    dependency: str,
    reason: str,
    proposed_order: object,
    risk_context: RiskContext,
) -> None:
    health = risk_context.dependencies.model_copy(update={dependency: False})
    context = risk_context.model_copy(update={"dependencies": health})
    decision = RiskEngine().evaluate(proposed_order, context)  # type: ignore[arg-type]
    assert decision.outcome == RiskOutcome.REJECTED
    assert reason in decision.reason_codes


def test_stale_market_data_is_rejected(
    proposed_order: object,
    risk_context: RiskContext,
) -> None:
    stale_market = risk_context.market.model_copy(
        update={"timestamp": risk_context.now - timedelta(minutes=1)}
    )
    decision = RiskEngine().evaluate(  # type: ignore[arg-type]
        proposed_order,
        risk_context.model_copy(update={"market": stale_market}),
    )
    assert "MARKET_DATA_STALE" in decision.reason_codes


def test_unsupported_asset_is_rejected(
    proposed_order: object,
    risk_context: RiskContext,
) -> None:
    market = risk_context.market.model_copy(
        update={"asset_class": AssetClass.CRYPTO, "symbol": "DOGE-USD"}
    )
    context = risk_context.model_copy(update={"market": market})
    decision = RiskEngine().evaluate(proposed_order, context)  # type: ignore[arg-type]
    assert "SYMBOL_NOT_ALLOWLISTED" in decision.reason_codes


def test_daily_and_weekly_loss_limits(
    proposed_order: object,
    risk_context: RiskContext,
) -> None:
    account = risk_context.account.model_copy(
        update={"daily_pnl": Decimal("-1000"), "weekly_pnl": Decimal("-3000")}
    )
    decision = RiskEngine().evaluate(  # type: ignore[arg-type]
        proposed_order, risk_context.model_copy(update={"account": account})
    )
    assert "DAILY_LOSS_LIMIT" in decision.reason_codes
    assert "WEEKLY_LOSS_LIMIT" in decision.reason_codes


def test_kill_switch_vetoes_every_entry(
    proposed_order: object,
    risk_context: RiskContext,
) -> None:
    context = risk_context.model_copy(
        update={
            "kill_switch": KillSwitchState(
                killed=True,
                reason_code="TEST",
                incident_id="fixture",
            )
        }
    )
    decision = RiskEngine().evaluate(proposed_order, context)  # type: ignore[arg-type]
    assert decision.outcome == RiskOutcome.REJECTED
    assert "KILL_SWITCH_ACTIVE" in decision.reason_codes


def test_planned_loss_limit_is_enforced(
    proposed_order: object,
    risk_context: RiskContext,
) -> None:
    order = proposed_order.model_copy(update={"planned_loss": Decimal("251")})  # type: ignore[union-attr]
    decision = RiskEngine().evaluate(order, risk_context)
    assert "PLANNED_LOSS_LIMIT" in decision.reason_codes


@pytest.mark.parametrize(
    ("context_update", "reason"),
    [
        ({"equity_minutes_since_open": 5}, "EQUITY_OPENING_WINDOW_BLOCK"),
        ({"equity_day_entry_cutoff_reached": True}, "EQUITY_DAY_ENTRY_CUTOFF"),
        ({"near_earnings": True}, "EARNINGS_PROXIMITY_BLOCK"),
        ({"duplicate_order": True}, "DUPLICATE_ORDER"),
    ],
)
def test_entry_safety_gates_are_enforced(
    context_update: dict[str, object],
    reason: str,
    proposed_order: object,
    risk_context: RiskContext,
) -> None:
    decision = RiskEngine().evaluate(  # type: ignore[arg-type]
        proposed_order,
        risk_context.model_copy(update=context_update),
    )
    assert reason in decision.reason_codes


def test_crypto_day_position_uses_separate_one_percent_cap(
    proposed_order: object,
    risk_context: RiskContext,
) -> None:
    market = risk_context.market.model_copy(
        update={"asset_class": AssetClass.CRYPTO, "symbol": "BTC-USD"}
    )
    order = proposed_order.model_copy(  # type: ignore[union-attr]
        update={
            "quantity": Decimal("15"),
            "time_in_force": TimeInForce.GTC,
            "time_horizon": TradingHorizon.DAY,
        }
    )
    decision = RiskEngine().evaluate(
        order,
        risk_context.model_copy(
            update={
                "market": market,
                "equity_minutes_since_open": None,
            }
        ),
    )
    assert "CRYPTO_POSITION_LIMIT" in decision.reason_codes


def test_high_volatility_regime_reduces_approved_quantity(
    proposed_order: object,
    risk_context: RiskContext,
) -> None:
    decision = RiskEngine().evaluate(  # type: ignore[arg-type]
        proposed_order,
        risk_context.model_copy(update={"high_volatility_regime": True}),
    )
    assert decision.outcome == RiskOutcome.APPROVED
    assert decision.approved_quantity == Decimal("0.50")
