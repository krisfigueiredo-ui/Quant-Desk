from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from quant_trade_desk.api.app import create_app
from quant_trade_desk.settings import Settings
from quant_trade_desk.tradingview.webhook import TradingViewVerifier


def _client(tmp_path: Path) -> TestClient:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        state_dir=tmp_path / "state",
        api_token="fixture-operator-token-that-is-long",
        tradingview_webhook_secret="fixture-webhook-secret-that-is-long",
    )
    return TestClient(create_app(settings))


def test_read_routes_are_labeled_synthetic(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        response = client.get("/api/v1/overview")
        assert response.status_code == 200
        assert response.json()["is_synthetic"] is True
        assert response.json()["operating_mode"] == "PAPER"


def test_dashboard_has_no_live_activation_route(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        response = client.post(
            "/api/v1/controls/activate-live",
            headers={"Authorization": "Bearer fixture-operator-token-that-is-long"},
            json={"confirmation_phrase": "anything", "reason": "test"},
        )
        assert response.status_code == 404


def test_control_requires_auth_and_exact_phrase(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        unauthorized = client.post(
            "/api/v1/controls/pause",
            json={"confirmation_phrase": "PAUSE NEW TRADES", "reason": "test"},
        )
        assert unauthorized.status_code == 401
        wrong = client.post(
            "/api/v1/controls/pause",
            headers={"Authorization": "Bearer fixture-operator-token-that-is-long"},
            json={"confirmation_phrase": "pause", "reason": "test"},
        )
        assert wrong.status_code == 400
        accepted = client.post(
            "/api/v1/controls/pause",
            headers={"Authorization": "Bearer fixture-operator-token-that-is-long"},
            json={"confirmation_phrase": "PAUSE NEW TRADES", "reason": "operator test"},
        )
        assert accepted.status_code == 200
        assert accepted.json()["new_entries_blocked"] is True
        assert accepted.json()["audit_event_id"]


def test_emergency_stop_is_authenticated_audited_and_persistent(
    tmp_path: Path,
) -> None:
    with _client(tmp_path) as client:
        response = client.post(
            "/api/v1/controls/emergency-stop",
            headers={"Authorization": "Bearer fixture-operator-token-that-is-long"},
            json={
                "confirmation_phrase": "EMERGENCY STOP",
                "reason": "deterministic integration test",
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "KILLED"
        assert response.json()["audit_recorded"] is True
        assert client.get("/api/v1/health").json()["kill_switch"]["killed"] is True


def _tradingview_body(
    observed_at: datetime,
    *,
    signal_id: str | None = None,
    symbol: str = "SPY",
) -> bytes:
    return json.dumps(
        {
            "schema_version": "1.0.0",
            "signal_id": signal_id or str(uuid4()),
            "strategy_id": "equity-intraday-trend-pullback-v1",
            "asset_class": "EQUITY",
            "symbol": symbol,
            "side": "BUY",
            "timeframe": "5m",
            "signal_timestamp": observed_at.isoformat(),
            "expires_at": (observed_at + timedelta(minutes=2)).isoformat(),
            "indicator_values": {"momentum": 0.8},
        },
        separators=(",", ":"),
    ).encode()


def test_tradingview_endpoint_accepts_review_only_and_rejects_unsafe_inputs(
    tmp_path: Path,
) -> None:
    secret = "fixture-webhook-secret-that-is-long"
    signer = TradingViewVerifier(
        secret=secret,
        allowed_equities=frozenset({"SPY", "QQQ"}),
        allowed_crypto=frozenset({"BTC-USD", "ETH-USD"}),
    )
    now = datetime.now(UTC)
    body = _tradingview_body(now)
    headers = {"X-Quant-Desk-Signature": signer.sign(body)}
    with _client(tmp_path) as client:
        accepted = client.post("/api/v1/tradingview/webhook", content=body, headers=headers)
        assert accepted.status_code == 200
        assert accepted.json()["direct_execution"] is False

        duplicate = client.post("/api/v1/tradingview/webhook", content=body, headers=headers)
        assert duplicate.status_code == 400
        assert duplicate.json()["detail"] == "DUPLICATE_OR_REPLAYED_SIGNAL"

        invalid = client.post(
            "/api/v1/tradingview/webhook",
            content=_tradingview_body(now),
            headers={"X-Quant-Desk-Signature": "invalid"},
        )
        assert invalid.status_code == 400
        assert invalid.json()["detail"] == "INVALID_SIGNATURE"

        stale_body = _tradingview_body(now - timedelta(minutes=5))
        stale = client.post(
            "/api/v1/tradingview/webhook",
            content=stale_body,
            headers={"X-Quant-Desk-Signature": signer.sign(stale_body)},
        )
        assert stale.status_code == 400
        assert stale.json()["detail"] == "STALE_SIGNAL"

        unsupported_body = _tradingview_body(now, symbol="UNSUPPORTED")
        unsupported = client.post(
            "/api/v1/tradingview/webhook",
            content=unsupported_body,
            headers={"X-Quant-Desk-Signature": signer.sign(unsupported_body)},
        )
        assert unsupported.status_code == 400
        assert unsupported.json()["detail"] == "UNSUPPORTED_SYMBOL"
