"""Deterministic multi-indicator technical assessment."""

from __future__ import annotations

from decimal import Decimal

from quant_trade_desk.communication.schemas import AssessmentPayload, EvidenceItem
from quant_trade_desk.data.quality import MarketSnapshot


class TechnicalAnalyst:
    agent_id = "technical-analyst"
    version = "1.0.0"

    def analyze(self, snapshot: MarketSnapshot) -> AssessmentPayload:
        metrics = snapshot.metrics
        required = {
            "trend",
            "momentum",
            "rsi",
            "volume_confirmation",
            "multi_timeframe_alignment",
        }
        missing = sorted(required - metrics.keys())
        if missing:
            return AssessmentPayload(
                score=Decimal("0"),
                decision="REJECT",
                time_horizon="UNCLASSIFIED",
                reject_reason=f"MISSING_METRICS:{','.join(missing)}",
            )
        signals = {
            "trend": metrics["trend"],
            "momentum": metrics["momentum"],
            "volume_confirmation": metrics["volume_confirmation"],
            "multi_timeframe_alignment": metrics["multi_timeframe_alignment"],
            "breakout": metrics.get("breakout", Decimal("0")),
            "adx": metrics.get("adx", Decimal("0")) / Decimal("100"),
        }
        bullish = [
            EvidenceItem(
                kind="technical",
                metric=name,
                value=value,
                interpretation=f"{name} supports the long setup",
                source_id=snapshot.source_id,
            )
            for name, value in signals.items()
            if value > Decimal("0.2")
        ]
        bearish = [
            EvidenceItem(
                kind="technical",
                metric=name,
                value=value,
                interpretation=f"{name} weakens the long setup",
                source_id=snapshot.source_id,
            )
            for name, value in signals.items()
            if value < Decimal("-0.2")
        ]
        rsi = metrics["rsi"]
        if rsi >= 75:
            bearish.append(
                EvidenceItem(
                    kind="technical",
                    metric="rsi",
                    value=rsi,
                    interpretation="oscillator is extended",
                    source_id=snapshot.source_id,
                )
            )
        composite = sum(signals.values(), Decimal("0")) / Decimal(len(signals))
        score = max(Decimal("0"), min(Decimal("100"), (composite + 1) * 50))
        decision = "QUALIFIED" if len(bullish) >= 3 and len(bearish) <= 1 else "REJECT"
        atr = metrics.get("atr", snapshot.last * Decimal("0.02"))
        return AssessmentPayload(
            score=score,
            decision=decision,
            bullish_evidence=tuple(bullish),
            bearish_evidence=tuple(bearish),
            entry_zone_low=max(Decimal("0.00000001"), snapshot.last - atr / 2),
            entry_zone_high=snapshot.last + atr / 4,
            invalidation_level=max(Decimal("0.00000001"), snapshot.last - atr * 2),
            stop_framework="ATR-based hard invalidation; deterministic risk engine sizes loss.",
            exit_framework="Time, thesis, target, or trailing exit according to strategy registry.",
            time_horizon=(
                "INTRADAY" if metrics.get("horizon_intraday", Decimal("0")) > 0 else "SWING"
            ),
            reject_reason=None if decision == "QUALIFIED" else "INSUFFICIENT_CONFIRMATION",
        )
