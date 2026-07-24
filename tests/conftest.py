from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from quant_trade_desk.communication.schemas import (
    AssetClass,
    OrderType,
    ProposedOrderPayload,
    Side,
    TimeInForce,
)
from quant_trade_desk.data.quality import MarketSnapshot
from quant_trade_desk.risk.drawdown import calculate_drawdown
from quant_trade_desk.risk.engine import (
    AccountState,
    DependencyHealth,
    RiskContext,
)
from quant_trade_desk.risk.kill_switch import KillSwitchState
from quant_trade_desk.risk.operating_mode import authorize_mode
from quant_trade_desk.settings import Settings


@pytest.fixture
def now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


@pytest.fixture
def proposed_order() -> ProposedOrderPayload:
    from uuid import uuid4

    return ProposedOrderPayload(
        account_id="paper-account",
        side=Side.BUY,
        quantity=Decimal("1"),
        order_type=OrderType.LIMIT,
        limit_price=Decimal("100"),
        time_in_force=TimeInForce.DAY,
        strategy_lot_id=uuid4(),
        max_slippage_bps=Decimal("10"),
    )


@pytest.fixture
def risk_context(now: datetime) -> RiskContext:
    return RiskContext(
        now=now,
        expected_account_id="paper-account",
        account=AccountState(
            account_id="paper-account",
            verified_at=now,
            equity=Decimal("100000"),
            buying_power=Decimal("90000"),
            cash=Decimal("90000"),
            gross_exposure=Decimal("10000"),
            equity_exposure=Decimal("10000"),
            crypto_exposure=Decimal("0"),
            daily_pnl=Decimal("0"),
            weekly_pnl=Decimal("0"),
            open_orders=0,
            live_orders_today=0,
            equity_day_trades_today=0,
            crypto_trades_24h=0,
        ),
        market=MarketSnapshot(
            asset_class=AssetClass.EQUITY,
            symbol="SPY",
            timestamp=now,
            last=Decimal("100"),
            bid=Decimal("99.95"),
            ask=Decimal("100.05"),
            volume=Decimal("1000000"),
            average_dollar_volume=Decimal("100000000"),
            source_id="fixture-market-data",
        ),
        mode_authorization=authorize_mode(Settings()),
        kill_switch=KillSwitchState(),
        drawdown=calculate_drawdown(
            verified_current_equity=Decimal("100000"),
            verified_peak_equity=Decimal("100000"),
        ),
        dependencies=DependencyHealth(),
        allowed_equities=frozenset({"SPY"}),
        allowed_crypto=frozenset({"BTC-USD", "ETH-USD"}),
        strategy_authorized=True,
        strategy_allocation=Decimal("0"),
        sector_exposure=Decimal("0"),
        correlated_exposure=Decimal("0.10"),
        existing_symbol_exposure=Decimal("0"),
        strategy_owned_quantity=Decimal("10"),
        signal_created_at=now - timedelta(seconds=1),
        equity_minutes_since_open=30,
    )
