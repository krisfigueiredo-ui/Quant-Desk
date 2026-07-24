from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from quant_trade_desk.communication.schemas import AssetClass, RiskOutcome, Side
from quant_trade_desk.execution.execution_agent import (
    ExecutionAgent,
    ExecutionPreflight,
)
from quant_trade_desk.execution.models import (
    BrokerOrderRequest,
    BrokerOrderResult,
    BrokerOrderState,
    BrokerQuote,
)
from quant_trade_desk.execution.paper_broker import PaperBroker
from quant_trade_desk.risk.engine import RiskContext, RiskEngine
from quant_trade_desk.risk.operating_mode import authorize_mode
from quant_trade_desk.settings import Settings, TradingMode


class FakeLiveBroker(PaperBroker):
    adapter_id = "fake-live-broker"

    def __init__(self) -> None:
        super().__init__(account_id="paper-account")
        self.submitted = False

    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        self.submitted = True
        return super().submit_order(request)


def _preflight(context: RiskContext) -> ExecutionPreflight:
    return ExecutionPreflight(
        account_identity_verified=True,
        account_equity=context.account.equity,
        buying_power=context.account.buying_power,
        current_position_quantity=Decimal("10"),
        open_order_count=0,
        latest_bid=Decimal("99.95"),
        latest_ask=Decimal("100.05"),
        market_timestamp=context.now,
        drawdown_ok=True,
        loss_limits_ok=True,
        kill_switch_clear=True,
        audit_available=True,
        database_available=True,
        time_synchronized=True,
    )


def _broker(context: RiskContext) -> PaperBroker:
    broker = PaperBroker(account_id="paper-account")
    broker.set_quote(
        BrokerQuote(
            symbol="SPY",
            timestamp=context.now,
            bid=Decimal("99.95"),
            ask=Decimal("100.05"),
        )
    )
    return broker


def test_execution_requires_exact_risk_authorization(
    proposed_order: object,
    risk_context: RiskContext,
) -> None:
    order = proposed_order
    risk = RiskEngine().evaluate(order, risk_context)  # type: ignore[arg-type]
    changed = risk.model_copy(update={"approved_quantity": Decimal("2")})
    result = ExecutionAgent().execute(
        order=order,  # type: ignore[arg-type]
        risk_decision=changed,
        mode_authorization=risk_context.mode_authorization,
        adapter=_broker(risk_context),
        asset_class=AssetClass.EQUITY,
        symbol="SPY",
        idempotency_key="execution-fixture-0001",
        preflight=_preflight(risk_context),
        now=risk_context.now,
    )
    assert result.state == BrokerOrderState.REJECTED
    assert "APPROVED_QUANTITY_DIFFERS" in result.reason_code


def test_execution_cannot_bypass_rejection(
    proposed_order: object,
    risk_context: RiskContext,
) -> None:
    risk = RiskEngine().evaluate(proposed_order, risk_context)  # type: ignore[arg-type]
    rejected = risk.model_copy(
        update={
            "outcome": RiskOutcome.REJECTED,
            "approved_quantity": Decimal("0"),
        }
    )
    result = ExecutionAgent().execute(
        order=proposed_order,  # type: ignore[arg-type]
        risk_decision=rejected,
        mode_authorization=risk_context.mode_authorization,
        adapter=_broker(risk_context),
        asset_class=AssetClass.EQUITY,
        symbol="SPY",
        idempotency_key="execution-fixture-0002",
        preflight=_preflight(risk_context),
        now=risk_context.now,
    )
    assert result.state == BrokerOrderState.REJECTED
    assert "RISK_REJECTED" in result.reason_code


def test_execution_cannot_reverse_the_risk_reviewed_side(
    proposed_order: object,
    risk_context: RiskContext,
) -> None:
    decision = RiskEngine().evaluate(proposed_order, risk_context)  # type: ignore[arg-type]
    reversed_order = proposed_order.model_copy(update={"side": Side.SELL})  # type: ignore[union-attr]
    result = ExecutionAgent().execute(
        order=reversed_order,
        risk_decision=decision,
        mode_authorization=risk_context.mode_authorization,
        adapter=_broker(risk_context),
        asset_class=AssetClass.EQUITY,
        symbol="SPY",
        idempotency_key="execution-fixture-reversed-side",
        preflight=_preflight(risk_context),
        now=risk_context.now,
    )
    assert result.state == BrokerOrderState.REJECTED
    assert "FINAL_ORDER_DIFFERS_FROM_RISK_REVIEW" in result.reason_code


