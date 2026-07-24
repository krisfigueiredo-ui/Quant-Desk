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

PRODUCERS: dict[MessageType, frozenset[str]] = {
    MessageType.MARKET_OBSERVATION: frozenset({"market-data-gateway", "tradingview-gateway"}),
    MessageType.SCANNER_CANDIDATE: frozenset({"equity-market-scanner", "crypto-market-scanner"}),
    MessageType.TECHNICAL_ASSESSMENT: frozenset({"technical-analyst"}),
    MessageType.FUNDAMENTAL_ASSESSMENT: frozenset({"fundamental-quality-analyst"}),
    MessageType.EVENT_RISK_ASSESSMENT: frozenset({"news-event-risk-analyst"}),
    MessageType.STRATEGY_SIGNAL: frozenset(
        {"day-trading-strategy-agent", "long-term-investment-agent"}
    ),
    MessageType.TRADE_INTENT: frozenset(
        {
            "day-trading-strategy-agent",
            "long-term-investment-agent",
            "position-exit-monitor",
        }
    ),
    MessageType.PORTFOLIO_DECISION: frozenset({"strategy-allocator", "portfolio-manager"}),
    MessageType.PROPOSED_ORDER: frozenset({"portfolio-manager"}),
    MessageType.RISK_DECISION: frozenset({"deterministic-risk-engine"}),
    MessageType.EXECUTION_REQUEST: frozenset({"execution-agent"}),
    MessageType.BROKER_ACKNOWLEDGEMENT: frozenset({"execution-agent"}),
    MessageType.ORDER_STATUS_UPDATE: frozenset({"execution-agent", "position-exit-monitor"}),
    MessageType.FILL_UPDATE: frozenset({"execution-agent", "position-exit-monitor"}),
    MessageType.POSITION_UPDATE: frozenset({"position-exit-monitor"}),
    MessageType.AGENT_HEALTH_UPDATE: frozenset(
        {
            "equity-market-scanner",
            "crypto-market-scanner",
            "technical-analyst",
            "fundamental-quality-analyst",
            "news-event-risk-analyst",
            "day-trading-strategy-agent",
            "long-term-investment-agent",
            "strategy-allocator",
            "portfolio-manager",
            "deterministic-risk-engine",
            "execution-agent",
            "position-exit-monitor",
            "auditor-communication-reporter",
        }
    ),
    MessageType.SYSTEM_ALERT: frozenset(
        {
            "deterministic-risk-engine",
            "execution-agent",
            "position-exit-monitor",
            "auditor-communication-reporter",
        }
    ),
    MessageType.KILL_SWITCH_EVENT: frozenset({"deterministic-risk-engine", "operator-control"}),
    MessageType.PLATEAU_EVENT: frozenset({"strategy-allocator"}),
    MessageType.STRATEGY_DECAY_EVENT: frozenset({"strategy-allocator"}),
    MessageType.CONFLICT_EVENT: frozenset({"portfolio-manager"}),
    MessageType.AUDIT_EVENT: frozenset({"auditor-communication-reporter"}),
}


def allowed_recipients(message_type: MessageType) -> tuple[str, ...]:
    return ROUTES.get(message_type, ("auditor-communication-reporter",))


def producer_allowed(agent_id: str, message_type: MessageType) -> bool:
    return agent_id in PRODUCERS.get(message_type, frozenset())
