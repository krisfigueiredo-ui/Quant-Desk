from __future__ import annotations

from decimal import Decimal

import pytest

from quant_trade_desk.communication.schemas import AssetClass
from quant_trade_desk.portfolio.strategy_lots import StrategyLot, StrategyLotLedger
from quant_trade_desk.risk.kill_switch import PersistentKillSwitch


def test_hard_kill_persists_across_restart(tmp_path: object) -> None:
    from pathlib import Path

    assert isinstance(tmp_path, Path)
    path = tmp_path / "state" / "hard-kill.json"
    first = PersistentKillSwitch(path)
    first.activate("DRAWDOWN_37_HARD_KILL", "incident-1")
    restarted = PersistentKillSwitch(path)
    assert restarted.read().killed
    assert restarted.read().reason_code == "DRAWDOWN_37_HARD_KILL"


def test_day_strategy_cannot_close_long_term_lot() -> None:
    ledger = StrategyLotLedger()
    lot = StrategyLot(
        strategy_id="long-term",
        asset_class=AssetClass.EQUITY,
        symbol="AAPL",
        quantity=Decimal("10"),
        average_cost=Decimal("100"),
    )
    ledger.add(lot)
    with pytest.raises(ValueError, match="exceeds strategy-owned"):
        ledger.apply_fill(
            lot.lot_id,
            side="SELL",
            quantity=Decimal("11"),
            price=Decimal("110"),
        )
    assert ledger.owned_quantity(lot.lot_id) == Decimal("10")
