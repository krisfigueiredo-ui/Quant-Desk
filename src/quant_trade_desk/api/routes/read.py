"""Read-only operations routes."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, StreamingResponse

from quant_trade_desk.api.fixtures import (
    agents_fixture,
    messages_fixture,
    orders_fixture,
    overview_fixture,
    risk_fixture,
    scanner_fixture,
    strategies_fixture,
)

router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    kill = request.app.state.kill_switch.read()
    return {
        "status": "HEALTHY",
        "mode": request.app.state.settings.trading_mode.value,
        "kill_switch": kill.model_dump(mode="json"),
        "live_equities_enabled": False,
        "live_crypto_enabled": False,
        "autonomous_execution_enabled": False,
    }


@router.get("/ready")
def ready(request: Request) -> dict[str, object]:
    kill = request.app.state.kill_switch.read()
    database_ok = request.app.state.database.ping()
    return {
        "ready": database_ok and not kill.killed,
        "ready_for_new_exposure": database_ok and not kill.killed,
        "database": database_ok,
        "queue": True,
        "audit": database_ok,
        "broker": "PAPER_ONLY",
        "time_synchronized": True,
    }


@router.get("/overview")
def overview() -> dict[str, object]:
    return overview_fixture()


@router.get("/agents")
def agents() -> list[dict[str, object]]:
    return agents_fixture()


@router.get("/messages")
def messages() -> list[dict[str, object]]:
    return messages_fixture()


@router.get("/scanner")
def scanner() -> list[dict[str, object]]:
    return scanner_fixture()


@router.get("/strategies")
def strategies() -> list[dict[str, object]]:
    return strategies_fixture()


@router.get("/risk")
def risk() -> dict[str, object]:
    return risk_fixture()


@router.get("/orders")
def orders() -> list[dict[str, object]]:
    return orders_fixture()


@router.get("/settings")
def settings(request: Request) -> dict[str, object]:
    configured = request.app.state.settings
    return {
        "trading_mode": configured.trading_mode.value,
        "live_equities_enabled": configured.live_equities_enabled,
        "live_crypto_enabled": configured.live_crypto_enabled,
        "autonomous_execution_enabled": configured.autonomous_execution_enabled,
        "database": "CONNECTED" if request.app.state.database.ping() else "UNAVAILABLE",
        "queue": "IN_MEMORY_DEVELOPMENT",
        "equity_broker": "NOT_AUTHENTICATED",
        "crypto_broker": "NOT_AUTHENTICATED",
        "tradingview": (
            "SIGNED_INPUT_READY" if configured.tradingview_webhook_secret else "NOT_CONFIGURED"
        ),
        "secret_manager": "ENVIRONMENT_COMPATIBLE",
        "activation_via_dashboard": False,
    }


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(request: Request) -> str:
    return str(request.app.state.metrics.render())


async def _events() -> AsyncIterator[str]:
    while True:
        payload = json.dumps({"type": "heartbeat", "data_mode": "SYNTHETIC_FIXTURE"})
        yield f"event: heartbeat\ndata: {payload}\n\n"
        await asyncio.sleep(10)


@router.get("/events")
def events() -> StreamingResponse:
    return StreamingResponse(
        _events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
