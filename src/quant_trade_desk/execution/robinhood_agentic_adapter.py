"""Robinhood Trading MCP capability boundary for long equities only.

The application cannot assume that a persistent server can call a user's
Codex/Desktop MCP session. An authenticated bridge must supply the exact
runtime schemas and a schema-bound executor. Without both, execution fails
closed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol

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
    BrokerQuote,
)

OFFICIAL_REQUIRED_READ_TOOLS = frozenset(
    {
        "get_accounts",
        "get_portfolio",
        "get_equity_positions",
        "get_equity_quotes",
        "get_equity_orders",
        "get_equity_tradability",
        "review_equity_order",
    }
)
OFFICIAL_EXECUTION_TOOLS = frozenset({"place_equity_order", "cancel_equity_order"})


class AgenticToolBridge(Protocol):
    def list_tools(self) -> dict[str, dict[str, Any]]: ...

    def get_verified_account(self) -> BrokerAccountSnapshot: ...

    def get_equity_quote(self, symbol: str) -> BrokerQuote: ...

    def review_and_place_equity_order(
        self,
        request: BrokerOrderRequest,
    ) -> BrokerOrderResult: ...

    def get_equity_order(self, broker_order_id: str) -> BrokerOrderResult: ...

    def cancel_equity_order(self, broker_order_id: str) -> BrokerOrderResult: ...


class RobinhoodAgenticAdapter:
    adapter_id = "robinhood-agentic-mcp"

    def __init__(
        self,
        *,
        expected_account_id: str,
        bridge: AgenticToolBridge | None = None,
    ) -> None:
        self.expected_account_id = expected_account_id
        self.bridge = bridge
        self._capabilities: BrokerCapabilities | None = None

    def discover_capabilities(self) -> BrokerCapabilities:
        if self.bridge is None:
            self._capabilities = BrokerCapabilities(
                adapter_id=self.adapter_id,
                discovered_at=datetime.now(UTC),
                authenticated=False,
                dedicated_account_verified=False,
                discovery_errors=("AUTHENTICATED_MCP_BRIDGE_UNAVAILABLE",),
            )
            return self._capabilities
        try:
            tools = self.bridge.list_tools()
            names = frozenset(tools)
            missing = sorted((OFFICIAL_REQUIRED_READ_TOOLS | OFFICIAL_EXECUTION_TOOLS) - names)
            account = self.bridge.get_verified_account()
            dedicated = account.account_id == self.expected_account_id
            errors = tuple(f"MISSING_TOOL:{name}" for name in missing)
            if not dedicated:
                errors += ("DEDICATED_ACCOUNT_MISMATCH",)
            self._capabilities = BrokerCapabilities(
                adapter_id=self.adapter_id,
                discovered_at=datetime.now(UTC),
                authenticated=True,
                dedicated_account_verified=dedicated,
                account_id=account.account_id,
                asset_classes=(frozenset({AssetClass.EQUITY}) if not errors else frozenset()),
                symbols=frozenset(),
                order_types=(
                    frozenset({OrderType.LIMIT, OrderType.MARKET}) if not errors else frozenset()
                ),
                time_in_force=(frozenset({TimeInForce.DAY}) if not errors else frozenset()),
                fractional_support=True,
                trading_sessions=frozenset({"REGULAR"}),
                cancellation_support="cancel_equity_order" in names,
                position_visibility="get_equity_positions" in names,
                account_visibility="get_accounts" in names,
                tool_names=names,
                discovery_errors=errors,
            )
            return self._capabilities
        except Exception as exc:
            self._capabilities = BrokerCapabilities(
                adapter_id=self.adapter_id,
                discovered_at=datetime.now(UTC),
                authenticated=False,
                dedicated_account_verified=False,
                discovery_errors=(f"DISCOVERY_FAILED:{type(exc).__name__}",),
            )
            return self._capabilities

    def _ready_bridge(self) -> AgenticToolBridge:
        if (
            self.bridge is None
            or self._capabilities is None
            or not self._capabilities.execution_ready
        ):
            raise RuntimeError("Robinhood Agentic MCP capability is not verified")
        return self.bridge

    def get_account(self) -> BrokerAccountSnapshot:
        account = self._ready_bridge().get_verified_account()
        if account.account_id != self.expected_account_id:
            raise RuntimeError("dedicated Agentic account mismatch")
        return account

    def get_quote(self, symbol: str) -> BrokerQuote:
        return self._ready_bridge().get_equity_quote(symbol.upper())

    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        if request.proposed_order.account_id != self.expected_account_id:
            raise RuntimeError("dedicated Agentic account mismatch")
        return self._ready_bridge().review_and_place_equity_order(request)

    def get_order(self, broker_order_id: str) -> BrokerOrderResult:
        return self._ready_bridge().get_equity_order(broker_order_id)

    def cancel_order(self, broker_order_id: str) -> BrokerOrderResult:
        return self._ready_bridge().cancel_equity_order(broker_order_id)
