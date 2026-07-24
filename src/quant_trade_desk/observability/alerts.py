"""Redacted alert hooks."""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field

from .logging import redact


class Alert(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    severity: str
    summary: str
    trace_id: str | None = None
    details: dict[str, object] = Field(default_factory=dict)


class AlertDispatcher:
    def __init__(self) -> None:
        self._hooks: list[Callable[[dict[str, object]], None]] = []

    def register(self, hook: Callable[[dict[str, object]], None]) -> None:
        self._hooks.append(hook)

    def dispatch(self, alert: Alert) -> None:
        payload = redact(alert.model_dump(mode="json"))
        for hook in tuple(self._hooks):
            hook(payload)
