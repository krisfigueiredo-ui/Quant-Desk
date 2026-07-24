"""Explicit message routing rules."""

from __future__ import annotations

from .schemas import MessageType

ROUTES: dict[MessageType, tuple[str, ...]] = {
    MessageType.MARKET_OBSERVATION: ("equity-market-scanner", "crypto-market-scanner"),
    MessageType.SCANNER_CANDIDATE: (
        "technical-analyst",
        "fundamental-quality-analyst",
        "news-event-risk-analyst",
    ),
    MessageType.TECHNICAL_ASSESSMENT: (
        "day-trading-strategy-agent",
        "long-term-investment-agent",
    ),
    MessageType.FUNDAMENTAL_ASSESSMENT: ("long-term-investment-agent",),
    MessageType.EVENT_RISK_ASSESSMENT: (
        "day-trading-strategy-agent",
        "long-term-investment-agent",
    ),
    MessageType.TRADE_INTENT: ("portfolio-manager",),
    MessageType.PORTFOLIO_DECISION: ("deterministic-risk-engine",),
    MessageType.PROPOSED_ORDER: ("deterministic-risk-engine",),
    MessageType.RISK_DECISION: ("execution-agent", "auditor-communication-reporter"),
    MessageType.EXECUTION_REQUEST: ("execution-agent",),
    MessageType.BROKER_ACKNOWLEDGEMENT: (
        "position-exit-monitor",
        "auditor-communication-reporter",
    ),
    MessageType.ORDER_STATUS_UPDATE: (
        "position-exit-monitor",
        "auditor-communication-reporter",
    ),
    MessageType.FILL_UPDATE: (
        "portfolio-manager",
        "position-exit-monitor",
        "auditor-communication-reporter",
    ),
}


def allowed_recipients(message_type: MessageType) -> tuple[str, ...]:
    return ROUTES.get(message_type, ("auditor-communication-reporter",))
