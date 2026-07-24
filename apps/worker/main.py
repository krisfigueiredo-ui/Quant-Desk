"""Worker entrypoint placeholder with fail-closed startup checks."""

from __future__ import annotations

import time

from quant_trade_desk.observability.logging import configure_logging
from quant_trade_desk.settings import Settings


def main() -> None:
    configure_logging()
    settings = Settings.from_env()
    if settings.live_equities_enabled or settings.live_crypto_enabled:
        raise SystemExit("worker refuses live flags without an offline activation record")
    while True:
        time.sleep(30)


if __name__ == "__main__":
    main()
