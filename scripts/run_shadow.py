#!/usr/bin/env python3
"""Verify a no-submission shadow configuration."""

from quant_trade_desk.settings import Settings, TradingMode


def main() -> None:
    settings = Settings.from_env()
    if settings.trading_mode != TradingMode.SHADOW:
        raise SystemExit("TRADING_MODE must be SHADOW")
    if (
        settings.live_equities_enabled
        or settings.live_crypto_enabled
        or settings.autonomous_execution_enabled
    ):
        raise SystemExit("shadow runner refuses live or autonomous flags")
    print("Shadow mode verified. Broker submissions remain prohibited.")


if __name__ == "__main__":
    main()
