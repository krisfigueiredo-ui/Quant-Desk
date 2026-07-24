from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from quant_trade_desk.execution.models import (
    BrokerAccountSnapshot,
    BrokerCapabilities,
    BrokerOrderRequest,
    BrokerOrderResult,
    BrokerOrderState,
    BrokerQuote,
)
from quant_trade_desk.execution.reconciliation import reconcile_order


class BrokenAdapter:
    adapter_id = "broken"

    def discover_capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            adapter_id=self.adapter_id,
            discovered_at=datetime.now(UTC),
            authenticated=False,
            dedicated_account_verified=False,
            discovery_errors=("BROKER_DISCONNECTED",),
        )

    def get_account(self) -> BrokerAccountSnapshot:
        raise RuntimeError("offline")

    def get_quote(self, symbol: str) -> BrokerQuote:
        raise RuntimeError("offline")

    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        raise RuntimeError("unknown submission state")

    def get_order(self, broker_order_id: str) -> BrokerOrderResult:
        raise RuntimeError("unknown order state")

    def cancel_order(self, broker_order_id: str) -> BrokerOrderResult:
        raise RuntimeError("offline")


def test_unknown_order_state_never_allows_resubmission() -> None:
    result = reconcile_order(BrokenAdapter(), "unknown-order")
    assert result.result.state == BrokerOrderState.UNKNOWN
    assert result.resubmission_allowed is False
    assert result.result.accepted_quantity == Decimal("0")
