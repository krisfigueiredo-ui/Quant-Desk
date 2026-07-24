from __future__ import annotations

import json
from datetime import timedelta
from uuid import uuid4

import pytest

from quant_trade_desk.tradingview.webhook import TradingViewVerifier


def _body(now: object, symbol: str = "SPY") -> bytes:
    from datetime import datetime

    assert isinstance(now, datetime)
    return json.dumps(
        {
            "schema_version": "1.0.0",
            "signal_id": str(uuid4()),
            "strategy_id": "equity-intraday-trend-pullback-v1",
            "asset_class": "EQUITY",
            "symbol": symbol,
            "side": "BUY",
            "timeframe": "5m",
            "signal_timestamp": now.isoformat(),
            "expires_at": (now + timedelta(minutes=1)).isoformat(),
            "indicator_values": {"momentum": 0.8},
        },
        separators=(",", ":"),
    ).encode()


def _verifier() -> TradingViewVerifier:
    return TradingViewVerifier(
        secret="fixture-secret-at-least-16-chars",
        allowed_equities=frozenset({"SPY"}),
        allowed_crypto=frozenset({"BTC-USD", "ETH-USD"}),
    )


def test_valid_signal_is_accepted_for_review(now: object) -> None:
    verifier = _verifier()
    body = _body(now)
    signal = verifier.verify(
        body=body,
        signature=verifier.sign(body),
        source_key="fixture",
        now=now,  # type: ignore[arg-type]
    )
    assert signal.symbol == "SPY"


def test_invalid_signature_is_rejected(now: object) -> None:
    with pytest.raises(ValueError, match="INVALID_SIGNATURE"):
        _verifier().verify(
            body=_body(now),
            signature="invalid",
            source_key="fixture",
            now=now,  # type: ignore[arg-type]
        )


def test_replay_is_rejected(now: object) -> None:
    verifier = _verifier()
    body = _body(now)
    signature = verifier.sign(body)
    verifier.verify(body=body, signature=signature, source_key="fixture", now=now)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="DUPLICATE_OR_REPLAYED"):
        verifier.verify(
            body=body,
            signature=signature,
            source_key="fixture",
            now=now,  # type: ignore[arg-type]
        )


def test_unsupported_symbol_is_rejected(now: object) -> None:
    verifier = _verifier()
    body = _body(now, "UNSUPPORTED")
    with pytest.raises(ValueError, match="UNSUPPORTED_SYMBOL"):
        verifier.verify(
            body=body,
            signature=verifier.sign(body),
            source_key="fixture",
            now=now,  # type: ignore[arg-type]
        )
