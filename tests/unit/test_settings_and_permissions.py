from __future__ import annotations

import pytest

from quant_trade_desk.communication.permissions import (
    Permission,
    PermissionDenied,
    is_allowed,
    require,
)
from quant_trade_desk.settings import Settings, TradingMode


def test_safe_defaults() -> None:
    settings = Settings()
    assert settings.trading_mode == TradingMode.PAPER
    assert settings.live_equities_enabled is False
    assert settings.live_crypto_enabled is False
    assert settings.autonomous_execution_enabled is False


def test_live_flags_cannot_be_enabled_outside_live_mode() -> None:
    with pytest.raises(ValueError, match="live asset flags"):
        Settings(live_equities_enabled=True)


def test_standard_live_cannot_be_configured() -> None:
    with pytest.raises(ValueError, match="STANDARD_LIVE"):
        Settings(
            trading_mode=TradingMode.STANDARD_LIVE,
            live_equities_enabled=True,
        )


@pytest.mark.parametrize(
    "agent_id",
    [
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
        "position-exit-monitor",
        "auditor-communication-reporter",
    ],
)
def test_only_execution_agent_can_submit(agent_id: str) -> None:
    assert is_allowed(agent_id, Permission.SUBMIT_ORDER) is False
    with pytest.raises(PermissionDenied):
        require(agent_id, Permission.SUBMIT_ORDER)


def test_execution_agent_is_narrowly_authorized() -> None:
    assert is_allowed("execution-agent", Permission.SUBMIT_ORDER)
    assert not is_allowed("execution-agent", Permission.GENERATE_SIGNAL)
    assert not is_allowed("execution-agent", Permission.APPROVE_RISK)
    assert not is_allowed("execution-agent", Permission.ACTIVATE_LIVE)
