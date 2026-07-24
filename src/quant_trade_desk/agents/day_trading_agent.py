"""Deterministic intraday strategy intent generation."""

from __future__ import annotations

from decimal import Decimal

from quant_trade_desk.communication.permissions import Permission, require
from quant_trade_desk.communication.schemas import (
    AssessmentPayload,
    EventRiskPayload,
    OrderType,
    Side,
    TimeInForce,
    TradeIntentPayload,
)


class DayTradingAgent:
    agent_id = "day-trading-strategy-agent"
    version = "1.0.0"
    strategy_id = "equity-intraday-trend-pullback-v1"

    def create_intent(
        self,
        *,
        assessment: AssessmentPayload,
        event_risk: EventRiskPayload,
        quantity: Decimal,
        limit_price: Decimal,
        planned_loss: Decimal,
        maximum_holding_seconds: int,
        session_eligible: bool,
    ) -> TradeIntentPayload | None:
        require(self.agent_id, Permission.GENERATE_SIGNAL)
        if (
            event_risk.event_block
            or assessment.decision != "QUALIFIED"
            or assessment.score < 60
            or not session_eligible
            or len(assessment.bullish_evidence) < 3
        ):
            return None
        return TradeIntentPayload(
            strategy_id=self.strategy_id,
            side=Side.BUY,
            quantity=quantity,
            order_type=OrderType.LIMIT,
            limit_price=limit_price,
            time_in_force=TimeInForce.DAY,
            expected_holding_seconds=maximum_holding_seconds,
            invalidation_reason="Technical invalidation or deterministic session cutoff.",
            planned_loss=planned_loss,
        )
