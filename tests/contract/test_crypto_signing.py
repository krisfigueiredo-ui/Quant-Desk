from __future__ import annotations

from quant_trade_desk.execution.crypto_adapter import RobinhoodCryptoSigner


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
