"""Only service permitted to call a broker adapter."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from quant_trade_desk.communication.idempotency import IdempotencyStore
from quant_trade_desk.communication.permissions import Permission, require
from quant_trade_desk.communication.schemas import (
    AssetClass,
    ProposedOrderPayload,
    RiskDecisionPayload,
    RiskOutcome,
    Side,
)
from quant_trade_desk.risk.operating_mode import ModeAuthorization
from quant_trade_desk.settings import TradingMode

from .models import (
    BrokerAdapter,
    BrokerOrderRequest,
    BrokerOrderResult,
    BrokerOrderState,
)


class ExecutionPreflight(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    account_identity_verified: bool
    account_equity: Decimal = Field(gt=0)
    buying_power: Decimal = Field(ge=0)
    current_position_quantity: Decimal = Field(ge=0)
    open_order_count: int = Field(ge=0)
    latest_bid: Decimal = Field(gt=0)
    latest_ask: Decimal = Field(gt=0)
    market_timestamp: datetime
    drawdown_ok: bool
    loss_limits_ok: bool
    kill_switch_clear: bool
    audit_available: bool
    database_available: bool
    time_synchronized: bool


class ExecutionAgent:
    agent_id = "execution-agent"
    version = "1.0.0"

    def __init__(self, idempotency: IdempotencyStore | None = None) -> None:
        self._idempotency = idempotency or IdempotencyStore()

    def execute(
        self,
        *,
        order: ProposedOrderPayload,
        risk_decision: RiskDecisionPayload,
        mode_authorization: ModeAuthorization,
        adapter: BrokerAdapter,
        asset_class: AssetClass,
        symbol: str,
        idempotency_key: str,
        preflight: ExecutionPreflight,
        now: datetime | None = None,
    ) -> BrokerOrderResult:
        require(self.agent_id, Permission.SUBMIT_ORDER)
        instant = (now or datetime.now(UTC)).astimezone(UTC)
        reasons: list[str] = []
        if risk_decision.proposed_order_id != order.proposed_order_id:
            reasons.append("RISK_ORDER_ID_MISMATCH")
        if risk_decision.valid_until.astimezone(UTC) <= instant:
            reasons.append("RISK_AUTHORIZATION_EXPIRED")
        if risk_decision.outcome == RiskOutcome.REJECTED:
            reasons.append("RISK_REJECTED")
        if risk_decision.outcome == RiskOutcome.REQUIRES_MANUAL_REVIEW:
            reasons.append("MANUAL_REVIEW_REQUIRED")
        if risk_decision.outcome == RiskOutcome.RISK_REDUCING_ONLY and not order.risk_reducing:
            reasons.append("ONLY_RISK_REDUCING_ORDER_ALLOWED")
        if risk_decision.approved_quantity != order.quantity:
            reasons.append("APPROVED_QUANTITY_DIFFERS_FROM_FINAL_ORDER")
        if len(risk_decision.context_checksum) != 64:
            reasons.append("RISK_CONTEXT_CHECKSUM_INVALID")
        if not mode_authorization.valid_for(asset_class, instant):
            reasons.append("MODE_AUTHORIZATION_INVALID")
        if mode_authorization.mode == TradingMode.PAPER and (adapter.adapter_id != "paper-broker"):
            reasons.append("PAPER_MODE_ADAPTER_MISMATCH")
        if mode_authorization.mode == TradingMode.SHADOW and (
            adapter.adapter_id != "shadow-broker"
        ):
            reasons.append("SHADOW_MODE_ADAPTER_MISMATCH")
        if mode_authorization.mode not in {
            TradingMode.PAPER,
            TradingMode.SHADOW,
            TradingMode.RESTRICTED_LIVE,
        }:
            reasons.append("OPERATING_MODE_NOT_EXECUTABLE")
        if not preflight.account_identity_verified:
            reasons.append("ACCOUNT_IDENTITY_UNVERIFIED")
        if order.side == Side.BUY:
            reference = order.limit_price or preflight.latest_ask
            if order.quantity * reference > preflight.buying_power:
                reasons.append("BUYING_POWER_CHANGED")
        if order.side == Side.SELL and order.quantity > (preflight.current_position_quantity):
            reasons.append("POSITION_CHANGED")
        if preflight.latest_bid > preflight.latest_ask:
            reasons.append("CROSSED_MARKET")
        if instant - preflight.market_timestamp.astimezone(UTC) > timedelta(seconds=15):
            reasons.append("MARKET_DATA_STALE")
        checks = {
            "DRAWDOWN_BLOCK": preflight.drawdown_ok,
            "LOSS_LIMIT_BLOCK": preflight.loss_limits_ok,
            "KILL_SWITCH_ACTIVE": preflight.kill_switch_clear,
            "AUDIT_UNAVAILABLE": preflight.audit_available,
            "DATABASE_UNAVAILABLE": preflight.database_available,
            "TIME_NOT_SYNCHRONIZED": preflight.time_synchronized,
        }
        reasons.extend(code for code, okay in checks.items() if not okay)
        capabilities = adapter.discover_capabilities()
        if not capabilities.execution_ready:
            reasons.extend(capabilities.discovery_errors or ("ADAPTER_NOT_READY",))
        if asset_class not in capabilities.asset_classes:
            reasons.append("ADAPTER_ASSET_CLASS_UNSUPPORTED")
        if capabilities.symbols and symbol.upper() not in capabilities.symbols:
            reasons.append("ADAPTER_SYMBOL_UNSUPPORTED")
        if order.order_type not in capabilities.order_types:
            reasons.append("ADAPTER_ORDER_TYPE_UNSUPPORTED")
        if order.time_in_force not in capabilities.time_in_force:
            reasons.append("ADAPTER_TIME_IN_FORCE_UNSUPPORTED")
        if capabilities.account_id != order.account_id:
            reasons.append("ADAPTER_ACCOUNT_MISMATCH")
        if reasons:
            return BrokerOrderResult(
                adapter_id=adapter.adapter_id,
                client_order_id="not-submitted",
                state=BrokerOrderState.REJECTED,
                accepted_quantity=Decimal("0"),
                reason_code=";".join(dict.fromkeys(reasons)),
            )
        if not self._idempotency.claim(idempotency_key, now=instant):
            return BrokerOrderResult(
                adapter_id=adapter.adapter_id,
                client_order_id="duplicate-not-submitted",
                state=BrokerOrderState.REJECTED,
                accepted_quantity=Decimal("0"),
                reason_code="DUPLICATE_ORDER",
            )

        client_order_id = (
            f"{symbol.upper()}:{uuid4()}" if asset_class == AssetClass.CRYPTO else str(uuid4())
        )
        request = BrokerOrderRequest(
            proposed_order=order,
            client_order_id=client_order_id,
            idempotency_key=idempotency_key,
        )
        try:
            result = adapter.submit_order(request)
        except Exception as exc:
            return BrokerOrderResult(
                adapter_id=adapter.adapter_id,
                client_order_id=client_order_id,
                state=BrokerOrderState.UNKNOWN,
                accepted_quantity=Decimal("0"),
                reason_code=f"SUBMISSION_STATE_UNCERTAIN:{type(exc).__name__}",
            )
        if result.accepted_quantity > order.quantity:
            return result.model_copy(
                update={
                    "state": BrokerOrderState.UNKNOWN,
                    "reason_code": "BROKER_ACCEPTED_QUANTITY_EXCEEDS_AUTHORIZATION",
                }
            )
        return result
