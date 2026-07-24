"""Ownership-aware deterministic position and exit monitoring."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from quant_trade_desk.communication.schemas import (
    OrderType,
    Side,
    TimeInForce,
    TradeIntentPayload,
)
from quant_trade_desk.portfolio.strategy_lots import StrategyLot


class PositionMonitor:
    agent_id = "position-exit-monitor"
    version = "1.0.0"

    def evaluate(
        self,
        *,
        lot: StrategyLot,
        current_price: Decimal,
        hard_stop: Decimal,
        target: Decimal | None,
        maximum_holding: timedelta,
        now: datetime | None = None,
    ) -> TradeIntentPayload | None:
        instant = (now or datetime.now(UTC)).astimezone(UTC)
        reasons: list[str] = []
        if current_price <= hard_stop:
            reasons.append("HARD_STOP")
        if target is not None and current_price >= target:
            reasons.append("PROFIT_TARGET")
        if instant - lot.opened_at.astimezone(UTC) >= maximum_holding:
            reasons.append("TIME_EXIT")
        if not reasons or lot.quantity <= 0:
            return None
        return TradeIntentPayload(
            strategy_id=lot.strategy_id,
            side=Side.SELL,
            quantity=lot.quantity,
            order_type=OrderType.LIMIT,
            limit_price=current_price,
            time_in_force=TimeInForce.DAY,
            expected_holding_seconds=60,
            invalidation_reason=";".join(reasons),
            planned_loss=Decimal("0"),
            risk_reducing=True,
        )
