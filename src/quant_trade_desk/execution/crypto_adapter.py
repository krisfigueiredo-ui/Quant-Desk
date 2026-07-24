"""Official Robinhood Crypto Trading API v2 adapter.

The adapter is disabled by default and uses only documented endpoints and
Ed25519 request signing. It performs no browser automation and stores no
credentials.
"""

from __future__ import annotations

import base64
import json
import time
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlencode

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import BaseModel, ConfigDict, Field

from quant_trade_desk.communication.schemas import (
    AssetClass,
    OrderType,
    Side,
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

BASE_URL = "https://trading.robinhood.com"


class CryptoPairRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    asset_increment: Decimal = Field(gt=0)
    quote_increment: Decimal = Field(gt=0)
    max_order_size: Decimal = Field(gt=0)
    min_order_amount: Decimal = Field(gt=0)
    is_api_tradable: bool

    def valid_quantity(self, quantity: Decimal) -> bool:
        if quantity <= 0 or quantity > self.max_order_size:
            return False
        try:
            return quantity % self.asset_increment == 0
        except InvalidOperation:
            return False


class RobinhoodCryptoSigner:
    def __init__(self, api_key: str, private_key_b64: str) -> None:
        raw = base64.b64decode(private_key_b64, validate=True)
        if len(raw) != 32:
            raise ValueError("Ed25519 private key must decode to 32 bytes")
        self.api_key = api_key
        self._private_key = Ed25519PrivateKey.from_private_bytes(raw)

    def headers(
        self,
        *,
        timestamp: int,
        path: str,
        method: str,
        body: str = "",
    ) -> dict[str, str]:
        message = f"{self.api_key}{timestamp}{path}{method.upper()}{body}"
        signature = self._private_key.sign(message.encode("utf-8"))
        return {
            "x-api-key": self.api_key,
            "x-timestamp": str(timestamp),
            "x-signature": base64.b64encode(signature).decode("ascii"),
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": "Quant-Desk/0.2 official-robinhood-crypto-api",
        }


class RobinhoodCryptoAdapter:
    adapter_id = "robinhood-crypto-v2"

    def __init__(
        self,
        *,
        api_key: str,
        private_key_b64: str,
        expected_account_id: str,
        allowlist: frozenset[str] = frozenset({"BTC-USD", "ETH-USD"}),
        enabled: bool = False,
        clock_skew_seconds: float = 0,
        verified_total_equity: Decimal | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.signer = RobinhoodCryptoSigner(api_key, private_key_b64)
        self.expected_account_id = expected_account_id
        self.allowlist = frozenset(symbol.upper() for symbol in allowlist)
        self.enabled = enabled
        self.clock_skew_seconds = clock_skew_seconds
        self.verified_total_equity = verified_total_equity
        self.client = client or httpx.Client(
            base_url=BASE_URL,
            timeout=httpx.Timeout(10),
            follow_redirects=False,
        )
        self._rules: dict[str, CryptoPairRule] = {}
        self._capabilities: BrokerCapabilities | None = None

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: list[tuple[str, str]] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        query = urlencode(params or [], doseq=True)
        signed_path = f"{path}?{query}" if query else path
        body = (
            json.dumps(payload, separators=(",", ":"), sort_keys=True)
            if payload is not None
            else ""
        )
        timestamp = int(time.time())
        headers = self.signer.headers(
            timestamp=timestamp,
            path=signed_path,
            method=method,
            body=body,
        )
        response = self.client.request(
            method,
            signed_path,
            content=body.encode() if body else None,
            headers=headers,
        )
        response.raise_for_status()
        if not response.content:
            return {}
        parsed = response.json()
        if not isinstance(parsed, dict):
            raise RuntimeError("unexpected Robinhood Crypto response")
        return parsed

    def discover_capabilities(self) -> BrokerCapabilities:
        errors: list[str] = []
        if not self.enabled:
            errors.append("ADAPTER_DISABLED")
        if abs(self.clock_skew_seconds) > 5:
            errors.append("CLOCK_NOT_SYNCHRONIZED")
        if self.verified_total_equity is None or self.verified_total_equity <= 0:
            errors.append("VERIFIED_TOTAL_EQUITY_UNAVAILABLE")
        account_id: str | None = None
        try:
            accounts = self._request("GET", "/api/v2/crypto/trading/accounts/")
            for account in accounts.get("results", []):
                if account.get("account_number") == self.expected_account_id:
                    account_id = self.expected_account_id
                    if account.get("status") != "active":
                        errors.append("ACCOUNT_NOT_ACTIVE")
                    break
            if account_id is None:
                errors.append("DEDICATED_ACCOUNT_MISMATCH")
            pairs = self._request("GET", "/api/v2/crypto/trading/trading_pairs/")
            self._rules = {}
            for row in pairs.get("results", []):
                symbol = str(row.get("symbol", "")).upper()
                if symbol not in self.allowlist or not row.get("is_api_tradable"):
                    continue
                self._rules[symbol] = CryptoPairRule(
                    symbol=symbol,
                    asset_increment=Decimal(str(row["asset_increment"])),
                    quote_increment=Decimal(str(row["quote_increment"])),
                    max_order_size=Decimal(str(row["max_order_size"])),
                    min_order_amount=Decimal(str(row["min_order_amount"])),
                    is_api_tradable=True,
                )
            if not self._rules:
                errors.append("NO_ALLOWLISTED_TRADABLE_PAIRS")
        except Exception as exc:
            errors.append(f"CAPABILITY_DISCOVERY_FAILED:{type(exc).__name__}")
        self._capabilities = BrokerCapabilities(
            adapter_id=self.adapter_id,
            discovered_at=datetime.now(UTC),
            authenticated=not any("DISCOVERY_FAILED" in error for error in errors),
            dedicated_account_verified=account_id == self.expected_account_id,
            account_id=account_id,
            asset_classes=(frozenset({AssetClass.CRYPTO}) if not errors else frozenset()),
            symbols=frozenset(self._rules),
            order_types=(frozenset({OrderType.LIMIT}) if not errors else frozenset()),
            time_in_force=(frozenset({TimeInForce.GTC}) if not errors else frozenset()),
            fractional_support=True,
            trading_sessions=frozenset({"CRYPTO_24_7"}),
            cancellation_support=True,
            position_visibility=True,
            account_visibility=True,
            discovery_errors=tuple(errors),
        )
        return self._capabilities

    def _require_ready(self) -> None:
        if self._capabilities is None or not self._capabilities.execution_ready:
            raise RuntimeError("Robinhood Crypto capability is not verified")

    def get_account(self) -> BrokerAccountSnapshot:
        self._require_ready()
        if self.verified_total_equity is None:
            raise RuntimeError("verified total account equity is unavailable")
        payload = self._request("GET", "/api/v2/crypto/trading/accounts/")
        for account in payload.get("results", []):
            if account.get("account_number") == self.expected_account_id:
                return BrokerAccountSnapshot(
                    account_id=self.expected_account_id,
                    verified_at=datetime.now(UTC),
                    equity=self.verified_total_equity,
                    buying_power=Decimal(str(account.get("buying_power", "0"))),
                )
        raise RuntimeError("dedicated crypto account mismatch")

    def get_quote(self, symbol: str) -> BrokerQuote:
        self._require_ready()
        normalized = symbol.upper()
        if normalized not in self._rules:
            raise RuntimeError("unsupported crypto symbol")
        payload = self._request(
            "GET",
            "/api/v2/crypto/marketdata/best_bid_ask/",
            params=[("symbol", normalized)],
        )
        for quote in payload.get("results", []):
            if str(quote.get("symbol", "")).upper() == normalized:
                return BrokerQuote(
                    symbol=normalized,
                    timestamp=datetime.now(UTC),
                    bid=Decimal(str(quote["bid"])),
                    ask=Decimal(str(quote["ask"])),
                )
        raise RuntimeError("crypto quote unavailable")

    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        self._require_ready()
        order = request.proposed_order
        if order.account_id != self.expected_account_id:
            raise RuntimeError("dedicated crypto account mismatch")
        if order.order_type != OrderType.LIMIT or order.limit_price is None:
            raise RuntimeError("restricted crypto adapter accepts limit orders only")
        if order.time_in_force != TimeInForce.GTC:
            raise RuntimeError("restricted crypto limit orders require GTC")
        symbol = self._symbol_from_client_order_id(request.client_order_id)
        rule = self._rules.get(symbol)
        if rule is None:
            raise RuntimeError("unsupported crypto symbol")
        if not rule.valid_quantity(order.quantity):
            raise RuntimeError("crypto quantity violates venue precision or size")
        if order.quantity * order.limit_price < rule.min_order_amount:
            raise RuntimeError("crypto order below minimum amount")
        payload = {
            "symbol": symbol,
            "client_order_id": request.client_order_id,
            "side": "buy" if order.side == Side.BUY else "sell",
            "type": "limit",
            "limit_order_config": {
                "asset_quantity": str(order.quantity),
                "limit_price": str(order.limit_price),
                "time_in_force": "gtc",
            },
        }
        response = self._request(
            "POST",
            "/api/v2/crypto/trading/orders/",
            params=[("account_number", self.expected_account_id)],
            payload=payload,
        )
        return self._result_from_order(response, request.client_order_id)

    @staticmethod
    def _symbol_from_client_order_id(client_order_id: str) -> str:
        """Client IDs are `<SYMBOL>:<uuid>` inside this adapter contract."""
        symbol, separator, _ = client_order_id.partition(":")
        if not separator:
            raise RuntimeError("crypto client order id lacks symbol binding")
        return symbol.upper()

    def _result_from_order(
        self,
        payload: dict[str, Any],
        client_order_id: str,
    ) -> BrokerOrderResult:
        state = str(payload.get("state", "unknown")).lower()
        mapped = {
            "pending": BrokerOrderState.PENDING,
            "open": BrokerOrderState.ACCEPTED,
            "filled": BrokerOrderState.FILLED,
            "partially_filled": BrokerOrderState.PARTIALLY_FILLED,
            "canceled": BrokerOrderState.CANCELED,
            "failed": BrokerOrderState.REJECTED,
        }.get(state, BrokerOrderState.UNKNOWN)
        return BrokerOrderResult(
            adapter_id=self.adapter_id,
            client_order_id=client_order_id,
            broker_order_id=payload.get("id"),
            state=mapped,
            accepted_quantity=Decimal(
                str(payload.get("limit_order_config", {}).get("asset_quantity", "0"))
            ),
            filled_quantity=Decimal(str(payload.get("filled_asset_quantity", "0"))),
            average_fill_price=(
                Decimal(str(payload["average_price"]))
                if payload.get("average_price") is not None
                else None
            ),
            reason_code=f"BROKER_STATE_{state.upper()}",
            raw_status=state,
        )

    def get_order(self, broker_order_id: str) -> BrokerOrderResult:
        self._require_ready()
        payload = self._request(
            "GET",
            f"/api/v2/crypto/trading/orders/{broker_order_id}/",
            params=[("account_number", self.expected_account_id)],
        )
        return self._result_from_order(payload, str(payload.get("client_order_id", "unknown")))

    def cancel_order(self, broker_order_id: str) -> BrokerOrderResult:
        self._require_ready()
        payload = self._request(
            "POST",
            f"/api/v2/crypto/trading/orders/{broker_order_id}/cancel/",
        )
        return self._result_from_order(payload, str(payload.get("client_order_id", "unknown")))
