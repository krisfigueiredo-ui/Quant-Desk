"""Stability-aware strategy allocator."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from quant_trade_desk.strategies.decay import StrategyPerformance, evaluate_decay


class StrategyAllocation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    strategy_id: str
    allocation: Decimal = Field(ge=0, le=1)
    reason_codes: tuple[str, ...]


class StrategyAllocator:
    agent_id = "strategy-allocator"
    version = "1.0.0"

    def allocate(
        self,
        performances: tuple[StrategyPerformance, ...],
        *,
        total_cap: Decimal = Decimal("0.20"),
        per_strategy_cap: Decimal = Decimal("0.05"),
    ) -> tuple[StrategyAllocation, ...]:
        eligible: list[tuple[StrategyPerformance, Decimal]] = []
        results: list[StrategyAllocation] = []
        for performance in performances:
            decay = evaluate_decay(performance)
            if decay.suspended or performance.observations < 30:
                results.append(
                    StrategyAllocation(
                        strategy_id=performance.strategy_id,
                        allocation=Decimal("0"),
                        reason_codes=decay.reason_codes or ("INADEQUATE_SAMPLE",),
                    )
                )
                continue
            quality = max(
                Decimal("0"),
                performance.sharpe
                * max(Decimal("0"), performance.excess_return)
                / (Decimal("1") + abs(performance.maximum_drawdown)),
            )
            eligible.append((performance, quality))
        total_quality = sum((quality for _, quality in eligible), Decimal("0"))
        for performance, quality in eligible:
            raw = (
                total_cap / len(eligible)
                if total_quality == 0
                else total_cap * quality / total_quality
            )
            results.append(
                StrategyAllocation(
                    strategy_id=performance.strategy_id,
                    allocation=min(per_strategy_cap, raw),
                    reason_codes=("STABILITY_WEIGHTED_WITH_HARD_CAP",),
                )
            )
        return tuple(sorted(results, key=lambda row: row.strategy_id))