def test_execution_cannot_change_the_risk_reviewed_limit(
    proposed_order: object,
    risk_context: RiskContext,
) -> None:
    decision = RiskEngine().evaluate(proposed_order, risk_context)  # type: ignore[arg-type]
    changed_order = proposed_order.model_copy(  # type: ignore[union-attr]
        update={"limit_price": Decimal("101")}
    )
    result = ExecutionAgent().execute(
        order=changed_order,
        risk_decision=decision,
        mode_authorization=risk_context.mode_authorization,
        adapter=_broker(risk_context),
        asset_class=AssetClass.EQUITY,
        symbol="SPY",
        idempotency_key="execution-fixture-changed-limit",
        preflight=_preflight(risk_context),
        now=risk_context.now,
    )
    assert result.state == BrokerOrderState.REJECTED
    assert "FINAL_ORDER_DIFFERS_FROM_RISK_REVIEW" in result.reason_code


def test_paper_execution_and_duplicate_protection(
    proposed_order: object,
    risk_context: RiskContext,
) -> None:
    order = proposed_order
    decision = RiskEngine().evaluate(order, risk_context)  # type: ignore[arg-type]
    agent = ExecutionAgent()
    broker = _broker(risk_context)
    arguments = {
        "order": order,
        "risk_decision": decision,
        "mode_authorization": risk_context.mode_authorization,
        "adapter": broker,
        "asset_class": AssetClass.EQUITY,
        "symbol": "SPY",
        "idempotency_key": "execution-fixture-0003",
        "preflight": _preflight(risk_context),
        "now": risk_context.now,
    }
    first = agent.execute(**arguments)  # type: ignore[arg-type]
    duplicate = agent.execute(**arguments)  # type: ignore[arg-type]
    assert first.state == BrokerOrderState.ACCEPTED
    assert duplicate.state == BrokerOrderState.REJECTED
    assert duplicate.reason_code == "DUPLICATE_ORDER"


def test_stale_preflight_blocks_submission(
    proposed_order: object,
    risk_context: RiskContext,
) -> None:
    decision = RiskEngine().evaluate(proposed_order, risk_context)  # type: ignore[arg-type]
    preflight = _preflight(risk_context).model_copy(
        update={"market_timestamp": risk_context.now - timedelta(minutes=1)}
    )
    result = ExecutionAgent().execute(
        order=proposed_order,  # type: ignore[arg-type]
        risk_decision=decision,
        mode_authorization=risk_context.mode_authorization,
        adapter=_broker(risk_context),
        asset_class=AssetClass.EQUITY,
        symbol="SPY",
        idempotency_key="execution-fixture-0004",
        preflight=preflight,
        now=risk_context.now,
    )
    assert result.state == BrokerOrderState.REJECTED
    assert "MARKET_DATA_STALE" in result.reason_code


def test_paper_and_shadow_modes_cannot_reach_live_adapter(
    proposed_order: object,
    risk_context: RiskContext,
) -> None:
    decision = RiskEngine().evaluate(proposed_order, risk_context)  # type: ignore[arg-type]
    for mode in (TradingMode.PAPER, TradingMode.SHADOW):
        adapter = FakeLiveBroker()
        adapter.set_quote(
            BrokerQuote(
                symbol="SPY",
                timestamp=risk_context.now,
                bid=Decimal("99.95"),
                ask=Decimal("100.05"),
            )
        )
        authorization = authorize_mode(Settings(trading_mode=mode))
        result = ExecutionAgent().execute(
            order=proposed_order,  # type: ignore[arg-type]
            risk_decision=decision,
            mode_authorization=authorization,
            adapter=adapter,
            asset_class=AssetClass.EQUITY,
            symbol="SPY",
            idempotency_key=f"mode-isolation-{mode.value}",
            preflight=_preflight(risk_context),
            now=risk_context.now,
        )
        assert result.state == BrokerOrderState.REJECTED
        assert f"{mode.value}_MODE_ADAPTER_MISMATCH" in result.reason_code
        assert adapter.submitted is False
