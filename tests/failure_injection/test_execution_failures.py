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


class PartialFillAdapter(BrokenAdapter):
    adapter_id = "partial-fill-fixture"

    def get_order(self, broker_order_id: str) -> BrokerOrderResult:
        return BrokerOrderResult(
            adapter_id=self.adapter_id,
            client_order_id="fixture-client-order",
            broker_order_id=broker_order_id,
            state=BrokerOrderState.PARTIALLY_FILLED,
            accepted_quantity=Decimal("10"),
            filled_quantity=Decimal("4"),
            average_fill_price=Decimal("100.25"),
            reason_code="PARTIAL_FILL",
        )


def test_partial_fill_preserves_quantity_and_blocks_resubmission() -> None:
    reconciled = reconcile_order(PartialFillAdapter(), "partial-order")
    assert reconciled.result.state == BrokerOrderState.PARTIALLY_FILLED
    assert reconciled.result.filled_quantity == Decimal("4")
    assert reconciled.result.accepted_quantity == Decimal("10")
    assert reconciled.resubmission_allowed is False
