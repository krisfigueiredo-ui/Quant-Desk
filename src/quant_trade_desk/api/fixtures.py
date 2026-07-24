"""Clearly labeled synthetic operations data for local/UI validation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from quant_trade_desk.agents.definitions import AGENT_DEFINITIONS
from quant_trade_desk.strategies.registry import STRATEGIES


def _stamp(minutes_ago: int = 0) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()


def overview_fixture() -> dict[str, object]:
    return {
        "is_synthetic": True,
        "data_mode": "SYNTHETIC_FIXTURE",
        "as_of": _stamp(),
        "total_verified_equity": 100_000,
        "cash": 78_250,
        "buying_power": 78_250,
        "total_exposure": 21_750,
        "equity_exposure": 17_750,
        "crypto_exposure": 4_000,
        "day_strategy_exposure": 3_500,
        "long_term_exposure": 18_250,
        "daily_pnl": 125.4,
        "weekly_pnl": -82.1,
        "total_pnl": 0,
        "current_drawdown": -0.012,
        "peak_equity": 101_215,
        "spy_relative_performance": 0,
        "btc_relative_crypto_performance": 0,
        "operating_mode": "PAPER",
        "live_equities_enabled": False,
        "live_crypto_enabled": False,
        "autonomous_execution_enabled": False,
        "kill_switch": "CLEAR",
        "data_freshness": "SYNTHETIC",
        "broker_connectivity": "PAPER_ADAPTER_READY",
        "open_positions": 3,
        "open_orders": 0,
        "active_alerts": 1,
        "series": {
            "equity": [
                {"time": _stamp(240), "portfolio": 100_000, "spy": 100_000},
                {"time": _stamp(180), "portfolio": 100_120, "spy": 100_080},
                {"time": _stamp(120), "portfolio": 100_060, "spy": 100_140},
                {"time": _stamp(60), "portfolio": 100_190, "spy": 100_170},
                {"time": _stamp(), "portfolio": 100_125.4, "spy": 100_185},
            ],
            "drawdown": [
                {"time": _stamp(240), "value": 0},
                {"time": _stamp(180), "value": -0.002},
                {"time": _stamp(120), "value": -0.006},
                {"time": _stamp(60), "value": -0.009},
                {"time": _stamp(), "value": -0.012},
            ],
        },
    }


def agents_fixture() -> list[dict[str, object]]:
    statuses = ("HEALTHY", "HEALTHY", "HEALTHY", "IDLE")
    return [
        {
            "agent_id": definition.agent_id,
            "name": definition.name,
            "role": definition.responsibility,
            "version": definition.version,
            "status": statuses[index % len(statuses)],
            "last_heartbeat": _stamp(index % 4),
            "current_task": ("Awaiting typed input" if index % 3 else "Processing fixture trace"),
            "inputs_received": 12 + index,
            "outputs_produced": 8 + index,
            "average_latency_ms": 18 + index * 3,
            "error_rate": 0,
            "timeout_count": 0,
            "messages_processed": 20 + index,
            "approvals": 1 if definition.agent_id == "deterministic-risk-engine" else 0,
            "rejections": 2 if definition.agent_id == "deterministic-risk-engine" else 0,
            "confidence": round(0.66 + (index % 3) * 0.05, 2),
            "health": statuses[index % len(statuses)],
        }
        for index, definition in enumerate(AGENT_DEFINITIONS.values())
    ]


def messages_fixture() -> list[dict[str, object]]:
    trace_id = str(uuid4())
    correlation_id = str(uuid4())
    flow = [
        ("MarketObservation", "market-data-gateway", "ACCEPTED", "Fresh paper quote"),
        ("ScannerCandidate", "equity-market-scanner", "ACCEPTED", "Ranked candidate"),
        ("TechnicalAssessment", "technical-analyst", "ACCEPTED", "Multi-factor confirmation"),
        ("EventRiskAssessment", "news-event-risk-analyst", "ACCEPTED", "No event block"),
        ("TradeIntent", "day-trading-strategy-agent", "ACCEPTED", "Limit intent"),
        ("PortfolioDecision", "portfolio-manager", "REJECTED", "Cash reserve would be breached"),
        ("RiskDecision", "deterministic-risk-engine", "REJECTED", "CASH_RESERVE_LIMIT"),
        ("AuditEvent", "auditor-communication-reporter", "ACCEPTED", "Safeguard recorded"),
    ]
    causation: str | None = None
    rows: list[dict[str, object]] = []
    for index, (message_type, agent_id, status, summary) in enumerate(flow):
        message_id = str(uuid4())
        rows.append(
            {
                "message_id": message_id,
                "message_type": message_type,
                "trace_id": trace_id,
                "correlation_id": correlation_id,
                "causation_id": causation,
                "agent_id": agent_id,
                "strategy_id": "equity-intraday-trend-pullback-v1",
                "asset_class": "EQUITY",
                "symbol": "SPY",
                "created_at": _stamp(8 - index),
                "status": status,
                "confidence": 0.72,
                "uncertainty": 0.28,
                "summary": summary,
                "is_synthetic": True,
            }
        )
        causation = message_id
    return rows


def scanner_fixture() -> list[dict[str, object]]:
    return [
        {
            "symbol": "SPY",
            "asset_class": "EQUITY",
            "rank": 1,
            "score": 78.4,
            "trend": "UP",
            "relative_strength": 0.64,
            "momentum": 0.58,
            "volume": "1.2x",
            "volatility": 0.18,
            "liquidity": "HIGH",
            "regime": "TRENDING",
            "analyst_status": "QUALIFIED",
            "event_block": False,
            "strategy_eligibility": "PAPER_ONLY",
            "rejection_reason": None,
            "is_synthetic": True,
        },
        {
            "symbol": "BTC-USD",
            "asset_class": "CRYPTO",
            "rank": 1,
            "score": 72.1,
            "trend": "UP",
            "relative_strength": 0.51,
            "momentum": 0.49,
            "volume": "1.1x",
            "volatility": 0.52,
            "liquidity": "HIGH",
            "regime": "VOLATILITY_EXPANSION",
            "analyst_status": "REVIEW",
            "event_block": False,
            "strategy_eligibility": "PAPER_ONLY",
            "rejection_reason": "SPREAD_NEAR_LIMIT",
            "is_synthetic": True,
        },
    ]


def strategies_fixture() -> list[dict[str, object]]:
    return [
        {
            **definition.model_dump(mode="json"),
            "operating_mode": "PAPER",
            "out_of_sample_metrics": None,
            "live_metrics": None,
            "benchmark_comparison": "NOT_VALIDATED",
            "drawdown": None,
            "rolling_expectancy": None,
            "plateau_status": "NOT_EVALUATED",
            "decay_status": "NOT_EVALUATED",
            "current_allocation": 0,
            "is_synthetic": True,
        }
        for definition in STRATEGIES.values()
    ]


def risk_fixture() -> dict[str, object]:
    return {
        "is_synthetic": True,
        "current_drawdown": -0.012,
        "thresholds": [0.05, 0.10, 0.15, 0.20, 0.25, 0.37],
        "daily_loss": -0.0008,
        "weekly_loss": -0.0017,
        "position_concentration": 0.05,
        "sector_concentration": 0.09,
        "asset_class_allocation": {"equity": 0.1775, "crypto": 0.04, "cash": 0.7825},
        "strategy_allocation": {
            "equity-quality-momentum-v1": 0.1425,
            "equity-intraday-trend-pullback-v1": 0.035,
            "crypto-intraday-breakout-v1": 0.04,
        },
        "kill_switch": "CLEAR",
        "plateau_states": [],
        "strategy_decay_states": [],
        "recent_rejections": ["CASH_RESERVE_LIMIT", "SIGNAL_STALE"],
        "remaining_daily_loss_budget": 0.0092,
        "controls_require_authentication": True,
    }


def orders_fixture() -> list[dict[str, object]]:
    return [
        {
            "proposed_order_id": str(uuid4()),
            "state": "REJECTED",
            "symbol": "SPY",
            "asset_class": "EQUITY",
            "strategy_id": "equity-intraday-trend-pullback-v1",
            "side": "BUY",
            "quantity": 5,
            "order_type": "LIMIT",
            "limit_price": 620.15,
            "risk_decision": "REJECTED",
            "reason": "CASH_RESERVE_LIMIT",
            "trace_id": messages_fixture()[0]["trace_id"],
            "created_at": _stamp(1),
            "idempotency_state": "CLAIMED",
            "is_synthetic": True,
        }
    ]
