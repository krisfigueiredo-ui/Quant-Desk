from __future__ import annotations

import base64
from decimal import Decimal

import httpx

from quant_trade_desk.execution.crypto_adapter import (
    RobinhoodCryptoAdapter,
    RobinhoodCryptoSigner,
)


def test_official_robinhood_signature_vector() -> None:
    signer = RobinhoodCryptoSigner(
        api_key="rh-api-6148effc-c0b1-486c-8940-a1d099456be6",
        private_key_b64="xQnTJVeQLmw1/Mg2YimEViSpw/SdJcgNXZ5kQkAXNPU=",
    )
    # Robinhood's published verification vector signs the Python mapping
    # representation shown in its code example.
    body = str(
        {
            "client_order_id": "131de903-5a9c-4260-abc1-28d562a5dcf0",
            "side": "buy",
            "symbol": "BTC-USD",
            "type": "market",
            "market_order_config": {"asset_quantity": "0.1"},
        }
    )
    headers = signer.headers(
        timestamp=1698708981,
        path="/api/v1/crypto/trading/orders/",
        method="POST",
        body=body,
    )
    assert headers["x-signature"] == (
        "q/nEtxp/P2Or3hph3KejBqnw5o9qeuQ+hYRnB56FaHbjDsNUY9KhB1asMxohDnzdVFSD7StaTqjSd9U9HvaRAw=="
    )


def _crypto_client() -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/accounts/"):
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "account_number": "fixture-account",
                            "status": "active",
                            "buying_power": "1000",
                        }
                    ]
                },
            )
        if request.url.path.endswith("/trading_pairs/"):
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "symbol": "BTC-USD",
                            "asset_increment": "0.00000001",
                            "quote_increment": "0.01",
                            "max_order_size": "10",
                            "min_order_amount": "1",
                            "is_api_tradable": True,
                        }
                    ]
                },
            )
        return httpx.Response(404)

    return httpx.Client(
        base_url="https://trading.robinhood.com",
        transport=httpx.MockTransport(handler),
    )


def _private_key() -> str:
    return base64.b64encode(b"\x01" * 32).decode()


def test_crypto_discovery_requires_verified_total_equity() -> None:
    adapter = RobinhoodCryptoAdapter(
        api_key="fixture-api-key",
        private_key_b64=_private_key(),
        expected_account_id="fixture-account",
        enabled=True,
        client=_crypto_client(),
    )
    capabilities = adapter.discover_capabilities()
    assert capabilities.execution_ready is False
    assert "VERIFIED_TOTAL_EQUITY_UNAVAILABLE" in capabilities.discovery_errors


def test_crypto_account_does_not_relabel_buying_power_as_equity() -> None:
    adapter = RobinhoodCryptoAdapter(
        api_key="fixture-api-key",
        private_key_b64=_private_key(),
        expected_account_id="fixture-account",
        enabled=True,
        verified_total_equity=Decimal("2500"),
        client=_crypto_client(),
    )
    assert adapter.discover_capabilities().execution_ready is True
    account = adapter.get_account()
    assert account.equity == Decimal("2500")
    assert account.buying_power == Decimal("1000")
