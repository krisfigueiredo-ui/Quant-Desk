"""Registry of the thirteen desk agents/services."""

from __future__ import annotations

from quant_trade_desk.communication.schemas import MessageType as M

from .base import AgentDefinition, RetryPolicy

NO_TRADE = (
    "submit orders",
    "cancel orders",
    "activate live trading",
    "override the deterministic risk engine",
)


def _definition(
    agent_id: str,
    name: str,
    responsibility: str,
    inputs: tuple[M, ...],
    outputs: tuple[M, ...],
    *,
    prohibited: tuple[str, ...] = NO_TRADE,
    timeout: float = 15,
    attempts: int = 2,
    failure: str = "Emit a structured failure audit event and produce no downstream approval.",
) -> AgentDefinition:
    return AgentDefinition(
        agent_id=agent_id,
        name=name,
        version="1.0.0",
        responsibility=responsibility,
        allowed_inputs=inputs,
        allowed_outputs=outputs,
        prohibited_actions=prohibited,
        timeout_seconds=timeout,
        retry_policy=RetryPolicy(max_attempts=attempts),
        failure_behavior=failure,
    )


AGENT_DEFINITIONS: dict[str, AgentDefinition] = {
    "equity-market-scanner": _definition(
        "equity-market-scanner",
        "Equity Market Scanner",
        "Rank eligible liquid US equities using deterministic data-quality filters.",
        (M.MARKET_OBSERVATION,),
        (M.SCANNER_CANDIDATE, M.AGENT_HEALTH_UPDATE),
    ),
    "crypto-market-scanner": _definition(
        "crypto-market-scanner",
        "Crypto Market Scanner",
        "Rank only allowlisted, venue-supported spot cryptocurrencies.",
        (M.MARKET_OBSERVATION,),
        (M.SCANNER_CANDIDATE, M.AGENT_HEALTH_UPDATE),
    ),
    "technical-analyst": _definition(
        "technical-analyst",
        "Technical Analyst",
        "Produce multi-indicator, multi-timeframe structured technical assessments.",
        (M.SCANNER_CANDIDATE, M.MARKET_OBSERVATION),
        (M.TECHNICAL_ASSESSMENT, M.AGENT_HEALTH_UPDATE),
    ),
    "fundamental-quality-analyst": _definition(
        "fundamental-quality-analyst",
        "Fundamental and Quality Analyst",
        "Separate reported facts, calculations, estimates, interpretations, and missing data.",
        (M.SCANNER_CANDIDATE,),
        (M.FUNDAMENTAL_ASSESSMENT, M.AGENT_HEALTH_UPDATE),
    ),
    "news-event-risk-analyst": _definition(
        "news-event-risk-analyst",
        "News and Event-Risk Analyst",
        "Detect confirmed, stale, duplicate, contradictory, or execution-blocking events.",
        (M.SCANNER_CANDIDATE,),
        (M.EVENT_RISK_ASSESSMENT, M.AGENT_HEALTH_UPDATE),
    ),
    "day-trading-strategy-agent": _definition(
        "day-trading-strategy-agent",
        "Day-Trading Strategy Agent",
        "Create deterministic intraday trade intents under asset-specific session rules.",
        (M.TECHNICAL_ASSESSMENT, M.EVENT_RISK_ASSESSMENT),
        (M.STRATEGY_SIGNAL, M.TRADE_INTENT, M.AGENT_HEALTH_UPDATE),
    ),
    "long-term-investment-agent": _definition(
        "long-term-investment-agent",
        "Long-Term Investment Agent",
        "Create swing, position, and long-horizon intents from quality and trend evidence.",
        (
            M.TECHNICAL_ASSESSMENT,
            M.FUNDAMENTAL_ASSESSMENT,
            M.EVENT_RISK_ASSESSMENT,
        ),
        (M.STRATEGY_SIGNAL, M.TRADE_INTENT, M.AGENT_HEALTH_UPDATE),
    ),
    "strategy-allocator": _definition(
        "strategy-allocator",
        "Strategy Allocator",
        "Allocate among validated strategies using stability, sample, cost, and drawdown caps.",
        (M.STRATEGY_SIGNAL, M.PLATEAU_EVENT, M.STRATEGY_DECAY_EVENT),
        (M.PORTFOLIO_DECISION, M.AGENT_HEALTH_UPDATE),
    ),
    "portfolio-manager": _definition(
        "portfolio-manager",
        "Portfolio Manager",
        "Resolve strategy-lot conflicts and create immutable proposed orders.",
        (M.TRADE_INTENT, M.FILL_UPDATE, M.POSITION_UPDATE),
        (M.PORTFOLIO_DECISION, M.PROPOSED_ORDER, M.CONFLICT_EVENT),
    ),
    "deterministic-risk-engine": _definition(
        "deterministic-risk-engine",
        "Deterministic Risk Engine",
        "Final non-LLM veto authority for all execution requests.",
        (M.PROPOSED_ORDER, M.KILL_SWITCH_EVENT, M.PLATEAU_EVENT),
        (M.RISK_DECISION, M.SYSTEM_ALERT),
        prohibited=("submit orders", "cancel orders", "activate live trading"),
        timeout=2,
        attempts=0,
        failure="Return REJECTED with RISK_ENGINE_UNAVAILABLE; never retry an approval.",
    ),
    "execution-agent": _definition(
        "execution-agent",
        "Execution Agent",
        "Narrow deterministic service that submits only immutable, authorized orders.",
        (M.PROPOSED_ORDER, M.RISK_DECISION, M.EXECUTION_REQUEST),
        (
            M.BROKER_ACKNOWLEDGEMENT,
            M.ORDER_STATUS_UPDATE,
            M.FILL_UPDATE,
            M.SYSTEM_ALERT,
        ),
        prohibited=(
            "select symbols",
            "generate signals",
            "increase quantity",
            "reverse side",
            "change account",
            "override a risk decision",
            "activate live trading",
        ),
        timeout=10,
        attempts=0,
        failure="Quarantine uncertain order state and block resubmission pending reconciliation.",
    ),
    "position-exit-monitor": _definition(
        "position-exit-monitor",
        "Position and Exit Monitor",
        "Monitor stops, exits, reconciliation, strategy ownership, and orphaned positions.",
        (M.FILL_UPDATE, M.POSITION_UPDATE, M.EVENT_RISK_ASSESSMENT),
        (M.TRADE_INTENT, M.SYSTEM_ALERT, M.AGENT_HEALTH_UPDATE),
    ),
    "auditor-communication-reporter": _definition(
        "auditor-communication-reporter",
        "Auditor and Communication Reporter",
        "Record append-only decisions and produce redacted communication reports.",
        tuple(M),
        (M.AUDIT_EVENT, M.SYSTEM_ALERT, M.AGENT_HEALTH_UPDATE),
        prohibited=(
            "submit orders",
            "cancel orders",
            "modify historical audit records",
            "activate live trading",
            "reset kill switches",
        ),
        timeout=10,
        attempts=3,
    ),
}
