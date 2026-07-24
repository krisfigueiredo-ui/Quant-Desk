"""Shared broker adapter contract."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from quant_trade_desk.communication.schemas import (
    AssetClass,
    OrderType,
    ProposedOrderPayload,
    TimeInForce,
)


class BrokerOrderState(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CANCELED = "CANCELED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"
    SHADOWED = "SHADOWED"


class BrokerCapabilities(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    adapter_id: str
    discovered_at: datetime
    authenticated: bool
    dedicated_account_verified: bool
    account_id: str | None = None
    asset_classes: frozenset[AssetClass] = frozenset()
    symbols: frozenset[str] = frozenset()
    order_types: frozenset[OrderType] = frozenset()
    time_in_force: frozenset[TimeInForce] = frozenset()
    fractional_support: bool = False
    trading_sessions: frozenset[str] = frozenset()
    cancellation_support: bool = False
    position_visibility: bool = False
    account_visibility: bool = False
    tool_names: frozenset[str] = frozenset()
    discovery_errors: tuple[str, ...] = ()

    @property
    def execution_ready(self) -> bool:
        return (
            self.authenticated
            and self.dedicated_account_verified
            and bool(self.order_types)
            and bool(self.asset_classes)
            and not self.discovery_errors
        )


class BrokerAccountSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    account_id: str
    verified_at: datetime
    equity: Decimal = Field(gt=0)
    buying_power: Decimal = Field(ge=0)


class BrokerQuote(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    timestamp: datetime
    bid: Decimal = Field(gt=0)
    ask: Decimal = Field(gt=0)

    @property
    def spread_bps(self) -> Decimal:
        midpoint = (self.bid + self.ask) / Decimal("2")
        return (self.ask - self.bid) / midpoint * Decimal("10000")


class BrokerOrderRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    proposed_order: ProposedOrderPayload
    client_order_id: str = Field(min_length=8, max_length=128)
    idempotency_key: str = Field(min_length=8, max_length=256)


class BrokerOrderResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    adapter_id: str
    client_order_id: str
    broker_order_id: str | None = None
    state: BrokerOrderState
    accepted_quantity: Decimal = Field(ge=0)
    filled_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    average_fill_price: Decimal | None = Field(default=None, ge=0)
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reason_code: str
    raw_status: str | None = None


class BrokerAdapter(Protocol):
    adapter_id: str

    def discover_capabilities(self) -> BrokerCapabilities: ...

    def get_account(self) -> BrokerAccountSnapshot: ...

    def get_quote(self, symbol: str) -> BrokerQuote: ...

    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult: ...

    def get_order(self, broker_order_id: str) -> BrokerOrderResult: ...

    def cancel_order(self, broker_order_id: str) -> BrokerOrderResult: ...
