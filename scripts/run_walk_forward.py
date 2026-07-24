#!/usr/bin/env python3
"""Validate a supplied sequence of independent walk-forward result files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", nargs="+", type=Path)
    args = parser.parse_args()
    if len(args.results) < 3:
        raise SystemExit(
            "At least three independently generated walk-forward windows are required."
        )
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in args.results]
    if any(payload.get("automatic_promotion_permitted") is not False for payload in payloads):
        raise SystemExit("Invalid result: automatic promotion must remain disabled.")
    print(
        json.dumps(
            {
                "windows_reviewed": len(payloads),
                "status": "MANUAL_REVIEW_REQUIRED",
                "automatic_promotion_permitted": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
