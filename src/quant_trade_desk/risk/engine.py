"""Final deterministic, non-bypassable pre-execution risk authority."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from quant_trade_desk.communication.permissions import Permission, require
from quant_trade_desk.communication.schemas import (
    AssetClass,
    ProposedOrderPayload,
    RiskDecisionPayload,
    RiskOutcome,
    Side,
    TradingHorizon,
)
from quant_trade_desk.data.quality import MarketSnapshot
from quant_trade_desk.settings import TradingMode

from .drawdown import DrawdownState
from .kill_switch import KillSwitchState
from .limits import RiskLimits
from .operating_mode import ModeAuthorization


class DependencyHealth(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    database: bool = True
    queue: bool = True
    audit: bool = True
    broker: bool = True
    time_synchronized: bool = True


class AccountState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    account_id: str
    verified_at: datetime
    equity: Decimal = Field(gt=0)
    buying_power: Decimal = Field(ge=0)
    cash: Decimal = Field(ge=0)
    gross_exposure: Decimal = Field(ge=0)
    equity_exposure: Decimal = Field(ge=0)
    crypto_exposure: Decimal = Field(ge=0)
    daily_pnl: Decimal
    weekly_pnl: Decimal
    open_orders: int = Field(ge=0)
    live_orders_today: int = Field(ge=0)
    equity_day_trades_today: int = Field(ge=0)
    crypto_trades_24h: int = Field(ge=0)


class RiskContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    now: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expected_account_id: str
    account: AccountState
    market: MarketSnapshot
    mode_authorization: ModeAuthorization
    kill_switch: KillSwitchState
    drawdown: DrawdownState
    dependencies: DependencyHealth
    allowed_equities: frozenset[str] = frozenset()
    allowed_crypto: frozenset[str] = frozenset({"BTC-USD", "ETH-USD"})
    strategy_authorized: bool = True
    strategy_allocation: Decimal = Field(default=Decimal("0"), ge=0)
    sector_exposure: Decimal = Field(default=Decimal("0"), ge=0)
    correlated_exposure: Decimal = Field(default=Decimal("0"), ge=0)
    existing_symbol_exposure: Decimal = Field(default=Decimal("0"), ge=0)
    strategy_owned_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    signal_created_at: datetime
    event_block: bool = False
    plateau_stage: int = Field(default=0, ge=0, le=3)
    strategy_decay_suspended: bool = False
    equity_minutes_since_open: int | None = Field(default=None, ge=0)
    equity_day_entry_cutoff_reached: bool = False
    near_earnings: bool = False
    earnings_entry_permitted: bool = False
    duplicate_order: bool = False
    high_volatility_regime: bool = False


class RiskEngine:
    agent_id = "deterministic-risk-engine"
    version = "1.0.0"

    def __init__(self, limits: RiskLimits | None = None) -> None:
        self.limits = limits or RiskLimits()

    def evaluate(
        self,
        order: ProposedOrderPayload,
        context: RiskContext,
    ) -> RiskDecisionPayload:
        require(self.agent_id, Permission.APPROVE_RISK)
        reasons: list[str] = []
        now = context.now.astimezone(UTC)
        is_entry = not order.risk_reducing

        if context.kill_switch.killed or context.drawdown.trigger_hard_kill:
            reasons.append("KILL_SWITCH_ACTIVE")
        if context.mode_authorization.mode in {
            TradingMode.PAUSED,
            TradingMode.CAPITAL_PRESERVATION,
            TradingMode.KILLED,
        }:
            reasons.append("OPERATING_MODE_BLOCKS_NEW_ORDERS")
        if not context.mode_authorization.valid_for(context.market.asset_class, now):
            reasons.append("MODE_AUTHORIZATION_INVALID")
        if order.account_id != context.expected_account_id:
            reasons.append("ACCOUNT_IDENTITY_MISMATCH")
        if context.account.account_id != context.expected_account_id:
            reasons.append("VERIFIED_ACCOUNT_MISMATCH")
        if now - context.account.verified_at.astimezone(UTC) > timedelta(seconds=15):
            reasons.append("ACCOUNT_STATE_STALE")
        unhealthy = [
            name.upper()
            for name, healthy in context.dependencies.model_dump().items()
            if not healthy
        ]
        reasons.extend(f"{name}_UNAVAILABLE" for name in unhealthy)
        if not context.strategy_authorized:
            reasons.append("STRATEGY_UNAUTHORIZED")
        if context.event_block:
            reasons.append("EVENT_BLOCK")
        if context.strategy_decay_suspended and is_entry:
            reasons.append("STRATEGY_DECAY_SUSPENDED")
        if context.duplicate_order:
            reasons.append("DUPLICATE_ORDER")
        if context.plateau_stage >= 3 and is_entry:
            reasons.append("PLATEAU_STAGE_3")
        if context.drawdown.block_new_entries and is_entry:
            reasons.append("DRAWDOWN_RISK_REDUCING_ONLY")
        if context.signal_created_at.tzinfo is None:
            reasons.append("SIGNAL_TIMESTAMP_INVALID")
        elif now - context.signal_created_at.astimezone(UTC) > timedelta(minutes=5):
            reasons.append("SIGNAL_STALE")

        maximum_age = timedelta(
            seconds=(
                self.limits.maximum_market_data_age_seconds_equity
                if context.market.asset_class == AssetClass.EQUITY
                else self.limits.maximum_market_data_age_seconds_crypto
            )
        )
        if not context.market.is_fresh(maximum_age, now=now):
            reasons.append("MARKET_DATA_STALE")
        if context.market.asset_class == AssetClass.EQUITY:
            if context.market.symbol not in context.allowed_equities:
                reasons.append("SYMBOL_NOT_ALLOWLISTED")
            if not context.market.market_open:
                reasons.append("MARKET_CLOSED")
            maximum_spread = self.limits.maximum_spread_bps_equity
        elif context.market.asset_class == AssetClass.CRYPTO:
            if context.market.symbol not in context.allowed_crypto:
                reasons.append("SYMBOL_NOT_ALLOWLISTED")
            maximum_spread = self.limits.maximum_spread_bps_crypto
        else:
            reasons.append("ASSET_CLASS_UNSUPPORTED")
            maximum_spread = Decimal("0")
        if context.market.spread_bps is None:
            reasons.append("SPREAD_UNAVAILABLE")
        elif context.market.spread_bps > maximum_spread:
            reasons.append("SPREAD_LIMIT_EXCEEDED")
        if order.max_slippage_bps > maximum_spread:
            reasons.append("SLIPPAGE_TOLERANCE_TOO_HIGH")

        reference_price = order.limit_price or context.market.last
        notional = order.quantity * reference_price
        weight = notional / context.account.equity
        if order.planned_loss / context.account.equity > (
            self.limits.maximum_planned_loss_per_trade
        ):
            reasons.append("PLANNED_LOSS_LIMIT")
        if order.side == Side.BUY and notional > context.account.buying_power:
            reasons.append("INSUFFICIENT_BUYING_POWER")
        if order.side == Side.SELL and order.quantity > context.strategy_owned_quantity:
            reasons.append("STRATEGY_LOT_QUANTITY_EXCEEDED")
        if order.side == Side.BUY:
            projected_gross = (context.account.gross_exposure + notional) / (context.account.equity)
            projected_cash = (context.account.cash - notional) / context.account.equity
            if projected_gross > self.limits.maximum_gross_exposure:
                reasons.append("GROSS_EXPOSURE_LIMIT")
            if projected_cash < self.limits.minimum_cash_reserve:
                reasons.append("CASH_RESERVE_LIMIT")
        if context.market.asset_class == AssetClass.EQUITY:
            is_day_trade = order.time_horizon == TradingHorizon.DAY
            minutes_since_open = context.equity_minutes_since_open
            maximum_position = (
                self.limits.maximum_equity_day_position
                if is_day_trade
                else (
                    self.limits.maximum_long_term_position
                    if order.time_horizon == TradingHorizon.LONG_TERM
                    else self.limits.maximum_equity_position
                )
            )
            if is_day_trade and is_entry and minutes_since_open is None:
                reasons.append("EQUITY_SESSION_CLOCK_UNAVAILABLE")
            elif (
                is_day_trade
                and is_entry
                and minutes_since_open is not None
                and minutes_since_open < self.limits.block_open_minutes_equity
            ):
                reasons.append("EQUITY_OPENING_WINDOW_BLOCK")
            if is_day_trade and is_entry and context.equity_day_entry_cutoff_reached:
                reasons.append("EQUITY_DAY_ENTRY_CUTOFF")
            if is_entry and context.near_earnings and not context.earnings_entry_permitted:
                reasons.append("EARNINGS_PROXIMITY_BLOCK")
            if weight + context.existing_symbol_exposure > maximum_position:
                reasons.append("EQUITY_POSITION_LIMIT")
            maximum_sector = (
                self.limits.maximum_long_term_sector_exposure
                if order.time_horizon == TradingHorizon.LONG_TERM
                else self.limits.maximum_equity_position
            )
            if order.time_horizon != TradingHorizon.LONG_TERM:
                maximum_sector = self.limits.maximum_equity_sector_exposure
            if context.sector_exposure + weight > maximum_sector:
                reasons.append("SECTOR_EXPOSURE_LIMIT")
            if (
                context.account.equity_day_trades_today >= self.limits.maximum_new_equity_day_trades
                and is_day_trade
                and is_entry
            ):
                reasons.append("EQUITY_DAY_TRADE_COUNT_LIMIT")
        if context.market.asset_class == AssetClass.CRYPTO:
            maximum_crypto_position = (
                self.limits.maximum_crypto_day_position
                if order.time_horizon == TradingHorizon.DAY
                else self.limits.maximum_crypto_position
            )
            if weight + context.existing_symbol_exposure > maximum_crypto_position:
                reasons.append("CRYPTO_POSITION_LIMIT")
            if (
                context.account.crypto_exposure + notional
            ) / context.account.equity > self.limits.maximum_crypto_allocation:
                reasons.append("CRYPTO_ALLOCATION_LIMIT")
            if (
                context.account.crypto_trades_24h >= self.limits.maximum_new_crypto_trades_24h
                and is_entry
            ):
                reasons.append("CRYPTO_TRADE_COUNT_LIMIT")
        if context.strategy_allocation + weight > self.limits.maximum_strategy_allocation:
            reasons.append("STRATEGY_ALLOCATION_LIMIT")
        if context.correlated_exposure + weight > self.limits.maximum_total_deployed:
            reasons.append("CORRELATED_EXPOSURE_LIMIT")
        if context.account.open_orders >= self.limits.maximum_open_orders:
            reasons.append("OPEN_ORDER_COUNT_LIMIT")
        if (
            context.account.live_orders_today >= self.limits.maximum_live_orders_per_day
            and is_entry
        ):
            reasons.append("DAILY_ORDER_COUNT_LIMIT")
        if -context.account.daily_pnl / context.account.equity >= (self.limits.maximum_daily_loss):
            reasons.append("DAILY_LOSS_LIMIT")
        if -context.account.weekly_pnl / context.account.equity >= (
            self.limits.maximum_weekly_loss
        ):
            reasons.append("WEEKLY_LOSS_LIMIT")

        if reasons:
            if order.risk_reducing and all(
                reason
                in {
                    "DRAWDOWN_RISK_REDUCING_ONLY",
                    "PLATEAU_STAGE_3",
                    "STRATEGY_DECAY_SUSPENDED",
                    "DAILY_LOSS_LIMIT",
                    "WEEKLY_LOSS_LIMIT",
                    "OPERATING_MODE_BLOCKS_NEW_ORDERS",
                }
                for reason in reasons
            ):
                outcome = RiskOutcome.RISK_REDUCING_ONLY
                approved_quantity = order.quantity
            else:
                outcome = RiskOutcome.REJECTED
                approved_quantity = Decimal("0")
        else:
            outcome = RiskOutcome.APPROVED
            approved_quantity = order.quantity * context.drawdown.size_multiplier
            if context.high_volatility_regime:
                approved_quantity *= Decimal("0.50")
            if approved_quantity <= 0:
                outcome = RiskOutcome.REJECTED
                reasons.append("ZERO_APPROVED_QUANTITY")

        context_json = json.dumps(
            {
                "order": order.model_dump(mode="json"),
                "context": context.model_dump(mode="json"),
                "limits": self.limits.model_dump(mode="json"),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return RiskDecisionPayload(
            risk_decision_id=uuid4(),
            proposed_order_id=order.proposed_order_id,
            outcome=outcome,
            reason_codes=tuple(dict.fromkeys(reasons)) or ("ALL_CHECKS_PASSED",),
            approved_quantity=approved_quantity,
            valid_until=now + timedelta(seconds=15),
            risk_config_version=self.limits.version,
            context_checksum=hashlib.sha256(context_json.encode()).hexdigest(),
        )
