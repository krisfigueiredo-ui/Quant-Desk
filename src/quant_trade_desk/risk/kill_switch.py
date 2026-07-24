"""Persistent hard-kill state.

Reset is intentionally not exposed. Operators must follow the documented
offline forensic-reset procedure.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock

from pydantic import BaseModel, ConfigDict


class KillSwitchState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    killed: bool = False
    activated_at: datetime | None = None
    reason_code: str | None = None
    incident_id: str | None = None
    reset_requires_offline_review: bool = True


class PersistentKillSwitch:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = RLock()

    def read(self) -> KillSwitchState:
        with self._lock:
            if not self.path.exists():
                return KillSwitchState()
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                return KillSwitchState.model_validate(payload)
            except (OSError, ValueError, json.JSONDecodeError):
                return KillSwitchState(
                    killed=True,
                    activated_at=datetime.now(UTC),
                    reason_code="KILL_STATE_UNREADABLE_FAIL_CLOSED",
                    incident_id="unreadable-state",
                )

    def activate(self, reason_code: str, incident_id: str) -> KillSwitchState:
        state = KillSwitchState(
            killed=True,
            activated_at=datetime.now(UTC),
            reason_code=reason_code,
            incident_id=incident_id,
        )
        with self._lock:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(
                state.model_dump_json(indent=2),
                encoding="utf-8",
            )
            os.chmod(temporary, 0o600)
            temporary.replace(self.path)
        return state
