"""Versioned conservative risk limits."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RiskLimits(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = "1.0.0"
    maximum_total_deployed: Decimal = Field(default=Decimal("0.50"), ge=0, le=1)
    maximum_gross_exposure: Decimal = Field(default=Decimal("0.50"), ge=0, le=1)
    minimum_cash_reserve: Decimal = Field(default=Decimal("0.50"), ge=0, le=1)
    maximum_daily_loss: Decimal = Field(default=Decimal("0.01"), ge=0, le=1)
    maximum_weekly_loss: Decimal = Field(default=Decimal("0.03"), ge=0, le=1)
    maximum_planned_loss_per_trade: Decimal = Field(default=Decimal("0.0025"), ge=0, le=1)
    maximum_live_orders_per_day: int = Field(default=5, ge=0, le=100)
    maximum_open_orders: int = Field(default=5, ge=0, le=100)
    maximum_equity_position: Decimal = Field(default=Decimal("0.05"), ge=0, le=1)
    maximum_equity_day_position: Decimal = Field(default=Decimal("0.02"), ge=0, le=1)
    maximum_new_equity_day_trades: int = Field(default=3, ge=0, le=100)
    maximum_equity_sector_exposure: Decimal = Field(default=Decimal("0.15"), ge=0, le=1)
    maximum_crypto_allocation: Decimal = Field(default=Decimal("0.10"), ge=0, le=1)
    maximum_crypto_position: Decimal = Field(default=Decimal("0.02"), ge=0, le=1)
    maximum_crypto_day_position: Decimal = Field(default=Decimal("0.01"), ge=0, le=1)
    maximum_new_crypto_trades_24h: int = Field(default=3, ge=0, le=100)
    maximum_long_term_position: Decimal = Field(default=Decimal("0.05"), ge=0, le=1)
    maximum_long_term_sector_exposure: Decimal = Field(default=Decimal("0.20"), ge=0, le=1)
    maximum_spread_bps_equity: Decimal = Field(default=Decimal("35"), ge=0)
    maximum_spread_bps_crypto: Decimal = Field(default=Decimal("60"), ge=0)
    maximum_market_data_age_seconds_equity: int = Field(default=15, ge=1)
    maximum_market_data_age_seconds_crypto: int = Field(default=10, ge=1)
    block_open_minutes_equity: int = Field(default=15, ge=0, le=120)
    maximum_correlation: Decimal = Field(default=Decimal("0.85"), ge=0, le=1)
    maximum_strategy_allocation: Decimal = Field(default=Decimal("0.20"), ge=0, le=1)

    @model_validator(mode="after")
    def cash_and_deployment_are_consistent(self) -> RiskLimits:
        if self.maximum_total_deployed + self.minimum_cash_reserve > Decimal("1"):
            raise ValueError("deployment cap and cash reserve cannot exceed 100%")
        return self
