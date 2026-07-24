#!/usr/bin/env python3
"""Offline-capable deterministic emergency stop; no LLM required."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from quant_trade_desk.risk.kill_switch import PersistentKillSwitch


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", default=".quant-desk-state")
    parser.add_argument("--incident-id", required=True)
    parser.add_argument("--confirmation", required=True)
    args = parser.parse_args()
    if args.confirmation != "EMERGENCY STOP":
        raise SystemExit("Exact confirmation phrase required: EMERGENCY STOP")
    path = Path(args.state_dir).resolve() / "hard-kill.json"
    state = PersistentKillSwitch(path).activate(
        "OFFLINE_EMERGENCY_STOP",
        args.incident_id,
    )
    os.write(
        1,
        f"Hard kill persisted at {path}; incident {state.incident_id}\n".encode(),
    )


if __name__ == "__main__":
    main()
