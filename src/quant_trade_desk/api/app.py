"""Quant Desk operations API."""

from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from quant_trade_desk.observability.logging import configure_logging
from quant_trade_desk.observability.metrics import MetricsRegistry
from quant_trade_desk.risk.kill_switch import PersistentKillSwitch
from quant_trade_desk.settings import Settings
from quant_trade_desk.storage.database import Database
from quant_trade_desk.tradingview.webhook import TradingViewVerifier

from .routes import controls, read, tradingview


def create_app(settings: Settings | None = None) -> FastAPI:
    configured = settings or Settings.from_env()
    app = FastAPI(
        title="Quant Desk Operations API",
        version="0.2.0",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.settings = configured
    app.state.database = Database(configured.database_url)
    app.state.database.create_schema()
    app.state.metrics = MetricsRegistry()
    app.state.kill_switch = PersistentKillSwitch(configured.state_dir / "hard-kill.json")
    app.state.paused = False
    app.state.incident_counter = 1
    app.state.tradingview_verifier = (
        TradingViewVerifier(
            secret=configured.tradingview_webhook_secret,
            allowed_equities=frozenset({"SPY", "QQQ"}),
            allowed_crypto=frozenset({"BTC-USD", "ETH-USD"}),
            maximum_body_bytes=configured.tradingview_max_body_bytes,
            maximum_age_seconds=configured.tradingview_max_age_seconds,
        )
        if configured.tradingview_webhook_secret
        else None
    )

    app.include_router(read.router, prefix="/api/v1", tags=["read"])
    app.include_router(controls.router, prefix="/api/v1/controls", tags=["controls"])
    app.include_router(tradingview.router, prefix="/api/v1", tags=["tradingview"])

    project_root = Path(__file__).resolve().parents[3]
    dashboard_dir = project_root / "dashboard"
    if dashboard_dir.exists():
        app.mount("/ops", StaticFiles(directory=dashboard_dir, html=True), name="ops")

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse("/ops/")

    @app.middleware("http")
    async def security_headers(request: Request, call_next: object) -> object:
        response = await call_next(request)  # type: ignore[operator]
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self'; img-src 'self' data:; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(Exception)
    async def unhandled_error(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "internal operation failed closed"},
        )

    return app


app = create_app()


def run() -> None:
    configure_logging()
    uvicorn.run("quant_trade_desk.api.app:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    run()
