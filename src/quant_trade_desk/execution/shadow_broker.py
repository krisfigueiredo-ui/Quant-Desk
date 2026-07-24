"""Shadow adapter records intent and can never submit to an external venue."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from quant_trade_desk.communication.schemas import (
    AssetClass,
    OrderType,
    TimeInForce,
)

from .models import (
    BrokerAccountSnapshot,
    BrokerCapabilities,
    BrokerOrderRequest,
    BrokerOrderResult,
    BrokerOrderState,
    BrokerQuote,
)


class ShadowBroker:
    adapter_id = "shadow-broker"

    def __init__(self, account_id: str = "shadow-account") -> None:
        self.account_id = account_id
        self._quotes: dict[str, BrokerQuote] = {}
        self._orders: dict[str, BrokerOrderResult] = {}

    def set_quote(self, quote: BrokerQuote) -> None:
        self._quotes[quote.symbol.upper()] = quote

    def discover_capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            adapter_id=self.adapter_id,
            discovered_at=datetime.now(UTC),
            authenticated=True,
            dedicated_account_verified=True,
            account_id=self.account_id,
            asset_classes=frozenset({AssetClass.EQUITY, AssetClass.CRYPTO}),
            symbols=frozenset(self._quotes),
            order_types=frozenset({OrderType.LIMIT, OrderType.MARKET}),
            time_in_force=frozenset({TimeInForce.DAY, TimeInForce.GTC}),
            fractional_support=True,
            trading_sessions=frozenset({"REGULAR", "CRYPTO_24_7"}),
            cancellation_support=False,
            position_visibility=False,
            account_visibility=True,
        )

    def get_account(self) -> BrokerAccountSnapshot:
        return BrokerAccountSnapshot(
            account_id=self.account_id,
            verified_at=datetime.now(UTC),
            equity=Decimal("100000"),
            buying_power=Decimal("100000"),
        )

    def get_quote(self, symbol: str) -> BrokerQuote:
        try:
            return self._quotes[symbol.upper()]
        except KeyError as exc:
            raise RuntimeError("shadow quote unavailable") from exc

    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        order_id = f"shadow-{request.client_order_id}"
        result = BrokerOrderResult(
            adapter_id=self.adapter_id,
            client_order_id=request.client_order_id,
            broker_order_id=order_id,
            state=BrokerOrderState.SHADOWED,
            accepted_quantity=Decimal("0"),
            reason_code="SHADOW_ONLY_NOT_SUBMITTED",
            raw_status="shadowed",
        )
        self._orders[order_id] = result
        return result

    def get_order(self, broker_order_id: str) -> BrokerOrderResult:
        try:
            return self._orders[broker_order_id]
        except KeyError as exc:
            raise RuntimeError("unknown shadow order") from exc

    def cancel_order(self, broker_order_id: str) -> BrokerOrderResult:
        return self.get_order(broker_order_id)
