"""Multi-confirmation profit-plateau state."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PlateauEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    days_since_meaningful_high: int = Field(ge=0)
    benchmark_relative_return: Decimal
    sharpe_change: Decimal
    expectancy: Decimal
    observations: int = Field(ge=0)
    confirmation_windows: int = Field(ge=0)


class PlateauState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    stage: int = Field(ge=0, le=3)
    risk_multiplier: Decimal = Field(ge=0, le=1)
    block_new_entries: bool
    move_to_shadow: bool
    reset_requires_manual_review: bool
    reason_codes: tuple[str, ...]


def evaluate_plateau(
    evidence: PlateauEvidence,
    *,
    minimum_observations: int = 30,
    minimum_confirmations: int = 2,
) -> PlateauState:
    confirmed = (
        evidence.days_since_meaningful_high >= 20
        and evidence.benchmark_relative_return <= 0
        and evidence.sharpe_change < 0
        and evidence.expectancy <= 0
        and evidence.observations >= minimum_observations
        and evidence.confirmation_windows >= minimum_confirmations
    )
    if not confirmed:
        return PlateauState(
            stage=0,
            risk_multiplier=Decimal("1"),
            block_new_entries=False,
            move_to_shadow=False,
            reset_requires_manual_review=False,
            reason_codes=(),
        )
    if evidence.days_since_meaningful_high >= 90 and evidence.confirmation_windows >= 4:
        return PlateauState(
            stage=3,
            risk_multiplier=Decimal("0"),
            block_new_entries=True,
            move_to_shadow=True,
            reset_requires_manual_review=True,
            reason_codes=("PLATEAU_STAGE_3",),
        )
    if evidence.days_since_meaningful_high >= 60 and evidence.confirmation_windows >= 3:
        return PlateauState(
            stage=2,
            risk_multiplier=Decimal("0.50"),
            block_new_entries=False,
            move_to_shadow=False,
            reset_requires_manual_review=True,
            reason_codes=("PLATEAU_STAGE_2",),
        )
    return PlateauState(
        stage=1,
        risk_multiplier=Decimal("0.75"),
        block_new_entries=False,
        move_to_shadow=False,
        reset_requires_manual_review=False,
        reason_codes=("PLATEAU_STAGE_1",),
    )
