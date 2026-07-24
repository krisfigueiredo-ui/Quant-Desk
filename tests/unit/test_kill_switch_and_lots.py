from __future__ import annotations

from decimal import Decimal

from quant_trade_desk.communication.schemas import (
    AssetClass,
    OrderType,
    Side,
    TimeInForce,
    TradeIntentPayload,
)
from quant_trade_desk.portfolio.allocator import PortfolioManager
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
    intent = TradeIntentPayload(
        strategy_id="equity-intraday-trend-pullback-v1",
        side=Side.SELL,
        quantity=Decimal("1"),
        order_type=OrderType.LIMIT,
        limit_price=Decimal("110"),
        time_in_force=TimeInForce.DAY,
        expected_holding_seconds=60,
        invalidation_reason="fixture exit",
        planned_loss=Decimal("0"),
        risk_reducing=True,
    )
    result = PortfolioManager(ledger).propose(
        intent,
        account_id="paper-account",
        asset_class=AssetClass.EQUITY,
        symbol="AAPL",
        strategy_lot_id=lot.lot_id,
        current_price=Decimal("110"),
        max_slippage_bps=Decimal("10"),
    )
    assert result.order is None
    assert "STRATEGY_LOT_OWNER_MISMATCH" in result.conflicts
    assert ledger.owned_quantity(lot.lot_id) == Decimal("10")
