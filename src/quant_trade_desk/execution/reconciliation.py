"""Order reconciliation that never resubmits uncertain orders."""

from __future__ import annotations

from dataclasses import dataclass

from .models import BrokerAdapter, BrokerOrderResult, BrokerOrderState


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    result: BrokerOrderResult
    resubmission_allowed: bool
    reason_code: str


def reconcile_order(
    adapter: BrokerAdapter,
    broker_order_id: str,
) -> ReconciliationResult:
    try:
        result = adapter.get_order(broker_order_id)
    except Exception:
        result = BrokerOrderResult(
            adapter_id=adapter.adapter_id,
            client_order_id="unknown",
            broker_order_id=broker_order_id,
            state=BrokerOrderState.UNKNOWN,
            accepted_quantity=0,
            reason_code="RECONCILIATION_UNCERTAIN",
        )
    final = {
        BrokerOrderState.REJECTED,
        BrokerOrderState.CANCELED,
        BrokerOrderState.FILLED,
        BrokerOrderState.EXPIRED,
    }
    return ReconciliationResult(
        result=result,
        resubmission_allowed=result.state
        in {
            BrokerOrderState.REJECTED,
            BrokerOrderState.CANCELED,
            BrokerOrderState.EXPIRED,
        },
        reason_code=(
            "FINAL_STATE_RECONCILED"
            if result.state in final
            else "RESUBMISSION_BLOCKED_PENDING_RECONCILIATION"
        ),
    )
