"""Deterministic local paper adapter; no external broker calls."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from threading import RLock
from uuid import uuid4

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


class PaperBroker:
    adapter_id = "paper-broker"

    def __init__(
        self,
        *,
        account_id: str = "paper-account",
        equity: Decimal = Decimal("100000"),
    ) -> None:
        self.account_id = account_id
        self.equity = equity
        self.buying_power = equity
        self._quotes: dict[str, BrokerQuote] = {}
        self._orders: dict[str, BrokerOrderResult] = {}
        self._idempotency: dict[str, str] = {}
        self._lock = RLock()

    def set_quote(self, quote: BrokerQuote) -> None:
        with self._lock:
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
            cancellation_support=True,
            position_visibility=True,
            account_visibility=True,
        )

    def get_account(self) -> BrokerAccountSnapshot:
        return BrokerAccountSnapshot(
            account_id=self.account_id,
            verified_at=datetime.now(UTC),
            equity=self.equity,
            buying_power=self.buying_power,
        )

    def get_quote(self, symbol: str) -> BrokerQuote:
        try:
            return self._quotes[symbol.upper()]
        except KeyError as exc:
            raise RuntimeError("paper quote unavailable") from exc

    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        with self._lock:
            existing_id = self._idempotency.get(request.idempotency_key)
            if existing_id is not None:
                return self._orders[existing_id]
            order_id = f"paper-{uuid4()}"
            result = BrokerOrderResult(
                adapter_id=self.adapter_id,
                client_order_id=request.client_order_id,
                broker_order_id=order_id,
                state=BrokerOrderState.ACCEPTED,
                accepted_quantity=request.proposed_order.quantity,
                reason_code="PAPER_ORDER_ACCEPTED",
                raw_status="accepted",
            )
            self._orders[order_id] = result
            self._idempotency[request.idempotency_key] = order_id
            return result

    def get_order(self, broker_order_id: str) -> BrokerOrderResult:
        try:
            return self._orders[broker_order_id]
        except KeyError as exc:
            raise RuntimeError("unknown paper order") from exc

    def cancel_order(self, broker_order_id: str) -> BrokerOrderResult:
        with self._lock:
            current = self.get_order(broker_order_id)
            if current.state not in {
                BrokerOrderState.PENDING,
                BrokerOrderState.ACCEPTED,
                BrokerOrderState.PARTIALLY_FILLED,
            }:
                return current
            canceled = current.model_copy(
                update={
                    "state": BrokerOrderState.CANCELED,
                    "reason_code": "PAPER_ORDER_CANCELED",
                    "observed_at": datetime.now(UTC),
                    "raw_status": "canceled",
                }
            )
            self._orders[broker_order_id] = canceled
            return canceled
