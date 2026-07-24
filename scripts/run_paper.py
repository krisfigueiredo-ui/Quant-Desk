#!/usr/bin/env python3
"""Verify the multi-agent desk is configured for paper operation."""

from quant_trade_desk.settings import Settings, TradingMode


def main() -> None:
    settings = Settings.from_env()
    if settings.trading_mode != TradingMode.PAPER:
        raise SystemExit("TRADING_MODE must be PAPER")
    if (
        settings.live_equities_enabled
        or settings.live_crypto_enabled
        or settings.autonomous_execution_enabled
    ):
        raise SystemExit("paper runner refuses live or autonomous flags")
    print("Paper mode verified. Start the API and worker in separate local processes.")


if __name__ == "__main__":
    main()
