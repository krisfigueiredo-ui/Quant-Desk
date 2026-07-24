"""Strict, conservative application settings."""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TradingMode(StrEnum):
    BACKTEST = "BACKTEST"
    PAPER = "PAPER"
    SHADOW = "SHADOW"
    RESTRICTED_LIVE = "RESTRICTED_LIVE"
    STANDARD_LIVE = "STANDARD_LIVE"
    PAUSED = "PAUSED"
    CAPITAL_PRESERVATION = "CAPITAL_PRESERVATION"
    KILLED = "KILLED"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


class Settings(BaseModel):
    """Runtime settings that reject unsafe combinations at startup."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    trading_mode: TradingMode = TradingMode.PAPER
    live_equities_enabled: bool = False
    live_crypto_enabled: bool = False
    autonomous_execution_enabled: bool = False
    database_url: str = "sqlite:///./quant_desk.db"
    redis_url: str | None = None
    api_token: str | None = None
    tradingview_webhook_secret: str | None = None
    tradingview_max_body_bytes: int = Field(default=32_768, ge=1_024, le=1_048_576)
    tradingview_max_age_seconds: int = Field(default=60, ge=5, le=600)
    state_dir: Path = Path(".quant-desk-state")
    robinhood_agentic_expected_account_id: str | None = None
    robinhood_agentic_bridge_url: str | None = None
    robinhood_crypto_api_key: str | None = None
    robinhood_crypto_private_key_b64: str | None = None
    robinhood_crypto_expected_account_id: str | None = None

    @field_validator(
        "api_token",
        "tradingview_webhook_secret",
        "robinhood_agentic_expected_account_id",
        "robinhood_agentic_bridge_url",
        "robinhood_crypto_api_key",
        "robinhood_crypto_private_key_b64",
        "robinhood_crypto_expected_account_id",
        mode="before",
    )
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def reject_unsafe_combinations(self) -> Settings:
        live_mode = self.trading_mode in {
            TradingMode.RESTRICTED_LIVE,
            TradingMode.STANDARD_LIVE,
        }
        if not live_mode and (self.live_equities_enabled or self.live_crypto_enabled):
            raise ValueError("live asset flags require a live operating mode")
        if live_mode and not (self.live_equities_enabled or self.live_crypto_enabled):
            raise ValueError("live mode requires at least one separately enabled asset class")
        if self.trading_mode == TradingMode.STANDARD_LIVE:
            raise ValueError("STANDARD_LIVE cannot be enabled through environment configuration")
        if self.autonomous_execution_enabled and not live_mode:
            raise ValueError("autonomous execution requires restricted live mode")
        return self

    @classmethod
    def from_env(cls) -> Settings:
        mode_raw = os.getenv("TRADING_MODE", TradingMode.PAPER.value).strip().upper()
        return cls(
            trading_mode=TradingMode(mode_raw),
            live_equities_enabled=_env_bool("LIVE_EQUITIES_ENABLED"),
            live_crypto_enabled=_env_bool("LIVE_CRYPTO_ENABLED"),
            autonomous_execution_enabled=_env_bool("AUTONOMOUS_EXECUTION_ENABLED"),
            database_url=os.getenv("QUANT_DESK_DATABASE_URL", "sqlite:///./quant_desk.db"),
            redis_url=os.getenv("QUANT_DESK_REDIS_URL") or None,
            api_token=os.getenv("QUANT_DESK_API_TOKEN") or None,
            tradingview_webhook_secret=os.getenv("TRADINGVIEW_WEBHOOK_SECRET") or None,
            tradingview_max_body_bytes=int(os.getenv("TRADINGVIEW_MAX_BODY_BYTES", "32768")),
            tradingview_max_age_seconds=int(os.getenv("TRADINGVIEW_MAX_AGE_SECONDS", "60")),
            state_dir=Path(os.getenv("QUANT_DESK_STATE_DIR", ".quant-desk-state")),
            robinhood_agentic_expected_account_id=os.getenv(
                "ROBINHOOD_AGENTIC_EXPECTED_ACCOUNT_ID"
            ),
            robinhood_agentic_bridge_url=os.getenv("ROBINHOOD_AGENTIC_BRIDGE_URL"),
            robinhood_crypto_api_key=os.getenv("ROBINHOOD_CRYPTO_API_KEY"),
            robinhood_crypto_private_key_b64=os.getenv("ROBINHOOD_CRYPTO_PRIVATE_KEY_B64"),
            robinhood_crypto_expected_account_id=os.getenv("ROBINHOOD_CRYPTO_EXPECTED_ACCOUNT_ID"),
        )
