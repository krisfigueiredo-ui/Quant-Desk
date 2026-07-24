"""Authenticated, audited, deterministic controls. No live activation route."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from quant_trade_desk.api.auth import require_operator

router = APIRouter()


class ControlRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    confirmation_phrase: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=3, max_length=500)


@router.post("/pause")
def pause_new_trades(
    payload: ControlRequest,
    request: Request,
    operator: str = Depends(require_operator),
) -> dict[str, object]:
    if payload.confirmation_phrase != "PAUSE NEW TRADES":
        raise HTTPException(status_code=400, detail="exact confirmation phrase required")
    request.app.state.paused = True
    request.app.state.metrics.increment("quant_desk_control_events_total", control="pause")
    return {
        "status": "PAUSED",
        "new_entries_blocked": True,
        "actor": operator,
        "audit_reason": payload.reason,
    }


@router.post("/emergency-stop")
def emergency_stop(
    payload: ControlRequest,
    request: Request,
    operator: str = Depends(require_operator),
) -> dict[str, object]:
    if payload.confirmation_phrase != "EMERGENCY STOP":
        raise HTTPException(status_code=400, detail="exact confirmation phrase required")
    state = request.app.state.kill_switch.activate(
        reason_code="OPERATOR_EMERGENCY_STOP",
        incident_id=f"manual-{request.app.state.incident_counter}",
    )
    request.app.state.incident_counter += 1
    request.app.state.metrics.increment("quant_desk_control_events_total", control="emergency_stop")
    return {
        "status": "KILLED",
        "kill_switch": state.model_dump(mode="json"),
        "actor": operator,
        "audit_reason": payload.reason,
    }
