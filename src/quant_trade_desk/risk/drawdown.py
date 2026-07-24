"""Drawdown calculation and staged response."""

from __future__ import annotations

from decimal import Decimal
from enum import IntEnum

from pydantic import BaseModel, ConfigDict, Field


class DrawdownStage(IntEnum):
    NORMAL = 0
    NOTIFY_REDUCE_25 = 1
    INCIDENT_REDUCE_50 = 2
    RISK_REDUCING_ONLY = 3
    SUSPEND_AUTONOMY = 4
    CAPITAL_PRESERVATION = 5
    HARD_KILL = 6


class DrawdownState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    peak_equity: Decimal = Field(gt=0)
    current_equity: Decimal = Field(ge=0)
    drawdown: Decimal = Field(le=0)
    stage: DrawdownStage
    size_multiplier: Decimal = Field(ge=0, le=1)
    block_new_entries: bool
    suspend_autonomy: bool
    trigger_hard_kill: bool
    reason_codes: tuple[str, ...]


def calculate_drawdown(
    *,
    verified_current_equity: Decimal,
    verified_peak_equity: Decimal,
) -> DrawdownState:
    if verified_peak_equity <= 0:
        raise ValueError("verified peak equity must be positive")
    if verified_current_equity < 0:
        raise ValueError("verified current equity cannot be negative")
    drawdown = (verified_current_equity - verified_peak_equity) / verified_peak_equity
    loss = -drawdown
    codes: tuple[str, ...]
    if loss >= Decimal("0.37"):
        return DrawdownState(
            peak_equity=verified_peak_equity,
            current_equity=verified_current_equity,
            drawdown=drawdown,
            stage=DrawdownStage.HARD_KILL,
            size_multiplier=Decimal("0"),
            block_new_entries=True,
            suspend_autonomy=True,
            trigger_hard_kill=True,
            reason_codes=("DRAWDOWN_37_HARD_KILL",),
        )
    if loss >= Decimal("0.25"):
        stage, multiplier, codes = (
            DrawdownStage.CAPITAL_PRESERVATION,
            Decimal("0"),
            ("DRAWDOWN_25_CAPITAL_PRESERVATION",),
        )
    elif loss >= Decimal("0.20"):
        stage, multiplier, codes = (
            DrawdownStage.SUSPEND_AUTONOMY,
            Decimal("0"),
            ("DRAWDOWN_20_AUTONOMY_SUSPENDED",),
        )
    elif loss >= Decimal("0.15"):
        stage, multiplier, codes = (
            DrawdownStage.RISK_REDUCING_ONLY,
            Decimal("0"),
            ("DRAWDOWN_15_RISK_REDUCING_ONLY",),
        )
    elif loss >= Decimal("0.10"):
        stage, multiplier, codes = (
            DrawdownStage.INCIDENT_REDUCE_50,
            Decimal("0.50"),
            ("DRAWDOWN_10_REDUCE_50",),
        )
    elif loss >= Decimal("0.05"):
        stage, multiplier, codes = (
            DrawdownStage.NOTIFY_REDUCE_25,
            Decimal("0.75"),
            ("DRAWDOWN_5_REDUCE_25",),
        )
    else:
        stage, multiplier, codes = (
            DrawdownStage.NORMAL,
            Decimal("1"),
            (),
        )
    return DrawdownState(
        peak_equity=verified_peak_equity,
        current_equity=verified_current_equity,
        drawdown=drawdown,
        stage=stage,
        size_multiplier=multiplier,
        block_new_entries=stage >= DrawdownStage.RISK_REDUCING_ONLY,
        suspend_autonomy=stage >= DrawdownStage.SUSPEND_AUTONOMY,
        trigger_hard_kill=False,
        reason_codes=codes,
    )
