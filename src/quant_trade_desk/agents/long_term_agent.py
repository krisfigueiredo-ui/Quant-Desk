"""Structured swing and long-term intent generation."""

from __future__ import annotations

from decimal import Decimal

from quant_trade_desk.communication.permissions import Permission, require
from quant_trade_desk.communication.schemas import (
    AssessmentPayload,
    EventRiskPayload,
    FundamentalAssessmentPayload,
    OrderType,
    Side,
    TimeInForce,
    TradeIntentPayload,
)


class LongTermInvestmentAgent:
    agent_id = "long-term-investment-agent"
    version = "1.0.0"
    strategy_id = "equity-quality-momentum-v1"

    def create_intent(
        self,
        *,
        technical: AssessmentPayload,
        fundamental: FundamentalAssessmentPayload,
        event_risk: EventRiskPayload,
        quantity: Decimal,
        limit_price: Decimal,
        planned_loss: Decimal,
        expected_holding_seconds: int,
    ) -> TradeIntentPayload | None:
        require(self.agent_id, Permission.GENERATE_SIGNAL)
        if (
            event_risk.event_block
            or technical.decision == "REJECT"
            or fundamental.score is None
            or fundamental.score < 60
            or fundamental.decision.startswith("REJECT")
        ):
            return None
        return TradeIntentPayload(
            strategy_id=self.strategy_id,
            side=Side.BUY,
            quantity=quantity,
            order_type=OrderType.LIMIT,
            limit_price=limit_price,
            time_in_force=TimeInForce.DAY,
            expected_holding_seconds=expected_holding_seconds,
            invalidation_reason="Fundamental thesis or long-horizon trend invalidation.",
            planned_loss=planned_loss,
            time_horizon="LONG_TERM",
        )
