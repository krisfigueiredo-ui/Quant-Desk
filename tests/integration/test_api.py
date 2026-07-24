from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from quant_trade_desk.api.app import create_app
from quant_trade_desk.settings import Settings


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
