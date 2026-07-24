#!/usr/bin/env python3
"""Offline, interactive restricted-live readiness record creation.

This command is intentionally not imported by the API or dashboard. Running it
does not start workers, submit orders, or enable STANDARD_LIVE.
"""

from __future__ import annotations

import argparse
import getpass
from pathlib import Path

from quant_trade_desk.communication.schemas import AssetClass
from quant_trade_desk.risk.operating_mode import (
    CRYPTO_CONFIRMATION,
    EQUITY_CONFIRMATION,
    OfflineActivationManager,
    ReadinessChecklist,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-class", choices=("equity", "crypto"), required=True)
    parser.add_argument("--checklist", type=Path, required=True)
    args = parser.parse_args()
    asset_class = AssetClass.EQUITY if args.asset_class == "equity" else AssetClass.CRYPTO
    expected = EQUITY_CONFIRMATION if asset_class == AssetClass.EQUITY else CRYPTO_CONFIRMATION
    checklist = ReadinessChecklist.model_validate_json(args.checklist.read_text(encoding="utf-8"))
    if not checklist.ready:
        raise SystemExit("Readiness checklist is incomplete; no record was created.")
    account_id = getpass.getpass("Verified dedicated account ID (stored only as a hash): ")
    phrase = input(f'Type exactly "{expected}": ')
    record_name = f"{args.asset_class}-live-activation.json"
    manager = OfflineActivationManager(Path(".quant-desk-state") / record_name)
    record = manager.create_record(
        asset_class=asset_class,
        exact_phrase=phrase,
        checklist=checklist,
        dedicated_account_id=account_id,
    )
    print(
        f"Created local {args.asset_class} readiness record {record.record_id}. "
        "No trading process was started."
    )


if __name__ == "__main__":
    main()
