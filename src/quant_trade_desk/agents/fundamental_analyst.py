"""Fundamental and quality assessment with explicit provenance categories."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from quant_trade_desk.communication.schemas import (
    AssetClass,
    FundamentalAssessmentPayload,
)

EQUITY_FACTS = {
    "revenue_growth",
    "earnings_growth",
    "gross_margin",
    "operating_margin",
    "free_cash_flow",
    "roic",
    "debt",
    "interest_coverage",
    "dilution",
    "valuation",
    "earnings_quality",
}
CRYPTO_FACTS = {
    "network_usage",
    "supply_schedule",
    "token_concentration",
    "protocol_revenue",
    "security_history",
    "liquidity",
    "venue_support",
    "regulatory_risk",
}


class FundamentalAnalyst:
    agent_id = "fundamental-quality-analyst"
    version = "1.0.0"

    def analyze(
        self,
        *,
        asset_class: AssetClass,
        reported_facts: dict[str, Any],
        calculated_metrics: dict[str, Any],
        third_party_estimates: dict[str, Any],
        interpretations: tuple[str, ...],
    ) -> FundamentalAssessmentPayload:
        allowed = EQUITY_FACTS if asset_class == AssetClass.EQUITY else CRYPTO_FACTS
        supplied = set(reported_facts) | set(calculated_metrics) | set(third_party_estimates)
        prohibited = sorted(supplied - allowed)
        if asset_class == AssetClass.CRYPTO and supplied & EQUITY_FACTS:
            prohibited = sorted(supplied & EQUITY_FACTS)
        missing = sorted(allowed - supplied)
        if prohibited:
            return FundamentalAssessmentPayload(
                reported_facts=reported_facts,
                calculated_metrics=calculated_metrics,
                third_party_estimates=third_party_estimates,
                interpretation=interpretations,
                missing_data=tuple(missing),
                decision=f"REJECT_PROHIBITED_FIELDS:{','.join(prohibited)}",
            )
        numeric = [
            Decimal(str(value))
            for value in {**reported_facts, **calculated_metrics}.values()
            if isinstance(value, (int, float, Decimal))
        ]
        score = (
            max(
                Decimal("0"),
                min(
                    Decimal("100"),
                    Decimal("50")
                    + (
                        sum(numeric, Decimal("0")) / Decimal(len(numeric)) * 10
                        if numeric
                        else Decimal("0")
                    ),
                ),
            )
            if supplied
            else None
        )
        return FundamentalAssessmentPayload(
            score=score,
            reported_facts=reported_facts,
            calculated_metrics=calculated_metrics,
            third_party_estimates=third_party_estimates,
            interpretation=interpretations,
            missing_data=tuple(missing),
            decision="ASSESSMENT_COMPLETE" if supplied else "INSUFFICIENT_DATA",
        )
