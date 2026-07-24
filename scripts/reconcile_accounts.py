#!/usr/bin/env python3
"""Account reconciliation entrypoint that refuses an unverified adapter."""

from quant_trade_desk.settings import Settings


def main() -> None:
    settings = Settings.from_env()
    if not (
        settings.robinhood_agentic_expected_account_id
        or settings.robinhood_crypto_expected_account_id
    ):
        raise SystemExit(
            "No dedicated account identity is configured; reconciliation failed closed."
        )
    raise SystemExit(
        "Authenticated capability discovery and human verification are required "
        "before account reconciliation."
    )


if __name__ == "__main__":
    main()
