"""Deny-by-default agent permission policy."""

from __future__ import annotations

from enum import StrEnum


class Permission(StrEnum):
    READ_MARKET_DATA = "READ_MARKET_DATA"
    READ_ACCOUNT_DATA = "READ_ACCOUNT_DATA"
    GENERATE_SIGNAL = "GENERATE_SIGNAL"
    PROPOSE_POSITION = "PROPOSE_POSITION"
    APPROVE_RISK = "APPROVE_RISK"
    REQUEST_EXECUTION = "REQUEST_EXECUTION"
    SUBMIT_ORDER = "SUBMIT_ORDER"
    CANCEL_ORDER = "CANCEL_ORDER"
    VIEW_SECRETS = "VIEW_SECRETS"
    CHANGE_CONFIGURATION = "CHANGE_CONFIGURATION"
    ACTIVATE_LIVE = "ACTIVATE_LIVE"
    RESET_KILL_SWITCH = "RESET_KILL_SWITCH"


class PermissionDenied(RuntimeError):
    def __init__(self, agent_id: str, permission: Permission) -> None:
        super().__init__(f"{agent_id} lacks {permission.value}")
        self.agent_id = agent_id
        self.permission = permission


PERMISSIONS: dict[str, frozenset[Permission]] = {
    "equity-market-scanner": frozenset({Permission.READ_MARKET_DATA}),
    "crypto-market-scanner": frozenset({Permission.READ_MARKET_DATA}),
    "technical-analyst": frozenset({Permission.READ_MARKET_DATA}),
    "fundamental-quality-analyst": frozenset({Permission.READ_MARKET_DATA}),
    "news-event-risk-analyst": frozenset({Permission.READ_MARKET_DATA}),
    "day-trading-strategy-agent": frozenset(
        {Permission.READ_MARKET_DATA, Permission.GENERATE_SIGNAL}
    ),
    "long-term-investment-agent": frozenset(
        {Permission.READ_MARKET_DATA, Permission.GENERATE_SIGNAL}
    ),
    "strategy-allocator": frozenset({Permission.READ_MARKET_DATA}),
    "portfolio-manager": frozenset({Permission.READ_ACCOUNT_DATA, Permission.PROPOSE_POSITION}),
    "deterministic-risk-engine": frozenset(
        {
            Permission.READ_MARKET_DATA,
            Permission.READ_ACCOUNT_DATA,
            Permission.APPROVE_RISK,
        }
    ),
    "execution-agent": frozenset(
        {
            Permission.READ_MARKET_DATA,
            Permission.READ_ACCOUNT_DATA,
            Permission.REQUEST_EXECUTION,
            Permission.SUBMIT_ORDER,
            Permission.CANCEL_ORDER,
        }
    ),
    "position-exit-monitor": frozenset(
        {
            Permission.READ_MARKET_DATA,
            Permission.READ_ACCOUNT_DATA,
            Permission.GENERATE_SIGNAL,
        }
    ),
    "auditor-communication-reporter": frozenset(),
}


def is_allowed(agent_id: str, permission: Permission) -> bool:
    return permission in PERMISSIONS.get(agent_id, frozenset())


def require(agent_id: str, permission: Permission) -> None:
    if not is_allowed(agent_id, permission):
        raise PermissionDenied(agent_id, permission)
