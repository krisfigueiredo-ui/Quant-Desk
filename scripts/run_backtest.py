#!/usr/bin/env python3
"""Evaluate an explicitly supplied return dataset; never fetch or fabricate data."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from quant_trade_desk.strategies.validation import (
    CostAssumptions,
    ReturnObservation,
    validate_strategy,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--strategy-id", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cost-bps", type=float, default=12)
    args = parser.parse_args()
    if not args.input.is_file():
        raise SystemExit("Input CSV is required; Quant Desk will not fabricate backtest data.")
    with args.input.open(newline="", encoding="utf-8") as handle:
        rows = [ReturnObservation.model_validate(row) for row in csv.DictReader(handle)]
    result = validate_strategy(
        args.strategy_id,
        rows,
        CostAssumptions(
            commissions_bps=0,
            spread_bps=0,
            slippage_bps=args.cost_bps,
            latency_bps=0,
        ),
    )
    rendered = result.model_dump_json(indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
