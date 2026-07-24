#!/usr/bin/env python3
"""CI guard proving development and tracked example defaults remain non-live."""

from __future__ import annotations

import re
from pathlib import Path

from quant_trade_desk.settings import Settings, TradingMode


def main() -> None:
    settings = Settings()
    assert settings.trading_mode == TradingMode.PAPER
    assert not settings.live_equities_enabled
    assert not settings.live_crypto_enabled
    assert not settings.autonomous_execution_enabled

    example = Path(".env.example").read_text(encoding="utf-8")
    expected = {
        "TRADING_MODE": "PAPER",
        "LIVE_EQUITIES_ENABLED": "false",
        "LIVE_CRYPTO_ENABLED": "false",
        "AUTONOMOUS_EXECUTION_ENABLED": "false",
    }
    for key, value in expected.items():
        if not re.search(rf"^{key}={value}$", example, re.MULTILINE):
            raise SystemExit(f"unsafe or missing default: {key}")
    print("Verified: live equity, live crypto, and autonomous execution are disabled.")


if __name__ == "__main__":
    main()
