"""Append-only audit utilities and permission-boundary detection."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from quant_trade_desk.communication.permissions import Permission, is_allowed
from quant_trade_desk.communication.schemas import AgentMessage


class PermissionViolation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    agent_id: str
    attempted_permission: Permission
    message_id: str | None = None
    reason_code: str = "PERMISSION_BOUNDARY_VIOLATION"


class Auditor:
    agent_id = "auditor-communication-reporter"
    version = "1.0.0"

    def check_permission(
        self,
        *,
        agent_id: str,
        permission: Permission,
        message: AgentMessage | None = None,
    ) -> PermissionViolation | None:
        if is_allowed(agent_id, permission):
            return None
        return PermissionViolation(
            agent_id=agent_id,
            attempted_permission=permission,
            message_id=str(message.message_id) if message else None,
        )
